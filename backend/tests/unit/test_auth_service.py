from datetime import datetime, timedelta, timezone

import pytest

from app.application.auth_service import AuthService, normalize_email
from app.core.security import (
    decode_access_token,
    hash_session_token,
    session_hash_from_token,
    verify_password,
)
from app.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidUserNameError,
)
from tests.fakes import FakeSessionRepository, FakeUserRepository
from tests.helpers import req


@pytest.fixture
def users():
    return FakeUserRepository()


@pytest.fixture
def sessions():
    return FakeSessionRepository()


@pytest.fixture
def service(users, sessions):
    return AuthService(users, sessions)


def test_normalize_email_strips_and_lowercases():
    assert normalize_email("  Anna@Example.COM ") == "anna@example.com"


@req("FR-A1", "FR-A2", "FR-A9")
async def test_register_stores_normalized_email_and_hashed_password(service, users):
    user = await service.register("  Anna ", " Anna@Example.com ", "Passw0rd!")

    assert user.email == "anna@example.com"
    assert user.name == "Anna"
    assert user.password_hash != "Passw0rd!"
    assert await verify_password("Passw0rd!", user.password_hash)
    assert users.users[user.id] is user


@req("FR-A3")
@pytest.mark.parametrize("second_email", ["anna@example.com", "ANNA@example.com", " anna@example.com "])
async def test_register_rejects_duplicate_email_case_insensitively(service, second_email):
    await service.register("Anna", "anna@example.com", "Passw0rd!")

    with pytest.raises(EmailAlreadyExistsError):
        await service.register("Other", second_email, "Passw0rd!")


@req("FR-A9")
async def test_two_users_with_same_password_get_different_hashes(service):
    first = await service.register("Anna", "a@example.com", "Passw0rd!")
    second = await service.register("Olga", "o@example.com", "Passw0rd!")

    assert first.password_hash != second.password_hash


async def test_register_invalid_name_after_strip_raises_domain_error(service):
    with pytest.raises(InvalidUserNameError):
        await service.register("   ", "a@example.com", "Passw0rd!")


@req("FR-A1")
async def test_authenticate_success_is_case_insensitive_for_email(service):
    registered = await service.register("Anna", "anna@example.com", "Passw0rd!")

    user = await service.authenticate("ANNA@example.com", "Passw0rd!")

    assert user.id == registered.id


@req("FR-A7")
async def test_authenticate_unknown_email_raises_generic_error(service):
    with pytest.raises(InvalidCredentialsError) as error:
        await service.authenticate("nobody@example.com", "Passw0rd!")

    assert str(error.value) == "Невірний email або пароль."


@req("FR-A8")
async def test_authenticate_wrong_password_raises_same_generic_error(service):
    await service.register("Anna", "anna@example.com", "Passw0rd!")

    with pytest.raises(InvalidCredentialsError) as error:
        await service.authenticate("anna@example.com", "WrongPass1!")

    assert str(error.value) == "Невірний email або пароль."


@req("FR-A7", "FR-A8")
async def test_error_messages_do_not_reveal_whether_email_exists(service):
    await service.register("Anna", "anna@example.com", "Passw0rd!")

    with pytest.raises(InvalidCredentialsError) as unknown:
        await service.authenticate("nobody@example.com", "Passw0rd!")

    with pytest.raises(InvalidCredentialsError) as wrong:
        await service.authenticate("anna@example.com", "WrongPass1!")

    assert str(unknown.value) == str(wrong.value)


@req("NFR-3")
async def test_create_session_stores_only_token_hash(service, sessions):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")

    token = await service.create_session(user)
    claims = decode_access_token(token)

    assert session_hash_from_token(token) in sessions.sessions
    assert hash_session_token(claims["jti"]) in sessions.sessions
    assert token not in sessions.sessions and claims["jti"] not in sessions.sessions
    stored = sessions.sessions[session_hash_from_token(token)]
    assert stored.user_id == user.id
    assert stored.expires_at > datetime.now(timezone.utc)


@req("FR-A10", "NFR-3")
async def test_get_user_by_valid_session(service):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")
    token = await service.create_session(user)

    found = await service.get_user_by_session(token)

    assert found is not None and found.id == user.id


@req("NFR-3")
async def test_get_user_by_unknown_session_returns_none(service):
    assert await service.get_user_by_session("unknown-token") is None


@req("NFR-3")
async def test_expired_session_is_rejected_and_deleted(service, sessions):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")
    token = await service.create_session(user)
    sessions.sessions[session_hash_from_token(token)].expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    assert await service.get_user_by_session(token) is None
    assert session_hash_from_token(token) not in sessions.sessions


@req("FR-A14")
async def test_logout_invalidates_session(service):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")
    token = await service.create_session(user)

    await service.logout(token)

    assert await service.get_user_by_session(token) is None


async def test_logout_with_unknown_token_is_harmless(service):
    await service.logout("never-existed")


@req("NFR-3")
async def test_session_token_is_a_jwt_with_user_as_subject(service):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")

    token = await service.create_session(user)
    claims = decode_access_token(token)

    assert claims["sub"] == str(user.id)


@req("NFR-3")
async def test_each_login_gets_a_different_token(service):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")

    first, second = await service.create_session(user), await service.create_session(user)

    assert first != second
    assert (await service.get_user_by_session(first)).id == user.id
    assert (await service.get_user_by_session(second)).id == user.id


@req("NFR-3")
async def test_forged_jwt_with_unknown_session_is_rejected(service):
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    from app.core.config import JWT_SECRET

    user = await service.register("Anna", "anna@example.com", "Passw0rd!")
    forged = pyjwt.encode(
        {"sub": str(user.id), "jti": "never-created", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        JWT_SECRET, algorithm="HS256",
    )

    assert await service.get_user_by_session(forged) is None


@req("NFR-3")
async def test_jwt_of_another_user_with_stolen_session_id_is_rejected(service):
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    from app.core.config import JWT_SECRET

    victim = await service.register("Anna", "anna@example.com", "Passw0rd!")
    attacker = await service.register("Olga", "olga@example.com", "Passw0rd!")
    victim_jti = decode_access_token(await service.create_session(victim))["jti"]
    forged = pyjwt.encode(
        {"sub": str(attacker.id), "jti": victim_jti, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        JWT_SECRET, algorithm="HS256",
    )

    assert await service.get_user_by_session(forged) is None


@req("NFR-3")
async def test_logout_with_garbage_token_does_not_touch_sessions(service, sessions):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")
    await service.create_session(user)

    await service.logout("garbage")

    assert len(sessions.sessions) == 1


@req("NFR-3")
async def test_creating_a_session_purges_expired_sessions(service, sessions):
    user = await service.register("Anna", "anna@example.com", "Passw0rd!")
    old_token = await service.create_session(user)
    sessions.sessions[session_hash_from_token(old_token)].expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    fresh_token = await service.create_session(user)

    assert list(sessions.sessions) == [session_hash_from_token(fresh_token)]
