import pytest
from pydantic import ValidationError

from app.application.dto.generation_dto import (
    GenerationRecipeRequest,
    GenerationRestrictionsRequest,
    GenerationSuggestionsRequest,
    SuggestionItemSchema,
)
from app.application.dto.recipe_dto import (
    RecipeGenerationSchema,
    RecipeSuggestionSchema,
    RecipeSuggestionsResponse,
)
from app.presentation.schemas.auth import UserLoginSchema, UserRegisterSchema
from app.presentation.schemas.user import ChangePasswordSchema, UserUpdateSchema
from tests.helpers import req


def register(**overrides):
    data = {"name": "Anna", "email": "anna@example.com", "password": "Passw0rd!"}
    data.update(overrides)
    return UserRegisterSchema(**data)


@req("FR-A4")
@pytest.mark.parametrize("length", [8, 12, 16])
def test_password_length_inside_range_is_valid(length):
    assert register(password="a" * length).password == "a" * length


@req("FR-A4")
@pytest.mark.parametrize("length", [0, 1, 7, 17, 100])
def test_password_length_outside_range_is_invalid(length):
    with pytest.raises(ValidationError):
        register(password="a" * length)


@req("FR-A5")
@pytest.mark.parametrize(
    "password",
    ["Пароль123!", "Passw0rd!є", "Pass word1", "Passw0rd\u00e9", "密码密码密码密码", "Pass\tw0rd1"],
)
def test_password_with_non_english_or_whitespace_is_invalid(password):
    with pytest.raises(ValidationError):
        register(password=password)


@req("FR-A5")
def test_password_allows_all_documented_special_characters():
    assert register(password="Aa1!@#$%^&*()").password


@req("FR-A6")
@pytest.mark.parametrize("name", ["Al", "A" * 24])
def test_name_boundaries_valid(name):
    assert register(name=name).name == name


@req("FR-A6")
@pytest.mark.parametrize("name", ["", "A", "A" * 25])
def test_name_boundaries_invalid(name):
    with pytest.raises(ValidationError):
        register(name=name)


@req("FR-A2")
@pytest.mark.parametrize("missing", ["name", "email", "password"])
def test_all_registration_fields_are_required(missing):
    data = {"name": "Anna", "email": "anna@example.com", "password": "Passw0rd!"}
    data.pop(missing)

    with pytest.raises(ValidationError):
        UserRegisterSchema(**data)


@req("FR-A2")
@pytest.mark.parametrize("email", ["", "not-an-email", "a@", "@b.com", "a b@c.com"])
def test_invalid_email_is_rejected(email):
    with pytest.raises(ValidationError):
        register(email=email)


@req("FR-A7", "FR-A8")
def test_login_schema_requires_email_and_password():
    assert UserLoginSchema(email="a@b.com", password="x")

    with pytest.raises(ValidationError):
        UserLoginSchema(email="a@b.com", password="")

    with pytest.raises(ValidationError):
        UserLoginSchema(email="bad", password="x")


@req("FR-A11")
def test_profile_update_requires_at_least_one_field():
    with pytest.raises(ValidationError):
        UserUpdateSchema()

    assert UserUpdateSchema(name="Anna")
    assert UserUpdateSchema(email="a@b.com")


def test_profile_update_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        UserUpdateSchema(name="Anna", role="admin")


@req("FR-A6")
@pytest.mark.parametrize("name", ["A", "A" * 25])
def test_profile_update_name_bounds(name):
    with pytest.raises(ValidationError):
        UserUpdateSchema(name=name)


@req("FR-A4", "FR-A5", "FR-A11")
@pytest.mark.parametrize("password", ["short1!", "a" * 17, "Пароль123!", "with space1"])
def test_new_password_rules_apply_on_change(password):
    with pytest.raises(ValidationError):
        ChangePasswordSchema(current_password="old", new_password=password)


@req("FR-A11")
def test_change_password_accepts_valid_and_forbids_extra():
    assert ChangePasswordSchema(current_password="old", new_password="NewPassw0rd!")

    with pytest.raises(ValidationError):
        ChangePasswordSchema(current_password="old", new_password="NewPassw0rd!", x=1)


@req("FR-B1")
def test_restrictions_request_requires_explicit_list():
    with pytest.raises(ValidationError):
        GenerationRestrictionsRequest()

    assert GenerationRestrictionsRequest(restriction_ids=[]).restriction_ids == []


