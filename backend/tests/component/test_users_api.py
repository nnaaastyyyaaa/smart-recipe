"""Компонентні тести профілю: перегляд, зміна даних/пароля, видалення акаунта."""
import pytest
from sqlalchemy import func, select

from app.infrastructure.database.models import RecipeModel, SessionModel, UserModel
from tests.helpers import API, PASSWORD, register, req

RECIPE = {
    "title": "Омлет", "description": "Опис", "ingredients": "Яйця — 2 шт",
    "instructions": "Смажити", "cooking_time": 10,
}


@req("FR-A10", "FR-A11")
async def test_get_my_profile(authed):
    response = await authed.get(f"{API}/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": authed.user["id"], "name": authed.user["name"], "email": authed.user["email"],
    }


async def test_profile_endpoints_require_authentication(client):
    assert (await client.get(f"{API}/auth/me")).status_code == 401
    assert (await client.patch(f"{API}/users/me", json={"name": "Anna"})).status_code == 401
    assert (await client.patch(f"{API}/users/me/password", json={})).status_code == 401
    assert (await client.delete(f"{API}/users/me")).status_code == 401


@req("FR-A11")
async def test_update_name(authed):
    response = await authed.patch(f"{API}/users/me", json={"name": "Olena"})

    assert response.status_code == 200 and response.json()["name"] == "Olena"
    assert (await authed.get(f"{API}/auth/me")).json()["name"] == "Olena"


@req("FR-A11")
async def test_update_email_is_normalized_and_persisted(authed):
    response = await authed.patch(f"{API}/users/me", json={"email": "New.Mail@Example.com"})

    assert response.status_code == 200
    assert response.json()["email"] == "new.mail@example.com"


@req("FR-A3")
async def test_update_email_to_taken_one_returns_409(authed, client_factory):
    await register(client_factory(), email="taken@example.com")

    response = await authed.patch(f"{API}/users/me", json={"email": "Taken@Example.com"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Користувач із таким email уже існує."


@req("FR-A6")
@pytest.mark.parametrize("name", ["A", "A" * 25, " a ", "  "])
async def test_update_name_invalid_returns_422(authed, name):
    response = await authed.patch(f"{API}/users/me", json={"name": name})

    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{}, {"role": "admin"}, {"name": "Anna", "id": "x"}])
async def test_update_rejects_empty_or_unknown_fields(authed, payload):
    assert (await authed.patch(f"{API}/users/me", json=payload)).status_code == 422

@req("FR-A11")
async def test_change_password_requires_correct_current_password(authed):
    response = await authed.patch(
        f"{API}/users/me/password",
        json={"current_password": "WrongPass1!", "new_password": "NewPassw0rd!"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Невірний поточний пароль."


@req("FR-A11", "FR-A9")
async def test_change_password_then_login_with_new_only(authed, client_factory):
    response = await authed.patch(
        f"{API}/users/me/password",
        json={"current_password": PASSWORD, "new_password": "NewPassw0rd!"},
    )
    assert response.status_code == 204

    fresh = client_factory()
    old = await fresh.post(f"{API}/auth/login", json={"email": authed.user["email"], "password": PASSWORD})
    new = await fresh.post(f"{API}/auth/login", json={"email": authed.user["email"], "password": "NewPassw0rd!"})

    assert old.status_code == 401 and new.status_code == 200


@req("FR-A4", "FR-A5", "FR-A11")
@pytest.mark.parametrize("new_password", ["short1!", "a" * 17, "Пароль1234"])
async def test_new_password_follows_registration_rules(authed, new_password):
    response = await authed.patch(
        f"{API}/users/me/password",
        json={"current_password": PASSWORD, "new_password": new_password},
    )

    assert response.status_code == 422


@req("FR-A11", "NFR-3")
async def test_change_password_signs_out_other_devices_but_not_current(client_factory):
    laptop, phone = client_factory(), client_factory()
    user = await register(laptop)
    await phone.post(f"{API}/auth/login", json={"email": user["email"], "password": PASSWORD})

    await laptop.patch(
        f"{API}/users/me/password",
        json={"current_password": PASSWORD, "new_password": "NewPassw0rd!"},
    )

    assert (await laptop.get(f"{API}/auth/me")).status_code == 200
    assert (await phone.get(f"{API}/auth/me")).status_code == 401

async def test_delete_account_removes_everything_and_signs_out(authed, client_factory, db):
    saved = await authed.post(f"{API}/recipes/saved", json=RECIPE)
    assert saved.status_code == 201

    response = await authed.delete(f"{API}/users/me")

    assert response.status_code == 204
    assert (await authed.get(f"{API}/auth/me")).status_code == 401
    assert await db.scalar(select(func.count()).select_from(UserModel)) == 0
    assert await db.scalar(select(func.count()).select_from(SessionModel)) == 0
    assert await db.scalar(select(func.count()).select_from(RecipeModel)) == 0

    relogin = await client_factory().post(
        f"{API}/auth/login", json={"email": authed.user["email"], "password": PASSWORD}
    )
    assert relogin.status_code == 401


async def test_delete_account_does_not_touch_other_users(authed, client_factory, db):
    other = client_factory()
    await register(other)
    await other.post(f"{API}/recipes/saved", json=RECIPE)

    await authed.delete(f"{API}/users/me")

    assert (await other.get(f"{API}/auth/me")).status_code == 200
    assert len((await other.get(f"{API}/recipes/saved")).json()) == 1
