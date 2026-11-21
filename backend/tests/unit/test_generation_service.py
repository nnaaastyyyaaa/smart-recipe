from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.application.dto.recipe_dto import RecipeSuggestionSchema
from app.application.exceptions import (
    AIProviderUnavailableError,
    CategoryNotFoundError,
    DietaryRestrictionsNotFoundError,
    GenerationNotFoundError,
    GenerationRestrictionsNotSelectedError,
    GenerationStateChangedError,
    GenerationSuggestionsNotReadyError,
    NoSuitableRecipesError,
    ProductsNotFoundError,
    ProductsViolateRestrictionsError,
    SuggestionNotFoundError,
    SuggestionsPageNotFoundError,
)
from app.application.generation_service import GenerationService
from app.domain.entities.category import Category
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.generation_session import GenerationStatus
from app.domain.entities.product import Product
from app.infrastructure.generation.in_memory_generation_session_repository import (
    InMemoryGenerationSessionRepository,
)
from tests.fakes import (
    FakeCategoryRepository,
    FakeProductRepository,
    FakeRecipeGenerator,
    FakeRestrictionRepository,
)
from tests.helpers import req

VEGAN = DietaryRestriction(id=1, name="Веганське")
GLUTEN = DietaryRestriction(id=2, name="Без глютену")

FORBIDDEN = {3: {1}, 4: {2}, 5: {1, 2}}


class Env:
    def __init__(self) -> None:
        self.sessions = InMemoryGenerationSessionRepository()
        self.ai = FakeRecipeGenerator()
        products = [Product(id=i, name=f"Продукт {i:02d}", category_id=1 if i <= 10 else 2) for i in range(1, 21)]
        self.service = GenerationService(
            sessions=self.sessions,
            categories=FakeCategoryRepository([Category(id=1, name="А"), Category(id=2, name="Б")]),
            products=FakeProductRepository(
                products,
                {k: set(v) for k, v in FORBIDDEN.items()},
                {1: VEGAN, 2: GLUTEN},
            ),
            restrictions=FakeRestrictionRepository([VEGAN, GLUTEN]),
            recipe_generator=self.ai,
        )
        self.user = uuid4()

    async def started(self, restrictions: list[int] | None = None):
        state = await self.service.start(self.user)
        if restrictions is not None:
            await self.service.set_restrictions(self.user, state.id, restrictions)
        return state.id

    async def ready(self, restrictions=None, products=(1, 2, 6, 7), count=10):
        generation_id = await self.started([] if restrictions is None else restrictions)
        self.ai.recipe_count = count
        page = await self.service.suggest_recipes(self.user, generation_id, list(products))
        return generation_id, page


@pytest.fixture
def env():
    return Env()


def ai_recipe(title, used):
    return RecipeSuggestionSchema(title=title, description="d", cooking_time=5, used_product_ids=used)


@req("FR-B1")
async def test_start_creates_session_waiting_for_restrictions(env):
    state = await env.service.start(env.user)

    assert state.status == GenerationStatus.AWAITING_RESTRICTIONS
    assert state.restrictions == [] and state.product_ids == [] and state.suggestions_total == 0
    assert await env.sessions.get(state.id) is not None


@req("FR-B1")
async def test_each_start_creates_a_new_session_and_drops_previous(env):
    first = await env.service.start(env.user)
    second = await env.service.start(env.user)

    assert first.id != second.id

    with pytest.raises(GenerationNotFoundError):
        await env.service.get_state(env.user, first.id)

    assert (await env.service.get_state(env.user, second.id)).id == second.id


async def test_unknown_generation_raises_not_found(env):
    with pytest.raises(GenerationNotFoundError):
        await env.service.get_state(env.user, uuid4())


async def test_foreign_generation_is_indistinguishable_from_missing(env):
    state = await env.service.start(env.user)

    with pytest.raises(GenerationNotFoundError):
        await env.service.get_state(uuid4(), state.id)


