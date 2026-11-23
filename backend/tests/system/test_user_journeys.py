"""Системні тести: наскрізні сценарії кінцевого користувача (HTTP + PostgreSQL).

Імітують те, що робитиме фронтенд: реєстрація -> «Почати генерацію» ->
обмеження -> продукти -> варіанти -> рецепт -> збереження -> вихід.
"""
import asyncio

from sqlalchemy import func, select

from app.infrastructure.database.models import RecipeModel, SessionModel, UserModel
from app.infrastructure.generation.in_memory_generation_session_repository import (
    InMemoryGenerationSessionRepository,
)
from tests.helpers import API, PASSWORD, register, req, set_restrictions, start_generation


def code(response):
    detail = response.json().get("detail")
    return detail.get("code") if isinstance(detail, dict) else None


@req("FR-A1", "FR-A10", "FR-A12", "FR-A14", "FR-B1", "FR-B2", "FR-B3", "FR-B4", "FR-G1", "FR-G2", "FR-G5", "FR-G6", "FR-S1")
async def test_scenario_full_path_from_registration_to_saved_recipe(client, catalog, fake_ai):
    
    user = await register(client, name="Anna", email="anna@example.com")
    assert (await client.get(f"{API}/auth/me")).json()["email"] == "anna@example.com"

   
    generation_id = await start_generation(client)
    blocked = await client.get(f"{API}/generations/{generation_id}/products")
    assert blocked.status_code == 409

   
    await set_restrictions(client, generation_id, [catalog.restrictions["vegan"]])
    offered = (await client.get(f"{API}/generations/{generation_id}/products", params={"limit": 12})).json()
    assert {p["name"] for p in offered} == {"Помідор", "Огірок", "Морква", "Картопля", "Рис", "Борошно", "Макарони"}

    
    categories = (await client.get(f"{API}/generations/{generation_id}/categories")).json()
    assert {c["name"] for c in categories} == {"Овочі", "Крупи та борошно"}

   
    veg = (await client.get(
        f"{API}/generations/{generation_id}/products", params={"category_id": catalog.categories["veg"]}
    )).json()
    assert len(veg) == 4

    
    chosen = [catalog.products["tomato"], catalog.products["carrot"], catalog.products["rice"]]
    too_few = await client.post(f"{API}/generations/{generation_id}/suggestions", json={"product_ids": chosen[:1]})
    assert too_few.status_code == 422
    suggestions = await client.post(f"{API}/generations/{generation_id}/suggestions", json={"product_ids": chosen})
    assert suggestions.status_code == 200 and 1 <= len(suggestions.json()["items"]) <= 8

    
    assert [r.name for r in fake_ai.suggest_calls[0][1]] == ["Веганське"]

   
    picked = suggestions.json()["items"][0]
    full = await client.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": picked["id"]})
    assert full.status_code == 200
    recipe = full.json()
    assert recipe["ingredients"] and recipe["instructions"] and recipe["cooking_time"] >= 1

   
    saved = await client.post(f"{API}/recipes/saved", json=recipe)
    assert saved.status_code == 201
    listing = (await client.get(f"{API}/recipes/saved")).json()
    assert [r["title"] for r in listing] == [recipe["title"]]
    assert (await client.get(f"{API}/recipes/saved/{saved.json()['id']}")).json()["instructions"] == recipe["instructions"]
    assert (await client.delete(f"{API}/recipes/saved/{saved.json()['id']}")).status_code == 204
    assert (await client.get(f"{API}/recipes/saved")).json() == []

    
    assert (await client.post(f"{API}/auth/logout")).status_code == 204
    assert (await client.get(f"{API}/auth/me")).status_code == 401
    relogin = await client.post(f"{API}/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert relogin.status_code == 200


@req("FR-B1", "FR-B2")
async def test_scenario_each_new_generation_asks_restrictions_again(authed, catalog):
    first = await start_generation(authed)
    await set_restrictions(authed, first, [catalog.restrictions["vegan"]])
    assert len((await authed.get(f"{API}/generations/{first}/products")).json()) == 7

   
    second = await start_generation(authed)
    state = (await authed.get(f"{API}/generations/{second}")).json()
    assert state["status"] == "awaiting_restrictions" and state["restrictions"] == []
    assert (await authed.get(f"{API}/generations/{second}/products")).status_code == 409

    await set_restrictions(authed, second, [])
    assert len((await authed.get(f"{API}/generations/{second}/products")).json()) == 11


@req("FR-B1", "FR-B2")
async def test_scenario_user_goes_back_and_changes_restrictions(authed, catalog):
    generation_id = await start_generation(authed)
    await set_restrictions(authed, generation_id, [])
    await authed.post(
        f"{API}/generations/{generation_id}/suggestions",
        json={"product_ids": catalog.ids("tomato", "milk")},
    )

    
    await set_restrictions(authed, generation_id, [catalog.restrictions["vegan"]])

    retry = await authed.post(
        f"{API}/generations/{generation_id}/suggestions",
        json={"product_ids": catalog.ids("tomato", "milk")},
    )
    assert retry.status_code == 422 and code(retry) == "PRODUCTS_VIOLATE_RESTRICTIONS"
    ok = await authed.post(
        f"{API}/generations/{generation_id}/suggestions",
        json={"product_ids": catalog.ids("tomato", "rice")},
    )
    assert ok.status_code == 200


@req("FR-G2", "FR-G3")
async def test_scenario_show_more_recipes_with_pagination(authed, catalog, fake_ai):
    fake_ai.recipe_count = 16
    generation_id = await start_generation(authed)
    await set_restrictions(authed, generation_id, [])

    first = (await authed.post(
        f"{API}/generations/{generation_id}/suggestions",
        json={"product_ids": catalog.ids("tomato", "cucumber", "carrot", "potato", "rice")},
    )).json()
    assert len(first["items"]) == 8 and first["total_pages"] == 2

    second = (await authed.get(f"{API}/generations/{generation_id}/suggestions", params={"page": 2})).json()
    assert len(second["items"]) == 8

    titles = [i["title"] for i in first["items"] + second["items"]]
    assert len(set(titles)) == 16

    last = await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": second["items"][-1]["id"]})
    assert last.status_code == 200 and last.json()["title"] == second["items"][-1]["title"]


@req("FR-G4")
async def test_scenario_no_recipes_found_then_user_changes_basket(authed, catalog, fake_ai):
    generation_id = await start_generation(authed)
    await set_restrictions(authed, generation_id, [catalog.restrictions["vegan"]])
    fake_ai.custom_suggestions = []

    none_found = await authed.post(
        f"{API}/generations/{generation_id}/suggestions",
        json={"product_ids": catalog.ids("tomato", "flour")},
    )
    assert none_found.status_code == 422 and code(none_found) == "NO_SUITABLE_RECIPES"

    fake_ai.custom_suggestions = None
    retry = await authed.post(
        f"{API}/generations/{generation_id}/suggestions",
        json={"product_ids": catalog.ids("tomato", "flour", "rice")},
    )
    assert retry.status_code == 200


@req("FR-A11", "NFR-3")
async def test_scenario_password_change_with_two_devices(client_factory):
    laptop, phone = client_factory(), client_factory()
    user = await register(laptop, email="dev@example.com")
    await phone.post(f"{API}/auth/login", json={"email": user["email"], "password": PASSWORD})

    wrong = await laptop.patch(f"{API}/users/me/password", json={"current_password": "Nope1234!", "new_password": "NewPassw0rd!"})
    assert wrong.status_code == 400

    changed = await laptop.patch(f"{API}/users/me/password", json={"current_password": PASSWORD, "new_password": "NewPassw0rd!"})
    assert changed.status_code == 204
    assert (await laptop.get(f"{API}/auth/me")).status_code == 200
    assert (await phone.get(f"{API}/auth/me")).status_code == 401

    again = await phone.post(f"{API}/auth/login", json={"email": user["email"], "password": "NewPassw0rd!"})
    assert again.status_code == 200


async def test_scenario_account_deletion_removes_all_user_data(authed, catalog, db):
    generation_id = await start_generation(authed)
    await set_restrictions(authed, generation_id, [])
    page = (await authed.post(
        f"{API}/generations/{generation_id}/suggestions", json={"product_ids": catalog.ids("tomato", "carrot")}
    )).json()
    recipe = (await authed.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": page["items"][0]["id"]})).json()
    await authed.post(f"{API}/recipes/saved", json=recipe)

    assert (await authed.delete(f"{API}/users/me")).status_code == 204

    for model in (UserModel, SessionModel, RecipeModel):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    assert (await authed.get(f"{API}/generations/{generation_id}")).status_code == 401


@req("FR-A12")
async def test_scenario_two_users_work_in_parallel_without_interference(client_factory, catalog, fake_ai):
    async def journey(name: str, restriction: str | None):
        client = client_factory()
        await register(client, name=name)
        generation_id = await start_generation(client)
        await set_restrictions(client, generation_id, [catalog.restrictions[restriction]] if restriction else [])
        products = (await client.get(f"{API}/generations/{generation_id}/products")).json()
        page = (await client.post(
            f"{API}/generations/{generation_id}/suggestions",
            json={"product_ids": [products[0]["id"], products[1]["id"]]},
        )).json()
        recipe = (await client.post(f"{API}/generations/{generation_id}/recipe", json={"suggestion_id": page["items"][0]["id"]})).json()
        await client.post(f"{API}/recipes/saved", json={**recipe, "title": f"Рецепт {name}"})
        return client, {p["name"] for p in products}

    (a, a_products), (b, b_products) = await asyncio.gather(journey("Anna", "vegan"), journey("Boris", None))

    assert len(a_products) == 7 and len(b_products) == 11
    assert [r["title"] for r in (await a.get(f"{API}/recipes/saved")).json()] == ["Рецепт Anna"]
    assert [r["title"] for r in (await b.get(f"{API}/recipes/saved")).json()] == ["Рецепт Boris"]


@req("NFR-1")
async def test_scenario_backend_restart_loses_generation_but_user_can_continue(authed, api_app, catalog):
    generation_id = await start_generation(authed)
    await set_restrictions(authed, generation_id, [])

    api_app.state.generation_sessions = InMemoryGenerationSessionRepository() 

    lost = await authed.get(f"{API}/generations/{generation_id}/products")
    assert lost.status_code == 404 and code(lost) == "GENERATION_NOT_FOUND"

    assert (await authed.get(f"{API}/auth/me")).status_code == 200
    fresh = await start_generation(authed)
    assert (await set_restrictions(authed, fresh, [])).status_code == 200
