"""Компонентні тести «Улюблені рецепти»: збереження, перегляд, видалення."""
import pytest
from sqlalchemy import func, select

from app.infrastructure.database.models import RecipeModel
from app.infrastructure.database.models.associations import saved_recipes
from tests.helpers import API, register, req


def recipe(title="Омлет", **overrides):
    data = {
        "title": title,
        "description": "Ніжний омлет",
        "ingredients": "Яйця — 2 шт\nМолоко — 50 мл",
        "instructions": "1. Збити\n2. Посмажити",
        "cooking_time": 10,
    }
    data.update(overrides)
    return data


async def save(client, **kwargs):
    response = await client.post(f"{API}/recipes/saved", json=recipe(**kwargs))
    assert response.status_code == 201, response.text
    return response.json()


@req("FR-S1")
async def test_save_recipe_returns_stored_recipe_with_id(authed):
    response = await authed.post(f"{API}/recipes/saved", json=recipe())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert {k: v for k, v in body.items() if k != "id"} == recipe()


@req("FR-S1")
async def test_saved_recipe_text_fields_are_trimmed(authed):
    body = await save(authed, title="  Омлет  ", description="  опис ")

    assert body["title"] == "Омлет" and body["description"] == "опис"


@req("FR-S1")
@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""}, {"title": "   "}, {"title": "я" * 81}, {"description": ""},
        {"ingredients": ""}, {"instructions": ""}, {"cooking_time": 0}, {"cooking_time": -1},
        {"cooking_time": "багато"},
    ],
)
async def test_save_recipe_validation(authed, overrides):
    response = await authed.post(f"{API}/recipes/saved", json=recipe(**overrides))

    assert response.status_code == 422


async def test_save_recipe_requires_all_fields(authed):
    for missing in ("title", "description", "ingredients", "instructions", "cooking_time"):
        payload = recipe()
        payload.pop(missing)
        assert (await authed.post(f"{API}/recipes/saved", json=payload)).status_code == 422


@req("FR-S1")
async def test_title_of_exactly_80_chars_is_accepted(authed):
    assert len((await save(authed, title="я" * 80))["title"]) == 80


@req("FR-A12", "FR-A13")
async def test_list_returns_all_saved_recipes_of_user(authed):
    for index in range(15):
        await save(authed, title=f"Рецепт {index:02d}")

    response = await authed.get(f"{API}/recipes/saved")

    assert response.status_code == 200 and len(response.json()) == 15
    assert [r["title"] for r in response.json()] == sorted(r["title"] for r in response.json())


@req("FR-A12")
async def test_list_is_empty_for_new_user(authed):
    assert (await authed.get(f"{API}/recipes/saved")).json() == []


@req("FR-A12")
async def test_view_saved_recipe_details(authed):
    saved = await save(authed)

    response = await authed.get(f"{API}/recipes/saved/{saved['id']}")

    assert response.status_code == 200 and response.json() == saved


