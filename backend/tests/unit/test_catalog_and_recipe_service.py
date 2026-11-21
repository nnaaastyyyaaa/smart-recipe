from uuid import uuid4

import pytest

from app.application.catalog_service import CatalogService
from app.application.dto.recipe_dto import RecipeGenerationSchema
from app.application.exceptions import (
    CategoryNotFoundError,
    DietaryRestrictionsNotFoundError,
    ProductNotFoundError,
)
from app.application.recipe_service import RecipeService
from app.domain.entities.category import Category
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product
from tests.fakes import (
    FakeCategoryRepository,
    FakeProductRepository,
    FakeRecipeRepository,
    FakeRestrictionRepository,
    FakeSavedRecipeRepository,
)
from tests.helpers import req

VEGAN = DietaryRestriction(id=1, name="Веганське")
GLUTEN = DietaryRestriction(id=2, name="Без глютену")


@pytest.fixture
def catalog_service():
    products = [
        Product(id=1, name="Помідор", category_id=1),
        Product(id=2, name="Молоко", category_id=2),
        Product(id=3, name="Борошно", category_id=3),
        Product(id=4, name="Печиво", category_id=3),
    ]
    forbidden = {2: {1}, 3: {2}, 4: {1, 2}}

    return CatalogService(
        categories=FakeCategoryRepository([Category(id=1, name="Овочі"), Category(id=2, name="Молочні"), Category(id=3, name="Крупи")]),
        products=FakeProductRepository(products, forbidden, {1: VEGAN, 2: GLUTEN}),
        restrictions=FakeRestrictionRepository([VEGAN, GLUTEN]),
    )


@req("FR-B3")
async def test_get_categories_sorted_by_name(catalog_service):
    names = [c.name for c in await catalog_service.get_categories()]

    assert names == sorted(names)


async def test_get_category_and_missing(catalog_service):
    assert (await catalog_service.get_category(1)).name == "Овочі"
    assert await catalog_service.get_category(99) is None


async def test_get_dietary_restrictions(catalog_service):
    assert len(await catalog_service.get_dietary_restrictions()) == 2


@req("FR-B3")
async def test_get_products_by_category(catalog_service):
    items = await catalog_service.get_products(3, None, 50, 0)

    assert {p.name for p in items} == {"Борошно", "Печиво"}


@req("FR-B3")
async def test_get_products_search(catalog_service):
    items = await catalog_service.get_products(None, "моло", 50, 0)

    assert [p.name for p in items] == ["Молоко"]


@req("FR-B5")
async def test_get_products_limit_and_offset(catalog_service):
    first = await catalog_service.get_products(None, None, 2, 0)
    second = await catalog_service.get_products(None, None, 2, 2)

    assert len(first) == 2 and len(second) == 2
    assert not {p.id for p in first} & {p.id for p in second}


async def test_get_products_unknown_category_raises(catalog_service):
    with pytest.raises(CategoryNotFoundError):
        await catalog_service.get_products(99, None, 50, 0)


@req("FR-B2")
async def test_get_products_excludes_by_restrictions(catalog_service):
    vegan = await catalog_service.get_products(None, None, 50, 0, restriction_ids=[1])
    both = await catalog_service.get_products(None, None, 50, 0, restriction_ids=[1, 2])

    assert {p.name for p in vegan} == {"Помідор", "Борошно"}
    assert {p.name for p in both} == {"Помідор"}


async def test_get_products_unknown_restriction_raises(catalog_service):
    with pytest.raises(DietaryRestrictionsNotFoundError):
        await catalog_service.get_products(None, None, 50, 0, restriction_ids=[1, 99])


async def test_get_products_duplicate_restriction_ids_are_tolerated(catalog_service):
    items = await catalog_service.get_products(None, None, 50, 0, restriction_ids=[1, 1])

    assert {p.name for p in items} == {"Помідор", "Борошно"}


