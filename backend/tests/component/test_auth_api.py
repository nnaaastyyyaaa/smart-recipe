"""Компонентні тести автентифікації: API + PostgreSQL."""
import hashlib

import pytest
from sqlalchemy import func, select

from app.infrastructure.database.models import SessionModel, UserModel
from tests.helpers import API, PASSWORD, register, req, user_payload


async def count(db, model) -> int:
    return await db.scalar(select(func.count()).select_from(model))


@req("FR-A1", "FR-A2", "FR-A10")
async def test_register_creates_account_and_logs_in(client, db):
    payload = user_payload(name="Anna", email="Anna@Example.com")

    response = await client.post(f"{API}/auth/register", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Anna"
    assert body["email"] == "anna@example.com" 
    assert set(body) == {"id", "name", "email"} 
    assert client.cookies.get("sid")

    me = await client.get(f"{API}/auth/me")
    assert me.status_code == 200 and me.json() == body


@req("NFR-3")
async def test_register_sets_httponly_samesite_cookie(client):
    response = await client.post(f"{API}/auth/register", json=user_payload())

    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith("sid=")
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie


@req("FR-A9", "NFR-2")
async def test_password_is_stored_only_as_salted_bcrypt_hash(client, db):
    await client.post(f"{API}/auth/register", json=user_payload(email="a@example.com"))
    await client.post(f"{API}/auth/register", json=user_payload(email="b@example.com"))

    hashes = (await db.scalars(select(UserModel.password_hash))).all()

    assert len(hashes) == 2
    assert all(h.startswith("$2b$") and PASSWORD not in h for h in hashes)
    assert hashes[0] != hashes[1]


@req("NFR-3")
async def test_cookie_is_jwt_and_session_id_is_stored_hashed(client, db):
    from app.core.security import decode_access_token

    await client.post(f"{API}/auth/register", json=user_payload())
    token = client.cookies.get("sid")
    claims = decode_access_token(token)

    stored = (await db.scalars(select(SessionModel.token_hash))).all()

    assert token.count(".") == 2 
    assert claims is not None
    assert stored == [hashlib.sha256(claims["jti"].encode()).hexdigest()]
    assert token not in stored and claims["jti"] not in stored


@req("FR-A3")
@pytest.mark.parametrize("variant", ["same", "UPPER", "padded"])
async def test_duplicate_email_is_rejected(client, client_factory, db, variant):
    await client.post(f"{API}/auth/register", json=user_payload(email="dup@example.com"))
    email = {"same": "dup@example.com", "UPPER": "DUP@EXAMPLE.COM", "padded": " dup@example.com "}[variant]

    other = client_factory()
    response = await other.post(f"{API}/auth/register", json=user_payload(email=email))

    assert response.status_code == 409
    assert response.json()["detail"] == "Користувач із таким email уже існує."
    assert await count(db, UserModel) == 1
    assert not other.cookies.get("sid")


@req("FR-A4")
@pytest.mark.parametrize("password", ["Short1!", "a" * 17, ""])
async def test_register_rejects_wrong_password_length(client, db, password):
    response = await client.post(f"{API}/auth/register", json=user_payload(password=password))

    assert response.status_code == 422
    assert await count(db, UserModel) == 0


@req("FR-A4")
@pytest.mark.parametrize("password", ["a" * 8, "a" * 16])
async def test_register_accepts_password_boundaries(client, password):
    response = await client.post(f"{API}/auth/register", json=user_payload(password=password))

    assert response.status_code == 201


@req("FR-A5")
@pytest.mark.parametrize("password", ["Пароль1234", "Passw0rdї!", "Pass word1"])
async def test_register_rejects_non_english_password(client, db, password):
    response = await client.post(f"{API}/auth/register", json=user_payload(password=password))

    assert response.status_code == 422
    assert await count(db, UserModel) == 0


@req("FR-A6")
@pytest.mark.parametrize("name", ["A", "A" * 25, ""])
async def test_register_rejects_wrong_name_length(client, db, name):
    response = await client.post(f"{API}/auth/register", json=user_payload(name=name))

    assert response.status_code == 422
    assert await count(db, UserModel) == 0


@req("FR-A6")
@pytest.mark.parametrize("name", ["Al", "A" * 24, "Анастасія"])
async def test_register_accepts_name_boundaries(client, name):
    assert (await client.post(f"{API}/auth/register", json=user_payload(name=name))).status_code == 201


@req("FR-A2")
@pytest.mark.parametrize("missing", ["name", "email", "password"])
async def test_register_requires_all_fields(client, missing):
    payload = user_payload()
    payload.pop(missing)

    assert (await client.post(f"{API}/auth/register", json=payload)).status_code == 422


@req("FR-A2")
async def test_register_rejects_invalid_email(client):
    response = await client.post(f"{API}/auth/register", json=user_payload(email="not-an-email"))

    assert response.status_code == 422


@req("FR-A6")
@pytest.mark.parametrize("name", [" a ", "  "])
async def test_register_name_that_is_too_short_after_trim_returns_422(client, name):
    response = await client.post(f"{API}/auth/register", json=user_payload(name=name))

    assert response.status_code == 422


@req("FR-A3")
async def test_concurrent_registration_with_same_email_gives_one_201_and_one_409(client_factory):
    import asyncio

    a, b = client_factory(), client_factory()
    payload = user_payload(email="race@example.com")

    results = await asyncio.gather(
        a.post(f"{API}/auth/register", json=payload),
        b.post(f"{API}/auth/register", json=payload),
    )

    assert sorted(r.status_code for r in results) == [201, 409]


@req("FR-A1")
async def test_login_with_correct_credentials(client_factory):
    first = client_factory()
    user = await register(first, email="login@example.com")

    second = client_factory()
    response = await second.post(f"{API}/auth/login", json={"email": "LOGIN@example.com", "password": user["password"]})

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert second.cookies.get("sid")
    assert (await second.get(f"{API}/auth/me")).status_code == 200


@req("FR-A7")
async def test_login_unknown_email_gives_generic_error(client):
    response = await client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})

    assert response.status_code == 401
    assert response.json()["detail"] == "Невірний email або пароль."
    assert not client.cookies.get("sid")


