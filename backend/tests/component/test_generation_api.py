"""Компонентні тести /api/generations: повний покроковий процес на реальній БД."""
from uuid import uuid4

import pytest

from app.application.dto.recipe_dto import RecipeSuggestionSchema
from app.application.exceptions import (
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderUnavailableError,
)
from app.infrastructure.ai.rate_limiter import AIRateLimitExceededError
from tests.helpers import API, register, req, set_restrictions, start_generation


def code(response) -> str | None:
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


async def to_products_step(client, catalog, restrictions=()):
    generation_id = await start_generation(client)
    response = await set_restrictions(client, generation_id, [catalog.restrictions[r] for r in restrictions])
    assert response.status_code == 200, response.text
    return generation_id


async def suggest(client, generation_id, product_ids):
    return await client.post(f"{API}/generations/{generation_id}/suggestions", json={"product_ids": product_ids})


@req("FR-B1")
async def test_start_returns_new_generation_awaiting_restrictions(authed):
    response = await authed.post(f"{API}/generations")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "awaiting_restrictions"
    assert body["restrictions"] == [] and body["product_ids"] == [] and body["suggestions_total"] == 0
    assert body["id"] and body["expires_at"]


@req("FR-B1")
async def test_every_press_of_start_creates_new_generation(authed):
    first = await start_generation(authed)
    second = await start_generation(authed)

    assert first != second
    assert (await authed.get(f"{API}/generations/{first}")).status_code == 404
    assert (await authed.get(f"{API}/generations/{second}")).status_code == 200


@req("FR-B1")
async def test_get_state_reflects_progress(authed, catalog):
    generation_id = await start_generation(authed)
    assert (await authed.get(f"{API}/generations/{generation_id}")).json()["status"] == "awaiting_restrictions"

    await set_restrictions(authed, generation_id, [catalog.restrictions["vegan"]])
    state = (await authed.get(f"{API}/generations/{generation_id}")).json()

    assert state["status"] == "awaiting_products"
    assert [r["name"] for r in state["restrictions"]] == ["Веганське"]


async def test_unknown_generation_returns_404_with_code(authed):
    response = await authed.get(f"{API}/generations/{uuid4()}")

    assert response.status_code == 404 and code(response) == "GENERATION_NOT_FOUND"


async def test_malformed_generation_id_returns_422(authed):
    assert (await authed.get(f"{API}/generations/not-a-uuid")).status_code == 422


@req("FR-B1")
async def test_restrictions_step_is_mandatory_before_products_and_suggestions(authed, catalog):
    generation_id = await start_generation(authed)

    products = await authed.get(f"{API}/generations/{generation_id}/products")
    suggestions = await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    assert products.status_code == 409 and code(products) == "RESTRICTIONS_NOT_SELECTED"
    assert suggestions.status_code == 409 and code(suggestions) == "RESTRICTIONS_NOT_SELECTED"


@req("FR-B1")
async def test_choosing_no_restrictions_is_explicit_empty_list(authed, catalog):
    generation_id = await start_generation(authed)

    response = await set_restrictions(authed, generation_id, [])

    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_products" and response.json()["restrictions"] == []


async def test_restrictions_field_is_required(authed):
    generation_id = await start_generation(authed)

    response = await authed.put(f"{API}/generations/{generation_id}/restrictions", json={})

    assert response.status_code == 422


@pytest.mark.parametrize("ids", [[0], [-1], [1, 1], list(range(1, 22))])
async def test_restrictions_are_validated(authed, catalog, ids):
    generation_id = await start_generation(authed)

    assert (await set_restrictions(authed, generation_id, ids)).status_code == 422


async def test_unknown_restriction_returns_404_and_keeps_state(authed, catalog):
    generation_id = await start_generation(authed)

    response = await set_restrictions(authed, generation_id, [catalog.restrictions["vegan"], 99999])

    assert response.status_code == 404 and code(response) == "RESTRICTIONS_NOT_FOUND"
    assert (await authed.get(f"{API}/generations/{generation_id}")).json()["status"] == "awaiting_restrictions"


