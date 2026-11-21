import pytest

from app.application.auth_service import AuthService
from app.application.user_service import UserService
from app.core.security import session_hash_from_token, verify_password
from app.domain.entities.recipe import Recipe
from app.domain.exceptions import (
    EmailAlreadyExistsError,
    InvalidCurrentPasswordError,
    InvalidUserNameError,
)
from tests.fakes import (
    FakeRecipeRepository,
    FakeSavedRecipeRepository,
    FakeSessionRepository,
    FakeUserRepository,
)
from tests.helpers import req


@pytest.fixture
def env():
    users, sessions = FakeUserRepository(), FakeSessionRepository()
    recipes = FakeRecipeRepository()
    saved = FakeSavedRecipeRepository(recipes)

    class Env:
        pass

    e = Env()
    e.users, e.sessions, e.recipes, e.saved = users, sessions, recipes, saved
    e.auth = AuthService(users, sessions)
    e.service = UserService(users, sessions, saved)
    return e


async def make_user(env, email="anna@example.com", name="Anna"):
    return await env.auth.register(name, email, "Passw0rd!")


@req("FR-A11")
async def test_update_name_only(env):
    user = await make_user(env)

    updated = await env.service.update_profile(user, name="Olena", email=None)

    assert updated.name == "Olena" and updated.email == "anna@example.com"


@req("FR-A11")
async def test_update_email_is_normalized(env):
    user = await make_user(env)

    updated = await env.service.update_profile(user, name=None, email="  New@Example.COM ")

    assert updated.email == "new@example.com"


@req("FR-A3")
async def test_update_email_to_existing_one_is_rejected(env):
    await make_user(env, "taken@example.com", "Taken")
    user = await make_user(env, "anna@example.com")

    with pytest.raises(EmailAlreadyExistsError):
        await env.service.update_profile(user, name=None, email="TAKEN@example.com")


async def test_update_email_to_own_email_is_allowed(env):
    user = await make_user(env)

    updated = await env.service.update_profile(user, name=None, email="ANNA@example.com")

    assert updated.email == "anna@example.com"


@req("FR-A6")
async def test_update_name_with_invalid_value_raises(env):
    user = await make_user(env)

    with pytest.raises(InvalidUserNameError):
        await env.service.update_profile(user, name="  a ", email=None)


@req("FR-A11")
async def test_change_password_requires_correct_current_password(env):
    user = await make_user(env)
    old_hash = user.password_hash

    with pytest.raises(InvalidCurrentPasswordError):
        await env.service.change_password(user, "WrongPass1!", "NewPassw0rd!", None)

    assert user.password_hash == old_hash


@req("FR-A9", "FR-A11")
async def test_change_password_stores_new_hash(env):
    user = await make_user(env)

    await env.service.change_password(user, "Passw0rd!", "NewPassw0rd!", None)

    assert await verify_password("NewPassw0rd!", user.password_hash)
    assert not await verify_password("Passw0rd!", user.password_hash)


@req("FR-A11", "NFR-3")
async def test_change_password_keeps_current_session_and_drops_others(env):
    user = await make_user(env)
    current = await env.auth.create_session(user)
    other = await env.auth.create_session(user)

    await env.service.change_password(user, "Passw0rd!", "NewPassw0rd!", current)

    assert session_hash_from_token(current) in env.sessions.sessions
    assert session_hash_from_token(other) not in env.sessions.sessions


async def test_change_password_without_current_token_drops_all_sessions(env):
    user = await make_user(env)
    await env.auth.create_session(user)

    await env.service.change_password(user, "Passw0rd!", "NewPassw0rd!", None)

    assert env.sessions.sessions == {}


async def test_change_password_does_not_touch_other_users_sessions(env):
    user = await make_user(env)
    stranger = await make_user(env, "o@example.com", "Olga")
    stranger_token = await env.auth.create_session(stranger)

    await env.service.change_password(user, "Passw0rd!", "NewPassw0rd!", None)

    assert session_hash_from_token(stranger_token) in env.sessions.sessions


async def test_delete_account_removes_user_sessions_and_saved_recipes(env):
    user = await make_user(env)
    await env.auth.create_session(user)
    recipe = await env.recipes.save(
        Recipe(title="T", description="D", ingredients="I", instructions="S", cooking_time=5)
    )
    await env.saved.save(user.id, recipe.id)

    await env.service.delete_account(user)

    assert user.id not in env.users.users
    assert env.sessions.sessions == {}
    assert env.saved.links == set()
    assert env.recipes.recipes == {}