async def test_expired_generation_raises_not_found(env):
    state = await env.service.start(env.user)
    (await env.sessions.get(state.id)).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    with pytest.raises(GenerationNotFoundError):
        await env.service.get_state(env.user, state.id)


async def test_access_extends_generation_lifetime(env):
    state = await env.service.start(env.user)
    session = await env.sessions.get(state.id)
    session.expires_at = datetime.now(timezone.utc) + timedelta(seconds=5)

    await env.service.get_state(env.user, state.id)

    assert session.expires_at > datetime.now(timezone.utc) + timedelta(minutes=30)


@req("FR-B1")
async def test_set_restrictions_returns_names_and_moves_to_products_step(env):
    generation_id = await env.started()

    state = await env.service.set_restrictions(env.user, generation_id, [2, 1])

    assert state.status == GenerationStatus.AWAITING_PRODUCTS
    assert [r.name for r in state.restrictions] == ["Без глютену", "Веганське"]


@req("FR-B1")
async def test_empty_restrictions_list_means_none(env):
    generation_id = await env.started()

    state = await env.service.set_restrictions(env.user, generation_id, [])

    assert state.status == GenerationStatus.AWAITING_PRODUCTS
    assert state.restrictions == []


async def test_unknown_restriction_is_rejected_and_state_unchanged(env):
    generation_id = await env.started()

    with pytest.raises(DietaryRestrictionsNotFoundError):
        await env.service.set_restrictions(env.user, generation_id, [1, 99])

    state = await env.service.get_state(env.user, generation_id)
    assert state.status == GenerationStatus.AWAITING_RESTRICTIONS


@req("FR-B1")
async def test_changing_restrictions_discards_suggestions_and_products(env):
    generation_id, _ = await env.ready([1])

    state = await env.service.set_restrictions(env.user, generation_id, [])

    assert state.status == GenerationStatus.AWAITING_PRODUCTS
    assert state.suggestions_total == 0 and state.product_ids == []

    with pytest.raises(GenerationSuggestionsNotReadyError):
        await env.service.get_suggestions_page(env.user, generation_id, 1)


@req("FR-B1", "FR-B2")
async def test_products_are_blocked_until_restrictions_selected(env):
    generation_id = await env.started()

    with pytest.raises(GenerationRestrictionsNotSelectedError):
        await env.service.get_available_products(env.user, generation_id, None, None, 50, 0)


@req("FR-B2")
async def test_products_exclude_those_violating_selected_restrictions(env):
    generation_id = await env.started([1])

    ids = {p.id for p in await env.service.get_available_products(env.user, generation_id, None, None, 50, 0)}

    assert 3 not in ids and 5 not in ids and 4 in ids


@req("FR-B2")
async def test_multiple_restrictions_are_combined(env):
    generation_id = await env.started([1, 2])

    ids = {p.id for p in await env.service.get_available_products(env.user, generation_id, None, None, 50, 0)}

    assert not ids & {3, 4, 5}
    assert len(ids) == 17


@req("FR-B2")
async def test_no_restrictions_shows_whole_catalog(env):
    generation_id = await env.started([])

    products = await env.service.get_available_products(env.user, generation_id, None, None, 50, 0)

    assert len(products) == 20


@req("FR-B3", "FR-B5")
async def test_products_support_category_search_and_pagination(env):
    generation_id = await env.started([])

    in_category = await env.service.get_available_products(env.user, generation_id, 2, None, 50, 0)
    page1 = await env.service.get_available_products(env.user, generation_id, None, None, 12, 0)
    page2 = await env.service.get_available_products(env.user, generation_id, None, None, 12, 12)
    found = await env.service.get_available_products(env.user, generation_id, None, "07", 50, 0)

    assert all(p.category_id == 2 for p in in_category) and len(in_category) == 10
    assert len(page1) == 12 and len(page2) == 8
    assert not {p.id for p in page1} & {p.id for p in page2}
    assert [p.id for p in found] == [7]