@req("FR-B2")
async def test_only_products_matching_restrictions_are_offered(authed, catalog):
    generation_id = await to_products_step(authed, catalog, ["vegan", "gluten"])

    response = await authed.get(f"{API}/generations/{generation_id}/products")

    assert response.status_code == 200
    assert {p["name"] for p in response.json()} == {"Помідор", "Огірок", "Морква", "Картопля", "Рис"}


@req("FR-B2")
async def test_without_restrictions_all_products_are_offered(authed, catalog):
    generation_id = await to_products_step(authed, catalog)

    assert len((await authed.get(f"{API}/generations/{generation_id}/products")).json()) == 11


@req("FR-B2")
async def test_changing_restrictions_changes_offered_products(authed, catalog):
    generation_id = await to_products_step(authed, catalog, ["vegan"])
    vegan_only = (await authed.get(f"{API}/generations/{generation_id}/products")).json()

    await set_restrictions(authed, generation_id, [])
    everything = (await authed.get(f"{API}/generations/{generation_id}/products")).json()

    assert len(vegan_only) == 7 and len(everything) == 11


@req("FR-B3", "FR-B5")
async def test_products_step_supports_category_search_and_pagination(authed, catalog):
    generation_id = await to_products_step(authed, catalog, ["vegan"])
    url = f"{API}/generations/{generation_id}/products"

    veg = await authed.get(url, params={"category_id": catalog.categories["veg"]})
    meat = await authed.get(url, params={"category_id": catalog.categories["meat"]})
    search = await authed.get(url, params={"search": "кар"})
    page1 = await authed.get(url, params={"limit": 3, "offset": 0})
    page2 = await authed.get(url, params={"limit": 3, "offset": 3})

    assert len(veg.json()) == 4
    assert meat.json() == []
    assert {p["name"] for p in search.json()} == {"Картопля", "Макарони"}
    assert not {p["id"] for p in page1.json()} & {p["id"] for p in page2.json()}


async def test_products_step_unknown_category_returns_404(authed, catalog):
    generation_id = await to_products_step(authed, catalog)

    response = await authed.get(f"{API}/generations/{generation_id}/products", params={"category_id": 99999})

    assert response.status_code == 404 and code(response) == "CATEGORY_NOT_FOUND"


@req("FR-B4")
@pytest.mark.parametrize("product_ids", [[], [1]])
async def test_at_least_two_products_are_required(authed, catalog, product_ids):
    generation_id = await to_products_step(authed, catalog)

    response = await suggest(authed, generation_id, product_ids)

    assert response.status_code == 422


@req("FR-B4")
async def test_exactly_two_products_are_accepted(authed, catalog):
    generation_id = await to_products_step(authed, catalog)

    response = await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    assert response.status_code == 200


@req("FR-G1")
async def test_selected_products_and_restrictions_reach_the_ai(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog, ["vegan"])

    await suggest(authed, generation_id, catalog.ids("tomato", "carrot", "rice"))

    products, restrictions = fake_ai.suggest_calls[0]
    assert {p.name for p in products} == {"Помідор", "Морква", "Рис"}
    assert [r.name for r in restrictions] == ["Веганське"]


@req("FR-B2")
async def test_product_violating_restrictions_is_rejected_and_ai_not_called(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog, ["vegan"])

    response = await suggest(authed, generation_id, catalog.ids("tomato", "milk"))

    assert response.status_code == 422 and code(response) == "PRODUCTS_VIOLATE_RESTRICTIONS"
    assert fake_ai.suggest_calls == []


async def test_unknown_product_returns_404(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog)

    response = await suggest(authed, generation_id, [catalog.products["tomato"], 99999])

    assert response.status_code == 404 and code(response) == "PRODUCTS_NOT_FOUND"
    assert fake_ai.suggest_calls == []


@pytest.mark.parametrize("product_ids", [[1, 1], [0, 2], [-1, 2], list(range(1, 32))])
async def test_product_ids_are_validated(authed, catalog, product_ids):
    generation_id = await to_products_step(authed, catalog)

    assert (await suggest(authed, generation_id, product_ids)).status_code == 422