@req("FR-A12")
async def test_missing_saved_recipe_returns_404(authed):
    response = await authed.get(f"{API}/recipes/saved/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Збережений рецепт не знайдений."


@req("FR-A12")
async def test_delete_saved_recipe_removes_it_everywhere(authed, db):
    saved = await save(authed)

    response = await authed.delete(f"{API}/recipes/saved/{saved['id']}")

    assert response.status_code == 204
    assert (await authed.get(f"{API}/recipes/saved/{saved['id']}")).status_code == 404
    assert (await authed.get(f"{API}/recipes/saved")).json() == []
    assert await db.scalar(select(func.count()).select_from(RecipeModel)) == 0 
    assert await db.scalar(select(func.count()).select_from(saved_recipes)) == 0


@req("FR-A12")
async def test_delete_twice_returns_404_second_time(authed):
    saved = await save(authed)
    await authed.delete(f"{API}/recipes/saved/{saved['id']}")

    assert (await authed.delete(f"{API}/recipes/saved/{saved['id']}")).status_code == 404


@req("FR-A12")
async def test_delete_keeps_other_recipes(authed):
    first, second = await save(authed, title="А"), await save(authed, title="Б")

    await authed.delete(f"{API}/recipes/saved/{first['id']}")

    assert [r["id"] for r in (await authed.get(f"{API}/recipes/saved")).json()] == [second["id"]]


@req("FR-A12")
async def test_saving_same_dish_twice_creates_two_independent_entries(authed):
    first, second = await save(authed), await save(authed)

    assert first["id"] != second["id"]
    await authed.delete(f"{API}/recipes/saved/{first['id']}")
    assert (await authed.get(f"{API}/recipes/saved/{second['id']}")).status_code == 200


@req("FR-A12")
async def test_users_see_only_their_own_recipes(authed, client_factory):
    mine = await save(authed, title="Моя")
    stranger = client_factory()
    await register(stranger)
    theirs = await save(stranger, title="Чужа")

    assert [r["title"] for r in (await authed.get(f"{API}/recipes/saved")).json()] == ["Моя"]
    assert [r["title"] for r in (await stranger.get(f"{API}/recipes/saved")).json()] == ["Чужа"]
    assert (await authed.get(f"{API}/recipes/saved/{theirs['id']}")).status_code == 404
    assert (await stranger.get(f"{API}/recipes/saved/{mine['id']}")).status_code == 404


@req("FR-A12")
async def test_user_cannot_delete_foreign_recipe(authed, client_factory):
    mine = await save(authed)
    stranger = client_factory()
    await register(stranger)

    assert (await stranger.delete(f"{API}/recipes/saved/{mine['id']}")).status_code == 404
    assert (await authed.get(f"{API}/recipes/saved/{mine['id']}")).status_code == 200


async def test_saved_recipes_survive_logout_and_login(authed, client_factory):
    saved = await save(authed)
    await authed.post(f"{API}/auth/logout")

    again = client_factory()
    await again.post(
        f"{API}/auth/login", json={"email": authed.user["email"], "password": authed.user["password"]}
    )

    assert [r["id"] for r in (await again.get(f"{API}/recipes/saved")).json()] == [saved["id"]]

async def save_many(client, count):
    for index in range(count):
        await save(client, title=f"Рецепт {index:02d}")


@req("FR-A13")
async def test_saved_recipes_are_paginated_by_12(authed):
    await save_many(authed, 25)
    url = f"{API}/recipes/saved"

    pages = [
        (await authed.get(url, params={"limit": 12, "offset": offset})).json()
        for offset in (0, 12, 24, 36)
    ]
    everything = (await authed.get(url)).json()

    assert [len(p) for p in pages] == [12, 12, 1, 0]
    assert [r["id"] for p in pages for r in p] == [r["id"] for r in everything]
    assert [r["title"] for r in everything] == sorted(r["title"] for r in everything)


@req("FR-A13")
async def test_total_count_header_allows_client_to_compute_pages(authed):
    await save_many(authed, 25)

    response = await authed.get(f"{API}/recipes/saved", params={"limit": 12})

    assert response.headers["x-total-count"] == "25"
    assert len(response.json()) == 12 


@req("FR-A13")
async def test_total_count_is_per_user(authed, client_factory):
    await save_many(authed, 3)
    other = client_factory()
    await register(other)
    await save(other)

    assert (await authed.get(f"{API}/recipes/saved")).headers["x-total-count"] == "3"
    assert (await other.get(f"{API}/recipes/saved")).headers["x-total-count"] == "1"


@req("FR-A13")
async def test_total_count_is_zero_for_new_user(authed):
    response = await authed.get(f"{API}/recipes/saved")

    assert response.headers["x-total-count"] == "0" and response.json() == []


@req("FR-A13")
async def test_without_limit_the_whole_list_is_returned(authed):
    await save_many(authed, 15)

    assert len((await authed.get(f"{API}/recipes/saved")).json()) == 15


@req("FR-A13")
@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"offset": -1}, {"offset": 99999999999999999999}])
async def test_saved_recipes_pagination_is_validated(authed, params):
    assert (await authed.get(f"{API}/recipes/saved", params=params)).status_code == 422


@req("FR-A13")
async def test_deleting_recipe_updates_total_count(authed):
    await save_many(authed, 3)
    first = (await authed.get(f"{API}/recipes/saved")).json()[0]

    await authed.delete(f"{API}/recipes/saved/{first['id']}")

    assert (await authed.get(f"{API}/recipes/saved")).headers["x-total-count"] == "2"