@req("FR-A8")
async def test_login_wrong_password_gives_generic_error(client, client_factory):
    user = await register(client_factory(), email="wp@example.com")

    response = await client.post(f"{API}/auth/login", json={"email": user["email"], "password": "WrongPass1!"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Невірний email або пароль."


@req("FR-A7", "FR-A8")
async def test_login_errors_are_identical_for_unknown_email_and_wrong_password(client, client_factory):
    user = await register(client_factory(), email="same@example.com")

    unknown = await client.post(f"{API}/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    wrong = await client.post(f"{API}/auth/login", json={"email": user["email"], "password": "WrongPass1!"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


@pytest.mark.parametrize("payload", [{}, {"email": "a@b.com"}, {"password": "x"}, {"email": "bad", "password": "x"}])
async def test_login_validates_payload(client, payload):
    assert (await client.post(f"{API}/auth/login", json=payload)).status_code == 422


@req("NFR-3")
async def test_relogin_rotates_session_token(client, db):
    user = await register(client)
    old_token = client.cookies.get("sid")

    await client.post(f"{API}/auth/login", json={"email": user["email"], "password": user["password"]})
    new_token = client.cookies.get("sid")

    assert new_token != old_token
    assert await count(db, SessionModel) == 1 

@req("FR-A10")
async def test_me_requires_authentication(client):
    response = await client.get(f"{API}/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Не авторизовано."


@req("NFR-3")
@pytest.mark.parametrize("cookie", ["garbage", "a" * 43, ""])
async def test_me_rejects_forged_session_cookie(client, cookie):
    client.cookies.set("sid", cookie)

    assert (await client.get(f"{API}/auth/me")).status_code == 401


async def _expire_all_sessions(session_factory):
    from datetime import datetime, timedelta, timezone

    async with session_factory() as other:
        await other.execute(
            SessionModel.__table__.update().values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        await other.commit()


@req("NFR-3")
async def test_expired_session_is_rejected(client, session_factory):
    await register(client)
    await _expire_all_sessions(session_factory)

    response = await client.get(f"{API}/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Не авторизовано."


@req("NFR-3")
async def test_expired_sessions_do_not_accumulate_in_database(client_factory, db, session_factory):
    await register(client_factory(), email="abandoned@example.com")
    await _expire_all_sessions(session_factory)

    newcomer = client_factory()
    await register(newcomer, email="newcomer@example.com")

    assert await count(db, SessionModel) == 1

@req("FR-A14")
async def test_logout_ends_session_and_clears_cookie(client, db):
    await register(client)
    token = client.cookies.get("sid")

    response = await client.post(f"{API}/auth/logout")

    assert response.status_code == 204
    assert 'sid=""' in response.headers["set-cookie"] or "max-age=0" in response.headers["set-cookie"].lower()
    assert await count(db, SessionModel) == 0

    client.cookies.set("sid", token)
    assert (await client.get(f"{API}/auth/me")).status_code == 401


@req("FR-A14")
async def test_logout_only_affects_current_device(client_factory):
    phone, laptop = client_factory(), client_factory()
    user = await register(phone)
    await laptop.post(f"{API}/auth/login", json={"email": user["email"], "password": user["password"]})

    await phone.post(f"{API}/auth/logout")

    assert (await phone.get(f"{API}/auth/me")).status_code == 401
    assert (await laptop.get(f"{API}/auth/me")).status_code == 200


async def test_logout_without_session_is_idempotent(client):
    assert (await client.post(f"{API}/auth/logout")).status_code == 204


def forge(secret=None, **claims) -> str:
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    from app.core.config import JWT_SECRET

    payload = {"sub": "00000000-0000-0000-0000-000000000000", "jti": "x",
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    payload.update(claims)
    return pyjwt.encode(payload, secret or JWT_SECRET, algorithm="HS256")


@req("NFR-3")
async def test_jwt_claims_do_not_contain_personal_data(client):
    from app.core.security import decode_access_token

    await client.post(f"{API}/auth/register", json=user_payload(email="secret@example.com", name="Hidden"))

    claims = decode_access_token(client.cookies.get("sid"))

    assert set(claims) == {"sub", "jti", "iat", "exp"}
    assert "secret@example.com" not in str(claims) and "Hidden" not in str(claims)


@req("NFR-3")
async def test_jwt_lifetime_equals_session_ttl(client):
    from app.core.config import SESSION_TTL_MINUTES
    from app.core.security import decode_access_token
    import time

    await client.post(f"{API}/auth/register", json=user_payload())

    claims = decode_access_token(client.cookies.get("sid"))

    assert abs((claims["exp"] - time.time()) - SESSION_TTL_MINUTES * 60) < 30


@req("NFR-3")
async def test_jwt_tampered_signature_is_rejected(authed):
    header, payload, signature = authed.cookies.get("sid").split(".")
    authed.cookies.set("sid", f"{header}.{payload}.{signature[:-3]}abc")

    assert (await authed.get(f"{API}/auth/me")).status_code == 401


@req("NFR-3")
async def test_jwt_signed_with_other_secret_is_rejected(authed):
    from app.core.security import decode_access_token

    claims = decode_access_token(authed.cookies.get("sid"))
    authed.cookies.set("sid", forge("another-secret-key-which-is-long-enough-123", sub=claims["sub"], jti=claims["jti"]))

    assert (await authed.get(f"{API}/auth/me")).status_code == 401


@req("NFR-3")
async def test_correctly_signed_jwt_without_server_session_is_rejected(authed):
    from app.core.security import decode_access_token

    claims = decode_access_token(authed.cookies.get("sid"))
    authed.cookies.set("sid", forge(sub=claims["sub"], jti="not-a-real-session"))

    assert (await authed.get(f"{API}/auth/me")).status_code == 401


@req("NFR-3")
async def test_expired_jwt_is_rejected_even_if_session_row_is_alive(authed):
    from datetime import datetime, timedelta, timezone

    from app.core.security import decode_access_token

    claims = decode_access_token(authed.cookies.get("sid"))
    authed.cookies.set("sid", forge(sub=claims["sub"], jti=claims["jti"], exp=datetime.now(timezone.utc) - timedelta(seconds=5)))

    assert (await authed.get(f"{API}/auth/me")).status_code == 401


@req("NFR-3")
async def test_unsigned_jwt_is_rejected(authed):
    import base64
    import json

    def b64(data):
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    authed.cookies.set("sid", f'{b64({"alg": "none", "typ": "JWT"})}.{b64({"sub": authed.user["id"], "jti": "x", "exp": 9999999999})}.')

    assert (await authed.get(f"{API}/auth/me")).status_code == 401


@req("NFR-3")
async def test_jwt_of_one_user_cannot_be_used_with_session_of_another(client_factory):
    from app.core.security import decode_access_token

    first, second = client_factory(), client_factory()
    await register(first)
    victim = await register(second)
    first_claims = decode_access_token(first.cookies.get("sid"))
    victim_claims = decode_access_token(second.cookies.get("sid"))

    first.cookies.set("sid", forge(sub=first_claims["sub"], jti=victim_claims["jti"]))

    assert (await first.get(f"{API}/auth/me")).status_code == 401
    assert (await second.get(f"{API}/auth/me")).json()["id"] == victim["id"]


@req("NFR-3")
async def test_jwt_is_revoked_immediately_after_logout(authed, client_factory):
    stolen = authed.cookies.get("sid")
    await authed.post(f"{API}/auth/logout")

    thief = client_factory()
    thief.cookies.set("sid", stolen)

    assert (await thief.get(f"{API}/auth/me")).status_code == 401