@req("FR-G2")
async def test_first_page_has_at_most_8_items(authed, catalog, fake_ai):
    fake_ai.recipe_count = 16
    generation_id = await to_products_step(authed, catalog)

    body = (await suggest(authed, generation_id, catalog.ids("tomato", "cucumber", "carrot", "potato"))).json()

    assert len(body["items"]) == 8
    assert (body["page"], body["page_size"], body["total"], body["total_pages"]) == (1, 8, 16, 2)
    assert set(body["items"][0]) == {"id", "title", "description", "cooking_time", "used_product_ids"}


@req("FR-G3")
async def test_second_page_shows_remaining_suggestions(authed, catalog, fake_ai):
    fake_ai.recipe_count = 16
    generation_id = await to_products_step(authed, catalog)
    first = (await suggest(authed, generation_id, catalog.ids("tomato", "cucumber", "carrot", "potato"))).json()

    second = await authed.get(f"{API}/generations/{generation_id}/suggestions", params={"page": 2})

    assert second.status_code == 200
    assert [i["id"] for i in second.json()["items"]] == list(range(8, 16))
    assert not {i["title"] for i in first["items"]} & {i["title"] for i in second.json()["items"]}


@req("FR-G3")
async def test_ai_answers_beyond_16_are_capped(authed, catalog, fake_ai):
    fake_ai.recipe_count = 25
    generation_id = await to_products_step(authed, catalog)

    body = (await suggest(authed, generation_id, catalog.ids("tomato", "cucumber", "carrot"))).json()

    assert body["total"] == 16 and body["total_pages"] == 2


@req("FR-G3")
async def test_page_defaults_to_first_and_is_validated(authed, catalog, fake_ai):
    fake_ai.recipe_count = 16
    generation_id = await to_products_step(authed, catalog)
    await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))
    url = f"{API}/generations/{generation_id}/suggestions"

    assert (await authed.get(url)).json()["page"] == 1
    assert (await authed.get(url, params={"page": 0})).status_code == 422
    third = await authed.get(url, params={"page": 3})
    assert third.status_code == 404 and code(third) == "SUGGESTIONS_PAGE_NOT_FOUND"


async def test_suggestions_page_before_generation_returns_409(authed, catalog):
    generation_id = await to_products_step(authed, catalog)

    response = await authed.get(f"{API}/generations/{generation_id}/suggestions")

    assert response.status_code == 409 and code(response) == "SUGGESTIONS_NOT_READY"


@req("FR-G4")
async def test_no_suitable_recipes_returns_422_and_generation_stays_usable(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog, ["vegan"])
    fake_ai.custom_suggestions = []

    empty = await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    assert empty.status_code == 422 and code(empty) == "NO_SUITABLE_RECIPES"
    assert empty.json()["detail"]["message"] == (
        "За обраними інгредієнтами та дієтичними обмеженнями рецептів не знайдено."
    )
    fake_ai.custom_suggestions = None
    retry = await suggest(authed, generation_id, catalog.ids("tomato", "carrot", "rice"))
    assert retry.status_code == 200
    state = (await authed.get(f"{API}/generations/{generation_id}")).json()
    assert [r["name"] for r in state["restrictions"]] == ["Веганське"]

@req("FR-G2")
async def test_invalid_ai_suggestions_are_filtered_out(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog)
    tomato, carrot, rice = catalog.ids("tomato", "carrot", "rice")
    fake_ai.custom_suggestions = [
        RecipeSuggestionSchema(title="Добра", description="d", cooking_time=5, used_product_ids=[tomato, carrot]),
        RecipeSuggestionSchema(title="добра", description="d", cooking_time=5, used_product_ids=[tomato, carrot]),
        RecipeSuggestionSchema(title="Чужий продукт", description="d", cooking_time=5, used_product_ids=[tomato, rice]),
    ]

    body = (await suggest(authed, generation_id, [tomato, carrot])).json()

    assert [i["title"] for i in body["items"]] == ["Добра"]


