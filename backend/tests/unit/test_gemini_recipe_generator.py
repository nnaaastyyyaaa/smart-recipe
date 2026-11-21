from types import SimpleNamespace

import pytest
from google.genai import errors

from app.application.dto.recipe_dto import (
    RecipeGenerationSchema,
    RecipeSuggestionSchema,
    RecipeSuggestionsResponse,
)
from app.application.exceptions import (
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderUnavailableError,
)
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product
from app.infrastructure.ai.gemini_recipe_generator import GeminiRecipeGenerator
from app.infrastructure.ai.rate_limiter import (
    AIRateLimitExceededError,
    InMemoryGeminiRateLimiter,
)
from tests.helpers import req

PRODUCTS = [Product(id=1, name="Помідор", category_id=1), Product(id=2, name="Сир", category_id=2)]
VEGAN = DietaryRestriction(id=1, name="Веганське")
SUGGESTION = RecipeSuggestionSchema(
    title="Салат", description="Легкий салат", cooking_time=10, used_product_ids=[1, 2],
)
SUGGESTIONS_JSON = (
    '{"recipes": [{"title": "Салат", "description": "Опис", "cooking_time": 10, "used_product_ids": [1, 2]}]}'
)
FULL_JSON = (
    '{"title": "Салат", "description": "Опис", "ingredients": "Помідор — 200 г", '
    '"instructions": "1. Нарізати", "cooking_time": 10}'
)


class FakeModels:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.response = SimpleNamespace(parsed=None, text=SUGGESTIONS_JSON)
        self.error: Exception | None = None

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        return self.response


@pytest.fixture
def models():
    return FakeModels()


@pytest.fixture
def generator(models):
    instance = GeminiRecipeGenerator(
        api_key="test-key",
        model="test-model",
        rate_limiter=InMemoryGeminiRateLimiter(requests_per_minute=100),
    )
    instance.aio = SimpleNamespace(models=models)
    return instance


def prompt_of(models: FakeModels) -> str:
    return models.calls[-1]["contents"]


def config_of(models: FakeModels):
    return models.calls[-1]["config"]


@req("NFR-5")
def test_system_instruction_requires_ukrainian_only():
    instruction = GeminiRecipeGenerator.SYSTEM_INSTRUCTION

    assert "українською" in instruction


@req("NFR-5")
async def test_suggestions_request_sends_ukrainian_system_instruction_and_json_schema(generator, models):
    await generator.suggest_recipes(PRODUCTS, [])

    config = config_of(models)
    assert config.system_instruction == GeminiRecipeGenerator.SYSTEM_INSTRUCTION
    assert config.response_mime_type == "application/json"
    assert config.response_schema is RecipeSuggestionsResponse
    assert models.calls[-1]["model"] == "test-model"


@req("NFR-5")
async def test_full_recipe_request_sends_ukrainian_system_instruction(generator, models):
    models.response = SimpleNamespace(parsed=None, text=FULL_JSON)

    await generator.generate_full_recipe(SUGGESTION, PRODUCTS, [])

    config = config_of(models)
    assert "українською" in config.system_instruction
    assert config.response_schema is RecipeGenerationSchema


@req("NFR-5")
async def test_both_prompts_demand_ukrainian_output(generator, models):
    await generator.suggest_recipes(PRODUCTS, [])
    suggest_prompt = prompt_of(models)

    models.response = SimpleNamespace(parsed=None, text=FULL_JSON)
    await generator.generate_full_recipe(SUGGESTION, PRODUCTS, [])
    full_prompt = prompt_of(models)

    assert "українською мовою" in suggest_prompt
    assert "українською мовою" in full_prompt


@req("FR-G1")
async def test_suggestions_prompt_lists_products_with_ids(generator, models):
    await generator.suggest_recipes(PRODUCTS, [])

    prompt = prompt_of(models)
    assert "ID: 1, назва: Помідор" in prompt
    assert "ID: 2, назва: Сир" in prompt


@req("FR-G2", "FR-G3")
async def test_suggestions_prompt_asks_for_up_to_16_recipes(generator, models):
    await generator.suggest_recipes(PRODUCTS, [])

    assert "від 1 до 16" in prompt_of(models)
    assert "не більше 16" in prompt_of(models)


@req("FR-G1")
async def test_suggestions_prompt_includes_restrictions(generator, models):
    gluten = DietaryRestriction(id=2, name="Без глютену")

    await generator.suggest_recipes(PRODUCTS, [VEGAN, gluten])

    prompt = prompt_of(models)
    assert "ДІЄТИЧНІ ОБМЕЖЕННЯ" in prompt
    assert "Веганське, Без глютену" in prompt


@req("FR-G1")
async def test_prompts_have_no_restriction_block_when_none_selected(generator, models):
    await generator.suggest_recipes(PRODUCTS, [])
    assert "ДІЄТИЧНІ ОБМЕЖЕННЯ" not in prompt_of(models)

    models.response = SimpleNamespace(parsed=None, text=FULL_JSON)
    await generator.generate_full_recipe(SUGGESTION, PRODUCTS, [])
    assert "ДІЄТИЧНІ ОБМЕЖЕННЯ" not in prompt_of(models)


