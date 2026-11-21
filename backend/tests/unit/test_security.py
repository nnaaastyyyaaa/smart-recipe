import hashlib

import pytest

import base64
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from app.core.config import JWT_SECRET
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    decode_access_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    session_hash_from_token,
    verify_password,
)
from tests.helpers import req


@req("FR-A9", "NFR-2")
async def test_password_hash_is_not_plain_text():
    hashed = await hash_password("Passw0rd!")

    assert hashed != "Passw0rd!"
    assert "Passw0rd!" not in hashed


@req("FR-A9", "NFR-2")
async def test_password_hash_uses_bcrypt_format():
    hashed = await hash_password("Passw0rd!")

    assert hashed.startswith("$2b$")
    assert len(hashed) == 60


@req("FR-A9", "NFR-2")
async def test_same_password_gives_different_hashes_unique_salt():
    first = await hash_password("Passw0rd!")
    second = await hash_password("Passw0rd!")

    assert first != second
    assert first[:29] != second[:29]


@req("FR-A8", "NFR-2")
async def test_verify_password_accepts_correct_and_rejects_wrong():
    hashed = await hash_password("Passw0rd!")

    assert await verify_password("Passw0rd!", hashed) is True
    assert await verify_password("passw0rd!", hashed) is False
    assert await verify_password("", hashed) is False


async def test_verify_password_returns_false_for_malformed_hash():
    assert await verify_password("Passw0rd!", "not-a-bcrypt-hash") is False
    assert await verify_password("Passw0rd!", "") is False


async def test_dummy_hash_is_valid_but_never_matches_real_passwords():
    assert DUMMY_PASSWORD_HASH.startswith("$2b$")
    assert await verify_password("Passw0rd!", DUMMY_PASSWORD_HASH) is False


@req("NFR-3")
def test_session_tokens_are_unique_and_long():
    tokens = {generate_session_token() for _ in range(200)}

    assert len(tokens) == 200
    assert all(len(token) >= 43 for token in tokens)


@req("NFR-3")
def test_session_token_hash_is_sha256_hex_and_deterministic():
    token = generate_session_token()
    hashed = hash_session_token(token)

    assert hashed == hashlib.sha256(token.encode()).hexdigest()
    assert hashed == hash_session_token(token)
    assert len(hashed) == 64
    assert token not in hashed


def test_different_tokens_have_different_hashes():
    assert hash_session_token("a") != hash_session_token("b")


def in_future(minutes: int = 60) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def make_token(**overrides) -> str:
    claims = {"sub": str(uuid4()), "jti": "session-id", "exp": in_future()}
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, overrides.pop("_secret", JWT_SECRET), algorithm="HS256")


@req("NFR-3")
def test_jwt_roundtrip_contains_only_required_claims():
    user_id = uuid4()
    token = create_access_token(user_id, "sid-123", in_future())

    claims = decode_access_token(token)

    assert token.count(".") == 2
    assert set(claims) == {"sub", "jti", "iat", "exp"}
    assert claims["sub"] == str(user_id) and claims["jti"] == "sid-123"


@req("NFR-3")
def test_jwt_uses_hs256_header():
    header = jwt.get_unverified_header(create_access_token(uuid4(), "x", in_future()))

    assert header["alg"] == "HS256"


@req("NFR-3")
def test_jwt_expiry_matches_requested_session_expiry():
    expires = in_future(120)

    claims = decode_access_token(create_access_token(uuid4(), "x", expires))

    assert abs(claims["exp"] - expires.timestamp()) < 2


@req("NFR-3")
def test_tampered_jwt_payload_is_rejected():
    header, payload, signature = create_access_token(uuid4(), "x", in_future()).split(".")
    forged = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    forged["sub"] = str(uuid4())
    forged_payload = base64.urlsafe_b64encode(json.dumps(forged).encode()).rstrip(b"=").decode()

    assert decode_access_token(f"{header}.{forged_payload}.{signature}") is None


@req("NFR-3")
def test_jwt_signed_with_another_secret_is_rejected():
    forged = jwt.encode(
        {"sub": str(uuid4()), "jti": "x", "exp": in_future()},
        "another-secret-key-which-is-long-enough-123",
        algorithm="HS256",
    )

    assert decode_access_token(forged) is None


@req("NFR-3")
def test_expired_jwt_is_rejected():
    expired = jwt.encode(
        {"sub": str(uuid4()), "jti": "x", "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
        JWT_SECRET,
        algorithm="HS256",
    )

    assert decode_access_token(expired) is None


@req("NFR-3")
def test_unsigned_alg_none_jwt_is_rejected():
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    unsigned = f'{b64({"alg": "none", "typ": "JWT"})}.{b64({"sub": str(uuid4()), "jti": "x", "exp": 9999999999})}.'

    assert decode_access_token(unsigned) is None


@req("NFR-3")
@pytest.mark.parametrize("missing", ["sub", "jti", "exp"])
def test_jwt_without_required_claim_is_rejected(missing):
    claims = {"sub": str(uuid4()), "jti": "x", "exp": in_future()}
    claims.pop(missing)

    assert decode_access_token(jwt.encode(claims, JWT_SECRET, algorithm="HS256")) is None


@req("NFR-3")
@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c", "....", "Bearer x", "ey" * 40])
def test_garbage_is_not_a_valid_jwt(garbage):
    assert decode_access_token(garbage) is None
    assert session_hash_from_token(garbage) is None


@req("NFR-3")
def test_session_hash_from_token_hashes_jti():
    token = create_access_token(uuid4(), "my-session", in_future())

    assert session_hash_from_token(token) == hash_session_token("my-session")