async def test_products_unknown_category_raises(env):
    generation_id = await env.started([])

    with pytest.raises(CategoryNotFoundError):
        await env.service.get_available_products(env.user, generation_id, 99, None, 50, 0)


@req("FR-B1")
async def test_suggestions_are_blocked_until_restrictions_selected(env):
    generation_id = await env.started()

    with pytest.raises(GenerationRestrictionsNotSelectedError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 2])


@req("FR-G1")
async def test_selected_restrictions_and_products_are_sent_to_ai(env):
    generation_id = await env.started([1])

    await env.service.suggest_recipes(env.user, generation_id, [1, 2, 6])

    products, restrictions = env.ai.suggest_calls[0]
    assert {p.id for p in products} == {1, 2, 6}
    assert [r.name for r in restrictions] == ["Веганське"]


@req("FR-G1")
async def test_no_restrictions_are_sent_as_empty_list(env):
    generation_id = await env.started([])

    await env.service.suggest_recipes(env.user, generation_id, [1, 2])

    assert env.ai.suggest_calls[0][1] == []


@req("FR-B2")
async def test_product_violating_restriction_is_rejected_before_ai_call(env):
    generation_id = await env.started([1])

    with pytest.raises(ProductsViolateRestrictionsError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 3])

    assert env.ai.suggest_calls == []


async def test_unknown_product_is_rejected_before_ai_call(env):
    generation_id = await env.started([])

    with pytest.raises(ProductsNotFoundError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 999])

    assert env.ai.suggest_calls == []


@req("FR-G2", "FR-G3")
@pytest.mark.parametrize(
    "count,total,pages,first_page_size",
    [(1, 1, 1, 1), (8, 8, 1, 8), (9, 9, 2, 8), (16, 16, 2, 8), (20, 16, 2, 8)],
)
async def test_first_page_has_at_most_8_and_total_is_capped_at_16(env, count, total, pages, first_page_size):
    _, page = await env.ready(count=count)

    assert page.page == 1 and page.page_size == 8
    assert page.total == total and page.total_pages == pages
    assert len(page.items) == first_page_size


@req("FR-G3")
async def test_second_page_contains_the_rest_with_continuing_ids(env):
    generation_id, first = await env.ready(count=16)

    second = await env.service.get_suggestions_page(env.user, generation_id, 2)

    assert [i.id for i in first.items] == list(range(8))
    assert [i.id for i in second.items] == list(range(8, 16))
    assert not {i.title for i in first.items} & {i.title for i in second.items}


@req("FR-G3")
@pytest.mark.parametrize("page", [0, -1, 3, 100])
async def test_nonexistent_page_raises(env, page):
    generation_id, _ = await env.ready(count=16)

    with pytest.raises(SuggestionsPageNotFoundError):
        await env.service.get_suggestions_page(env.user, generation_id, page)


async def test_suggestions_page_is_unavailable_before_generation(env):
    generation_id = await env.started([])

    with pytest.raises(GenerationSuggestionsNotReadyError):
        await env.service.get_suggestions_page(env.user, generation_id, 1)


@req("FR-G2")
async def test_suggestions_with_most_products_come_first(env):
    generation_id = await env.started([])
    env.ai.custom_suggestions = [
        ai_recipe("Мало", [1, 2]),
        ai_recipe("Багато", [1, 2, 6, 7]),
        ai_recipe("Середньо", [1, 2, 6]),
    ]

    page = await env.service.suggest_recipes(env.user, generation_id, [1, 2, 6, 7])

    assert [i.title for i in page.items] == ["Багато", "Середньо", "Мало"]


async def test_invalid_ai_suggestions_are_filtered_out(env):
    generation_id = await env.started([])
    env.ai.custom_suggestions = [
        ai_recipe("Добра", [1, 2]),
        ai_recipe("добра", [1, 2, 6]),
        ai_recipe("Чужі продукти", [1, 999]),
        ai_recipe("Не обрані", [1, 7]),
    ]

    page = await env.service.suggest_recipes(env.user, generation_id, [1, 2, 6])

    assert [i.title for i in page.items] == ["Добра"]
    assert page.total == 1