@req("FR-G1", "FR-G6")
async def test_full_recipe_prompt_contains_chosen_dish_products_and_restrictions(generator, models):
    models.response = SimpleNamespace(parsed=None, text=FULL_JSON)

    await generator.generate_full_recipe(SUGGESTION, PRODUCTS, [VEGAN])

    prompt = prompt_of(models)
    assert "Салат" in prompt and "Легкий салат" in prompt and "10 хвилин" in prompt
    assert "- Помідор" in prompt and "- Сир" in prompt
    assert "Веганське" in prompt
    assert "точні кількості" in prompt


@req("FR-G2")
async def test_suggestions_are_parsed_from_json_text(generator):
    result = await generator.suggest_recipes(PRODUCTS, [])

    assert isinstance(result, RecipeSuggestionsResponse)
    assert result.recipes[0].title == "Салат"


async def test_suggestions_prefer_parsed_object_when_available(generator, models):
    parsed = RecipeSuggestionsResponse(recipes=[SUGGESTION])
    models.response = SimpleNamespace(parsed=parsed, text=None)

    result = await generator.suggest_recipes(PRODUCTS, [])

    assert result.recipes == [SUGGESTION]


@req("FR-G6")
async def test_full_recipe_is_parsed(generator, models):
    models.response = SimpleNamespace(parsed=None, text=FULL_JSON)

    result = await generator.generate_full_recipe(SUGGESTION, PRODUCTS, [])

    assert result.ingredients == "Помідор — 200 г" and result.cooking_time == 10


@req("FR-G4")
async def test_empty_recipe_list_is_a_valid_answer(generator, models):
    models.response = SimpleNamespace(parsed=None, text='{"recipes": []}')

    assert (await generator.suggest_recipes(PRODUCTS, [])).recipes == []


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(parsed=None, text=None),
        SimpleNamespace(parsed=None, text=""),
        SimpleNamespace(parsed=None, text="це не JSON"),
        SimpleNamespace(parsed=None, text='{"recipes": [{"title": "x"}]}'),
        SimpleNamespace(parsed=None, text='{"unexpected": 1}'),
    ],
)
async def test_invalid_ai_payload_raises_invalid_response(generator, models, response):
    models.response = response

    with pytest.raises(AIProviderInvalidResponseError):
        await generator.suggest_recipes(PRODUCTS, [])


async def test_invalid_full_recipe_payload_raises_invalid_response(generator, models):
    models.response = SimpleNamespace(parsed=None, text='{"title": ""}')

    with pytest.raises(AIProviderInvalidResponseError):
        await generator.generate_full_recipe(SUGGESTION, PRODUCTS, [])


@req("NFR-4")
async def test_provider_429_becomes_rate_limit_error(generator, models):
    models.error = errors.ClientError(429, {"error": {"message": "quota"}})

    with pytest.raises(AIProviderRateLimitError):
        await generator.suggest_recipes(PRODUCTS, [])


@pytest.mark.parametrize(
    "error",
    [
        errors.ServerError(503, {"error": {"message": "down"}}),
        errors.ClientError(400, {"error": {"message": "bad"}}),
        errors.ClientError(403, {"error": {"message": "forbidden"}}),
        TimeoutError("timeout"),
        RuntimeError("boom"),
    ],
)
async def test_other_provider_errors_become_unavailable(generator, models, error):
    models.error = error

    with pytest.raises(AIProviderUnavailableError):
        await generator.suggest_recipes(PRODUCTS, [])

    with pytest.raises(AIProviderUnavailableError):
        await generator.generate_full_recipe(SUGGESTION, PRODUCTS, [])


@req("NFR-4")
async def test_rate_limit_is_checked_before_calling_gemini(models):
    limiter = InMemoryGeminiRateLimiter(requests_per_minute=1)
    instance = GeminiRecipeGenerator("k", "m", limiter)
    instance.aio = SimpleNamespace(models=models)

    await instance.suggest_recipes(PRODUCTS, [])

    with pytest.raises(AIRateLimitExceededError):
        await instance.suggest_recipes(PRODUCTS, [])

    assert len(models.calls) == 1


@req("NFR-4")
async def test_every_ai_call_consumes_one_rpm_slot(models):
    limiter = InMemoryGeminiRateLimiter(requests_per_minute=10)
    instance = GeminiRecipeGenerator("k", "m", limiter)
    instance.aio = SimpleNamespace(models=models)

    await instance.suggest_recipes(PRODUCTS, [])
    models.response = SimpleNamespace(parsed=None, text=FULL_JSON)
    await instance.generate_full_recipe(SUGGESTION, PRODUCTS, [])

    assert len(limiter.requests) == 2


async def test_close_closes_async_client(generator):
    closed = []

    async def aclose():
        closed.append(True)

    generator.aio = SimpleNamespace(aclose=aclose)

    await generator.close()

    assert closed == [True]