async def test_get_product_restrictions(catalog_service):
    assert [r.name for r in await catalog_service.get_product_restrictions(4)] == ["Веганське", "Без глютену"]
    assert await catalog_service.get_product_restrictions(1) == []

    with pytest.raises(ProductNotFoundError):
        await catalog_service.get_product_restrictions(99)


async def test_get_single_product_and_restriction(catalog_service):
    assert (await catalog_service.get_product(1)).name == "Помідор"
    assert await catalog_service.get_product(99) is None
    assert (await catalog_service.get_dietary_restriction(1)).name == "Веганське"
    assert await catalog_service.get_dietary_restriction(99) is None


def full_recipe(title="Омлет") -> RecipeGenerationSchema:
    return RecipeGenerationSchema(
        title=title, description="Опис", ingredients="Яйця — 2 шт", instructions="Смажити", cooking_time=10,
    )


@pytest.fixture
def recipe_service():
    recipes = FakeRecipeRepository()
    saved = FakeSavedRecipeRepository(recipes)
    return RecipeService(recipes, saved), saved


@req("FR-S1")
async def test_save_recipe_creates_recipe_and_link(recipe_service):
    service, saved = recipe_service
    user_id = uuid4()

    recipe = await service.save_recipe(user_id, full_recipe())

    assert recipe.id is not None
    assert (user_id, recipe.id) in saved.links


@req("FR-S1")
async def test_save_recipe_fails_loudly_if_link_not_created(recipe_service):
    service, saved = recipe_service
    saved.link_fails = True

    with pytest.raises(RuntimeError):
        await service.save_recipe(uuid4(), full_recipe())


@req("FR-A12")
async def test_get_saved_recipes_returns_only_own(recipe_service):
    service, _ = recipe_service
    mine, other = uuid4(), uuid4()
    await service.save_recipe(mine, full_recipe("Моя"))
    await service.save_recipe(other, full_recipe("Чужа"))

    assert [r.title for r in await service.get_saved_recipes(mine)] == ["Моя"]


@req("FR-A12")
async def test_get_saved_recipe_of_other_user_is_none(recipe_service):
    service, _ = recipe_service
    owner = uuid4()
    recipe = await service.save_recipe(owner, full_recipe())

    assert await service.get_saved_recipe(owner, recipe.id) is not None
    assert await service.get_saved_recipe(uuid4(), recipe.id) is None


@req("FR-A12")
async def test_delete_saved_recipe(recipe_service):
    service, _ = recipe_service
    owner = uuid4()
    recipe = await service.save_recipe(owner, full_recipe())

    assert await service.delete_saved_recipe(uuid4(), recipe.id) is False
    assert await service.delete_saved_recipe(owner, recipe.id) is True
    assert await service.delete_saved_recipe(owner, recipe.id) is False


@req("FR-A13")
async def test_saved_recipes_support_limit_and_offset(recipe_service):
    service, _ = recipe_service
    owner = uuid4()
    for index in range(30):
        await service.save_recipe(owner, full_recipe(f"Рецепт {index:02d}"))

    first = await service.get_saved_recipes(owner, limit=12, offset=0)
    second = await service.get_saved_recipes(owner, limit=12, offset=12)
    third = await service.get_saved_recipes(owner, limit=12, offset=24)
    everything = await service.get_saved_recipes(owner)

    assert [len(first), len(second), len(third), len(everything)] == [12, 12, 6, 30]
    assert [r.id for r in first + second + third] == [r.id for r in everything]


@req("FR-A13")
async def test_count_saved_recipes_counts_only_own(recipe_service):
    service, _ = recipe_service
    mine, other = uuid4(), uuid4()
    for index in range(3):
        await service.save_recipe(mine, full_recipe(f"Моя {index}"))
    await service.save_recipe(other, full_recipe("Чужа"))

    assert await service.count_saved_recipes(mine) == 3
    assert await service.count_saved_recipes(uuid4()) == 0