async def test_recipe_using_fewer_than_two_distinct_products_is_filtered(env):
    generation_id = await env.started([])
    env.ai.custom_suggestions = [
        RecipeSuggestionSchema.model_construct(
            title="Одна", description="d", cooking_time=5, used_product_ids=[1, 1],
        ),
        ai_recipe("Нормальна", [1, 2]),
    ]

    page = await env.service.suggest_recipes(env.user, generation_id, [1, 2])

    assert [i.title for i in page.items] == ["Нормальна"]


@req("FR-G4")
async def test_empty_ai_answer_raises_no_suitable_recipes(env):
    generation_id = await env.started([])
    env.ai.custom_suggestions = []

    with pytest.raises(NoSuitableRecipesError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 2])


@req("FR-G4")
async def test_all_invalid_ai_answers_raise_no_suitable_recipes(env):
    generation_id = await env.started([])
    env.ai.custom_suggestions = [ai_recipe("Чужа", [1, 999])]

    with pytest.raises(NoSuitableRecipesError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 2])


@req("FR-G4")
async def test_session_survives_no_results_and_user_can_retry(env):
    generation_id = await env.started([1])
    env.ai.custom_suggestions = []

    with pytest.raises(NoSuitableRecipesError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 2])

    env.ai.custom_suggestions = None
    page = await env.service.suggest_recipes(env.user, generation_id, [1, 2, 6])

    assert page.total > 0
    assert (await env.service.get_state(env.user, generation_id)).restrictions[0].name == "Веганське"


async def test_ai_failure_keeps_previous_suggestions(env):
    generation_id, first = await env.ready(count=5)
    env.ai.suggest_error = AIProviderUnavailableError()

    with pytest.raises(AIProviderUnavailableError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 2, 6])

    again = await env.service.get_suggestions_page(env.user, generation_id, 1)
    assert [i.title for i in again.items] == [i.title for i in first.items]


async def test_regenerating_replaces_previous_suggestions_and_products(env):
    generation_id, _ = await env.ready(count=16)
    env.ai.recipe_count = 3

    page = await env.service.suggest_recipes(env.user, generation_id, [8, 9, 10])

    state = await env.service.get_state(env.user, generation_id)
    assert page.total == 3 and state.product_ids == [8, 9, 10] and state.suggestions_total == 3


@req("FR-B1")
async def test_restrictions_changed_while_ai_is_working_is_detected(env):
    generation_id = await env.started([1])
    original = env.ai.suggest_recipes

    async def racing(products, restrictions):
        result = await original(products, restrictions)
        await env.service.set_restrictions(env.user, generation_id, [2])
        return result

    env.ai.suggest_recipes = racing

    with pytest.raises(GenerationStateChangedError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 2])

    state = await env.service.get_state(env.user, generation_id)
    assert state.suggestions_total == 0


async def test_new_generation_started_while_ai_is_working_invalidates_old_one(env):
    generation_id = await env.started([])
    original = env.ai.suggest_recipes

    async def racing(products, restrictions):
        result = await original(products, restrictions)
        await env.service.start(env.user)
        return result

    env.ai.suggest_recipes = racing

    with pytest.raises(GenerationNotFoundError):
        await env.service.suggest_recipes(env.user, generation_id, [1, 2])


@req("FR-G5", "FR-G6")
async def test_full_recipe_is_generated_for_chosen_suggestion(env):
    generation_id, page = await env.ready([1], products=(1, 2, 6, 7))
    chosen = page.items[2]

    recipe = await env.service.generate_full_recipe(env.user, generation_id, chosen.id)

    suggestion, products, restrictions = env.ai.full_calls[0]
    assert recipe.title == chosen.title
    assert suggestion.title == chosen.title and suggestion.cooking_time == chosen.cooking_time
    assert {p.id for p in products} == set(chosen.used_product_ids)
    assert [r.name for r in restrictions] == ["Веганське"]
    assert recipe.ingredients and recipe.instructions and recipe.cooking_time >= 1