@req("FR-G5", "FR-G6")
async def test_full_recipe_for_chosen_suggestion(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog, ["gluten"])
    page = (await suggest(authed, generation_id, catalog.ids("tomato", "cucumber", "rice"))).json()
    chosen = page["items"][1]

    response = await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": chosen["id"]})

    assert response.status_code == 200
    recipe = response.json()
    assert set(recipe) == {"title", "description", "ingredients", "instructions", "cooking_time"}
    assert recipe["title"] == chosen["title"]
    assert recipe["ingredients"].strip() and recipe["instructions"].strip() and recipe["cooking_time"] >= 1
    suggestion, products, restrictions = fake_ai.full_calls[0]
    assert {p.id for p in products} == set(chosen["used_product_ids"])
    assert [r.name for r in restrictions] == ["Без глютену"]


@req("FR-G5")
async def test_full_recipe_for_item_from_second_page(authed, catalog, fake_ai):
    fake_ai.recipe_count = 16
    generation_id = await to_products_step(authed, catalog)
    await suggest(authed, generation_id, catalog.ids("tomato", "cucumber", "carrot", "potato"))
    second = (await authed.get(f"{API}/generations/{generation_id}/suggestions", params={"page": 2})).json()

    response = await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": second["items"][3]["id"]})

    assert response.status_code == 200 and response.json()["title"] == second["items"][3]["title"]


@req("FR-G5")
async def test_unknown_suggestion_id_returns_404(authed, catalog):
    generation_id = await to_products_step(authed, catalog)
    await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    response = await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": 500})

    assert response.status_code == 404 and code(response) == "SUGGESTION_NOT_FOUND"


async def test_full_recipe_before_suggestions_returns_409(authed, catalog):
    generation_id = await to_products_step(authed, catalog)

    response = await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": 0})

    assert response.status_code == 409 and code(response) == "SUGGESTIONS_NOT_READY"


@pytest.mark.parametrize("payload", [{}, {"suggestion_id": -1}, {"suggestion_id": "x"}, {"suggestion_id": 0, "extra": 1}])
async def test_recipe_request_validation(authed, catalog, payload):
    generation_id = await to_products_step(authed, catalog)
    await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    assert (await authed.post(f"{API}/generations/{generation_id}/recipe", json=payload)).status_code == 422


@req("FR-B1")
async def test_changing_restrictions_discards_suggestions(authed, catalog):
    generation_id = await to_products_step(authed, catalog)
    await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    await set_restrictions(authed, generation_id, [catalog.restrictions["vegan"]])

    state = (await authed.get(f"{API}/generations/{generation_id}")).json()
    assert state["status"] == "awaiting_products" and state["suggestions_total"] == 0
    assert (await authed.get(f"{API}/generations/{generation_id}/suggestions")).status_code == 409


@req("NFR-4")
async def test_internal_rpm_limit_returns_429_with_retry_after(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog)
    fake_ai.suggest_error = AIRateLimitExceededError(retry_after=42)

    response = await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"
    assert code(response) == "AI_REQUEST_LIMIT_REACHED"
    assert "Спробуйте ще раз" in response.json()["detail"]["message"]


@req("NFR-4")
async def test_provider_quota_exhaustion_returns_503_with_message(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog)
    fake_ai.suggest_error = AIProviderRateLimitError()

    response = await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))

    assert response.status_code == 503 and code(response) == "AI_PROVIDER_LIMIT_REACHED"


@pytest.mark.parametrize(
    "error,status,error_code",
    [
        (AIProviderUnavailableError(), 503, "AI_SERVICE_UNAVAILABLE"),
        (AIProviderInvalidResponseError(), 502, "AI_INVALID_RESPONSE"),
    ],
)
async def test_other_ai_errors_are_mapped(authed, catalog, fake_ai, error, status, error_code):
    generation_id = await to_products_step(authed, catalog)
    fake_ai.suggest_error = error

    suggestions = await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))
    assert (suggestions.status_code, code(suggestions)) == (status, error_code)

    fake_ai.suggest_error = None
    await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))
    fake_ai.full_error = error
    recipe = await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": 0})
    assert (recipe.status_code, code(recipe)) == (status, error_code)


@req("NFR-4")
async def test_rate_limit_error_on_full_recipe_returns_429(authed, catalog, fake_ai):
    generation_id = await to_products_step(authed, catalog)
    await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))
    fake_ai.full_error = AIRateLimitExceededError(retry_after=10)

    response = await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": 0})

    assert response.status_code == 429 and response.headers["retry-after"] == "10"


