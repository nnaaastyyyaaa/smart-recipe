from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.entities.category import Category
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.generation_session import (
    GenerationSession,
    GenerationStatus,
    GenerationSuggestion,
)
from app.domain.entities.product import Product
from app.domain.entities.recipe import Recipe
from app.domain.entities.session import Session
from app.domain.entities.user import User
from app.domain.exceptions import (
    InvalidCategoryNameError,
    InvalidDietaryRestrictionNameError,
    InvalidProductNameError,
    InvalidRecipeCookingTimeError,
    InvalidRecipeDescriptionError,
    InvalidRecipeIngredientsError,
    InvalidRecipeInstructionsError,
    InvalidRecipeTitleError,
    InvalidUserNameError,
    InvalidUserPasswordHashError,
)
from tests.helpers import req


def make_user(name="Anna") -> User:
    return User(email="a@b.com", password_hash="hash", name=name)


@req("FR-A6")
@pytest.mark.parametrize("name", ["Al", "A" * 24, "Анна", "  Anna  "])
def test_user_accepts_valid_names(name):
    assert make_user(name).name == name.strip()


@req("FR-A6")
@pytest.mark.parametrize("name", ["", "A", "A" * 25, "   ", " a "])
def test_user_rejects_invalid_names(name):
    with pytest.raises(InvalidUserNameError):
        make_user(name)


def test_user_rename_validates_and_strips():
    user = make_user()
    user.rename("  Olena ")
    assert user.name == "Olena"

    with pytest.raises(InvalidUserNameError):
        user.rename("x")


def test_user_change_email_and_password_hash():
    user = make_user()
    user.change_email("new@b.com")
    user.update_password_hash("new-hash")

    assert user.email == "new@b.com"
    assert user.password_hash == "new-hash"

    with pytest.raises(InvalidUserPasswordHashError):
        user.update_password_hash("   ")


def test_user_ids_are_unique():
    assert make_user().id != make_user().id


@pytest.mark.parametrize(
    "factory,error",
    [
        (lambda name: Category(name=name), InvalidCategoryNameError),
        (lambda name: Product(name=name, category_id=1), InvalidProductNameError),
        (lambda name: DietaryRestriction(name=name), InvalidDietaryRestrictionNameError),
    ],
)
class TestCatalogEntityNames:
    def test_rejects_empty_and_blank(self, factory, error):
        for name in ("", "   "):
            with pytest.raises(error):
                factory(name)

    def test_rejects_over_60_chars(self, factory, error):
        with pytest.raises(error):
            factory("я" * 61)

    def test_accepts_boundary_and_strips(self, factory, error):
        assert factory("я" * 60).name == "я" * 60
        assert factory("  Молоко ").name == "Молоко"


def make_recipe(**overrides) -> Recipe:
    data = dict(
        title="Омлет",
        description="Опис",
        ingredients="Яйця",
        instructions="Смажити",
        cooking_time=10,
    )
    data.update(overrides)
    return Recipe(**data)


@req("FR-G6")
def test_recipe_valid_and_strips_fields():
    recipe = make_recipe(title="  Омлет ", description=" d ", ingredients=" i ", instructions=" s ")

    assert (recipe.title, recipe.description, recipe.ingredients, recipe.instructions) == (
        "Омлет", "d", "i", "s",
    )


@pytest.mark.parametrize(
    "overrides,error",
    [
        ({"title": "  "}, InvalidRecipeTitleError),
        ({"title": "я" * 81}, InvalidRecipeTitleError),
        ({"description": " "}, InvalidRecipeDescriptionError),
        ({"ingredients": ""}, InvalidRecipeIngredientsError),
        ({"instructions": ""}, InvalidRecipeInstructionsError),
        ({"cooking_time": 0}, InvalidRecipeCookingTimeError),
        ({"cooking_time": -5}, InvalidRecipeCookingTimeError),
    ],
)
def test_recipe_invariants(overrides, error):
    with pytest.raises(error):
        make_recipe(**overrides)


def test_recipe_title_boundary_80():
    assert len(make_recipe(title="я" * 80).title) == 80


@req("NFR-3")
def test_auth_session_expiry():
    now = datetime.now(timezone.utc)

    fresh = Session("h", uuid4(), expires_at=now + timedelta(minutes=5))
    old = Session("h", uuid4(), expires_at=now - timedelta(seconds=1))

    assert fresh.is_expired() is False
    assert old.is_expired() is True


def new_generation() -> GenerationSession:
    return GenerationSession.start(uuid4(), ttl_minutes=30)


@req("FR-B1")
def test_generation_starts_awaiting_restrictions():
    session = new_generation()

    assert session.status == GenerationStatus.AWAITING_RESTRICTIONS
    assert session.restrictions_selected is False
    assert session.suggestions == []
    assert session.is_expired() is False


@req("FR-B1")
def test_generation_empty_restrictions_is_a_valid_choice():
    session = new_generation()
    session.select_restrictions([])

    assert session.restrictions_selected is True
    assert session.status == GenerationStatus.AWAITING_PRODUCTS


def test_generation_status_progression():
    session = new_generation()
    session.select_restrictions([1])
    session.set_suggestions(
        [1, 2],
        [GenerationSuggestion("t", "d", 5, [1, 2])],
    )

    assert session.status == GenerationStatus.SUGGESTIONS_READY
    assert session.product_ids == [1, 2]


def test_changing_restrictions_resets_dependent_state_and_bumps_revision():
    session = new_generation()
    session.select_restrictions([1])
    revision = session.revision
    session.set_suggestions([1, 2], [GenerationSuggestion("t", "d", 5, [1, 2])])

    session.select_restrictions([2])

    assert session.restriction_ids == [2]
    assert session.product_ids == []
    assert session.suggestions == []
    assert session.revision == revision + 1
    assert session.status == GenerationStatus.AWAITING_PRODUCTS


def test_generation_expiry_and_touch():
    session = new_generation()
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert session.is_expired() is True

    session.touch(10)
    assert session.is_expired() is False
    assert session.expires_at > datetime.now(timezone.utc) + timedelta(minutes=9)


def test_generation_does_not_share_mutable_input():
    ids = [1, 2]
    session = new_generation()
    session.select_restrictions(ids)
    ids.append(3)

    assert session.restriction_ids == [1, 2]
