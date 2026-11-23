"""Системні тести безпеки: контроль доступу, CORS, поведінка при зловмисних даних."""
from uuid import uuid4

import pytest

from tests.helpers import API, PASSWORD, register, req, user_payload

PROTECTED = [
    ("GET", "/auth/me", None),
    ("GET", "/auth/me", None),
    ("PATCH", "/users/me", {"name": "Anna"}),
    ("PATCH", "/users/me/password", {"current_password": "x", "new_password": "NewPassw0rd!"}),
    ("DELETE", "/users/me", None),
    ("GET", "/categories", None),
    ("GET", "/categories/1", None),
    ("GET", "/dietary-restrictions", None),
    ("GET", "/dietary-restrictions/1", None),
    ("GET", "/products", None),
    ("GET", "/products/1", None),
    ("GET", "/products/1/restrictions", None),
    ("POST", "/generations", None),
    ("GET", f"/generations/{uuid4()}", None),
    ("PUT", f"/generations/{uuid4()}/restrictions", {"restriction_ids": []}),
    ("GET", f"/generations/{uuid4()}/categories", None),
    ("GET", f"/generations/{uuid4()}/products", None),
    ("POST", f"/generations/{uuid4()}/suggestions", {"product_ids": [1, 2]}),
    ("GET", f"/generations/{uuid4()}/suggestions", None),
    ("POST", f"/generations/{uuid4()}/recipe", {"suggestion_id": 0}),
    ("POST", "/recipes/saved", {"title": "t", "description": "d", "ingredients": "i", "instructions": "s", "cooking_time": 5}),
    ("GET", "/recipes/saved", None),
    ("GET", "/recipes/saved/1", None),
    ("DELETE", "/recipes/saved/1", None),
]


@req("FR-A1", "FR-B1", "NFR-3")
@pytest.mark.parametrize("method,path,body", PROTECTED, ids=[f"{m} {p[:40]}" for m, p, _ in PROTECTED])
async def test_guest_cannot_use_protected_endpoint(client, method, path, body):
    response = await client.request(method, f"{API}{path}", json=body)

    assert response.status_code == 401
    assert response.json()["detail"] == "Не авторизовано."


@req("FR-A1")
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/health", None),
        ("POST", "/auth/register", user_payload()),
        ("POST", "/auth/login", {"email": "x@example.com", "password": "x"}),
        ("POST", "/auth/logout", None),
    ],
)
async def test_public_endpoints_are_available_to_guests(client, method, path, body):
    response = await client.request(method, f"{API}{path}", json=body)

    assert response.status_code in (200, 201, 204, 401)
    assert response.status_code != 403


@req("NFR-3")
async def test_cookie_of_deleted_account_stops_working(client, client_factory):
    user = await register(client)
    stolen = client.cookies.get("sid")
    await client.delete(f"{API}/users/me")

    attacker = client_factory()
    attacker.cookies.set("sid", stolen)

    assert (await attacker.get(f"{API}/auth/me")).status_code == 401


@req("NFR-3")
async def test_stolen_token_is_useless_after_logout(authed, client_factory):
    stolen = authed.cookies.get("sid")
    await authed.post(f"{API}/auth/logout")

    attacker = client_factory()
    attacker.cookies.set("sid", stolen)

    assert (await attacker.get(f"{API}/recipes/saved")).status_code == 401


@req("NFR-2")
async def test_responses_never_expose_password_or_hash(authed):
    bodies = [
        (await authed.get(f"{API}/auth/me")).text,
        (await authed.get(f"{API}/users/me")).text,
        (await authed.patch(f"{API}/users/me", json={"name": "Olena"})).text,
    ]

    for body in bodies:
        assert "password" not in body.lower()
        assert "$2b$" not in body


@pytest.mark.parametrize(
    "email",
    ["' OR '1'='1", "admin'--", "a@b.com'; DROP TABLE users;--", "<script>alert(1)</script>@x.com"],
)
async def test_injection_strings_in_login_do_not_cause_server_errors(client, email):
    response = await client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})

    assert response.status_code in (401, 422)


async def test_injection_in_registration_name_is_stored_literally(client, db):
    from sqlalchemy import func, select

    from app.infrastructure.database.models import UserModel

    payload = user_payload(name="'; DROP TABLE users;--")
    response = await client.post(f"{API}/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["name"] == "'; DROP TABLE users;--"
    assert await db.scalar(select(func.count()).select_from(UserModel)) == 1


async def test_malformed_json_returns_422_not_500(client):
    response = await client.post(
        f"{API}/auth/login", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 422


async def test_wrong_http_method_returns_405(authed):
    assert (await authed.put(f"{API}/auth/me")).status_code == 405
    assert (await authed.delete(f"{API}/products")).status_code == 405


async def test_unknown_endpoint_returns_404(client):
    assert (await client.get(f"{API}/no-such-endpoint")).status_code == 404


async def test_removed_endpoints_are_not_reachable(authed):
    assert (await authed.get(f"{API}/users/me/dietary-restrictions")).status_code in (404, 405)
    assert (await authed.post(f"{API}/recipes/suggestions", json={"product_ids": [1, 2]})).status_code in (404, 405)
    assert (await authed.post(f"{API}/recipes/generate", json={})).status_code in (404, 405)

async def test_cors_allows_frontend_origin_with_credentials(client):
    response = await client.options(
        f"{API}/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_cors_rejects_unknown_origin(client):
    response = await client.options(
        f"{API}/auth/login",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert "access-control-allow-origin" not in response.headers


async def test_cors_exposes_total_count_header_to_frontend(authed):
    response = await authed.get(
        f"{API}/recipes/saved", headers={"Origin": "http://localhost:3000"}
    )

    assert "x-total-count" in response.headers["access-control-expose-headers"].lower()