@req("FR-B1")
@pytest.mark.parametrize("ids", [[0], [-1], [1, 1], list(range(1, 22))])
def test_restrictions_request_rejects_bad_ids(ids):
    with pytest.raises(ValidationError):
        GenerationRestrictionsRequest(restriction_ids=ids)


@req("FR-B4")
@pytest.mark.parametrize("ids", [[], [1]])
def test_at_least_two_products_required(ids):
    with pytest.raises(ValidationError):
        GenerationSuggestionsRequest(product_ids=ids)


@req("FR-B4")
def test_two_products_is_enough():
    assert GenerationSuggestionsRequest(product_ids=[1, 2]).product_ids == [1, 2]


@pytest.mark.parametrize("ids", [[1, 1], [0, 2], [-1, 2], list(range(1, 32))])
def test_product_ids_must_be_unique_positive_and_at_most_30(ids):
    with pytest.raises(ValidationError):
        GenerationSuggestionsRequest(product_ids=ids)


def test_suggestions_request_forbids_extra_fields():
    with pytest.raises(ValidationError):
        GenerationSuggestionsRequest(product_ids=[1, 2], restriction_ids=[1])


@req("FR-G5")
def test_recipe_request_suggestion_id_must_be_non_negative_int():
    assert GenerationRecipeRequest(suggestion_id=0).suggestion_id == 0

    with pytest.raises(ValidationError):
        GenerationRecipeRequest(suggestion_id=-1)

    with pytest.raises(ValidationError):
        GenerationRecipeRequest()


def suggestion(**overrides):
    data = dict(title="Салат", description="Легкий салат", cooking_time=10, used_product_ids=[1, 2])
    data.update(overrides)
    return RecipeSuggestionSchema(**data)


@req("FR-G2")
def test_ai_suggestion_valid_and_strips_text():
    item = suggestion(title="  Салат ", description=" опис ")

    assert (item.title, item.description) == ("Салат", "опис")


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "я" * 81},
        {"description": ""},
        {"description": "я" * 201},
        {"cooking_time": 0},
        {"used_product_ids": [1]},
        {"used_product_ids": [1, 1]},
        {"used_product_ids": [0, 2]},
    ],
)
def test_ai_suggestion_invalid_values_are_rejected(overrides):
    with pytest.raises(ValidationError):
        suggestion(**overrides)


@req("FR-G2", "FR-G3")
def test_ai_response_allows_up_to_16_recipes_but_not_more():
    items = [suggestion(title=f"Страва {i}") for i in range(16)]
    assert len(RecipeSuggestionsResponse(recipes=items).recipes) == 16

    with pytest.raises(ValidationError):
        RecipeSuggestionsResponse(recipes=items + [suggestion(title="Зайва")])


def test_ai_response_may_be_empty():
    assert RecipeSuggestionsResponse(recipes=[]).recipes == []


@req("FR-G6")
@pytest.mark.parametrize("field", ["title", "description", "ingredients", "instructions"])
def test_full_recipe_requires_non_blank_text_fields(field):
    data = dict(title="T", description="D", ingredients="I", instructions="S", cooking_time=5)
    data[field] = "   "

    with pytest.raises(ValidationError):
        RecipeGenerationSchema(**data)


@req("FR-G6")
def test_full_recipe_requires_positive_time():
    with pytest.raises(ValidationError):
        RecipeGenerationSchema(title="T", description="D", ingredients="I", instructions="S", cooking_time=0)


def test_suggestion_item_extends_suggestion_with_id():
    item = SuggestionItemSchema(id=3, title="T", description="D", cooking_time=5, used_product_ids=[1, 2])

    assert item.id == 3
    assert set(item.model_dump()) == {"id", "title", "description", "cooking_time", "used_product_ids"}


@pytest.mark.parametrize("value", [2_147_483_648, 99_999_999_999])
def test_ids_above_int32_are_rejected(value):
    with pytest.raises(ValidationError):
        GenerationSuggestionsRequest(product_ids=[1, value])

    with pytest.raises(ValidationError):
        GenerationRestrictionsRequest(restriction_ids=[value])


def test_max_int32_id_is_still_valid():
    assert GenerationSuggestionsRequest(product_ids=[1, 2_147_483_647]).product_ids[-1] == 2_147_483_647
    assert GenerationRestrictionsRequest(restriction_ids=[2_147_483_647]).restriction_ids == [2_147_483_647]