@req("FR-G5")
async def test_full_recipe_on_second_page_uses_correct_suggestion(env):
    generation_id, _ = await env.ready(count=16)
    second = await env.service.get_suggestions_page(env.user, generation_id, 2)

    recipe = await env.service.generate_full_recipe(env.user, generation_id, second.items[0].id)

    assert recipe.title == second.items[0].title


@req("FR-G5")
@pytest.mark.parametrize("suggestion_id", [-1, 10, 999])
async def test_full_recipe_for_unknown_suggestion_raises(env, suggestion_id):
    generation_id, _ = await env.ready(count=10)

    with pytest.raises(SuggestionNotFoundError):
        await env.service.generate_full_recipe(env.user, generation_id, suggestion_id)


async def test_full_recipe_requires_generated_suggestions(env):
    generation_id = await env.started([])

    with pytest.raises(GenerationSuggestionsNotReadyError):
        await env.service.generate_full_recipe(env.user, generation_id, 0)


async def test_full_recipe_ai_error_is_propagated(env):
    generation_id, _ = await env.ready()
    env.ai.full_error = AIProviderUnavailableError()

    with pytest.raises(AIProviderUnavailableError):
        await env.service.generate_full_recipe(env.user, generation_id, 0)


async def test_other_user_cannot_use_my_generation(env):
    generation_id, _ = await env.ready()
    stranger = uuid4()

    for call in (
        env.service.get_state(stranger, generation_id),
        env.service.get_suggestions_page(stranger, generation_id, 1),
        env.service.generate_full_recipe(stranger, generation_id, 0),
        env.service.suggest_recipes(stranger, generation_id, [1, 2]),
        env.service.set_restrictions(stranger, generation_id, []),
        env.service.get_available_products(stranger, generation_id, None, None, 10, 0),
    ):
        with pytest.raises(GenerationNotFoundError):
            await call


async def test_full_recipe_fails_cleanly_if_product_was_removed_from_catalog(env):
    generation_id, page = await env.ready(products=(1, 2, 6, 7))
    for product_id in page.items[0].used_product_ids:
        env.service.products.products.pop(product_id)

    with pytest.raises(ProductsNotFoundError):
        await env.service.generate_full_recipe(env.user, generation_id, page.items[0].id)

    assert env.ai.full_calls == []


async def categories_of(env, generation_id):
    return [c.name for c in await env.service.get_available_categories(env.user, generation_id)]


@req("FR-B1", "FR-B2")
async def test_categories_are_blocked_until_restrictions_selected(env):
    generation_id = await env.started()

    with pytest.raises(GenerationRestrictionsNotSelectedError):
        await env.service.get_available_categories(env.user, generation_id)


@req("FR-B2")
async def test_all_categories_with_products_are_offered_without_restrictions(env):
    generation_id = await env.started([])

    assert await categories_of(env, generation_id) == ["А", "Б"]


@req("FR-B2")
async def test_category_without_any_allowed_product_is_hidden(env):
    for product_id in range(11, 21):
        env.service.products.forbidden[product_id] = {1}
    generation_id = await env.started([1])

    assert await categories_of(env, generation_id) == ["А"]


@req("FR-B2")
async def test_category_stays_if_at_least_one_product_is_allowed(env):
    for product_id in range(11, 20):
        env.service.products.forbidden[product_id] = {1}
    generation_id = await env.started([1])

    assert await categories_of(env, generation_id) == ["А", "Б"]


async def test_categories_of_foreign_generation_are_not_available(env):
    generation_id = await env.started([])

    with pytest.raises(GenerationNotFoundError):
        await env.service.get_available_categories(uuid4(), generation_id)