async def test_other_user_cannot_access_my_generation(authed, catalog, client_factory):
    generation_id = await to_products_step(authed, catalog)
    await suggest(authed, generation_id, catalog.ids("tomato", "carrot"))
    stranger = client_factory()
    await register(stranger)
    base = f"{API}/generations/{generation_id}"

    responses = [
        await stranger.get(base),
        await stranger.put(f"{base}/restrictions", json={"restriction_ids": []}),
        await stranger.get(f"{base}/products"),
        await suggest(stranger, generation_id, catalog.ids("tomato", "carrot")),
        await stranger.get(f"{base}/suggestions"),
        await stranger.post(f"{base}/recipe", json={"suggestion_id": 0}),
    ]

    assert [r.status_code for r in responses] == [404] * 6
    assert (await authed.get(base)).status_code == 200 


@pytest.mark.parametrize("field,path", [("product_ids", "suggestions"), ("restriction_ids", "restrictions")])
async def test_huge_ids_in_generation_requests_never_cause_server_error(authed, catalog, field, path):
    generation_id = await start_generation(authed)
    await set_restrictions(authed, generation_id, [])
    ids = [catalog.products["tomato"], 99999999999] if field == "product_ids" else [99999999999]
    method = authed.post if field == "product_ids" else authed.put

    response = await method(f"{API}/generations/{generation_id}/{path}", json={field: ids})

    assert response.status_code in (404, 422)


@req("FR-B2")
async def test_categories_without_any_allowed_product_are_hidden(authed, catalog):
    generation_id = await to_products_step(authed, catalog, ["vegan"])

    response = await authed.get(f"{API}/generations/{generation_id}/categories")

    assert response.status_code == 200
    assert {c["name"] for c in response.json()} == {"Овочі", "Крупи та борошно"}



async def category_names(client, generation_id):
    response = await client.get(f"{API}/generations/{generation_id}/categories")
    assert response.status_code == 200, response.text
    return {c["name"] for c in response.json()}


@req("FR-B1", "FR-B2")
async def test_categories_are_blocked_until_restrictions_selected(authed):
    generation_id = await start_generation(authed)

    response = await authed.get(f"{API}/generations/{generation_id}/categories")

    assert response.status_code == 409 and code(response) == "RESTRICTIONS_NOT_SELECTED"


@req("FR-B2")
async def test_all_categories_are_offered_without_restrictions(authed, catalog):
    generation_id = await to_products_step(authed, catalog)

    assert await category_names(authed, generation_id) == {"Овочі", "М'ясо", "Молочні продукти", "Крупи та борошно"}


@req("FR-B2")
async def test_categories_without_allowed_products_are_hidden_for_vegan(authed, catalog):
    generation_id = await to_products_step(authed, catalog, ["vegan"])

    assert await category_names(authed, generation_id) == {"Овочі", "Крупи та борошно"}


@req("FR-B2")
async def test_categories_follow_combined_restrictions(authed, catalog):
    generation_id = await to_products_step(authed, catalog, ["vegan", "gluten"])

    assert await category_names(authed, generation_id) == {"Овочі", "Крупи та борошно"}


@req("FR-B2")
async def test_every_offered_category_has_at_least_one_offered_product(authed, catalog):
    generation_id = await to_products_step(authed, catalog, ["vegan"])
    base = f"{API}/generations/{generation_id}"

    for category in (await authed.get(f"{base}/categories")).json():
        products = (await authed.get(f"{base}/products", params={"category_id": category["id"]})).json()
        assert products, f"категорія {category['name']} порожня"


async def test_categories_of_foreign_generation_return_404(authed, catalog, client_factory):
    generation_id = await to_products_step(authed, catalog)
    stranger = client_factory()
    await register(stranger)

    assert (await stranger.get(f"{API}/generations/{generation_id}/categories")).status_code == 404


async def test_huge_offset_in_generation_products_is_rejected(authed, catalog):
    generation_id = await to_products_step(authed, catalog)

    response = await authed.get(
        f"{API}/generations/{generation_id}/products", params={"offset": 99999999999999999999}
    )

    assert response.status_code == 422
