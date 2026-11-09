from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.dto.catalog_dto import CategoryResponseSchema, ProductResponseSchema
from app.application.dto.generation_dto import (
    GenerationRecipeRequest,
    GenerationRestrictionsRequest,
    GenerationStateSchema,
    GenerationSuggestionsRequest,
    SuggestionsPageSchema,
)
from app.application.dto.recipe_dto import RecipeGenerationSchema
from app.application.exceptions import (
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderUnavailableError,
    CategoryNotFoundError,
    DietaryRestrictionsNotFoundError,
    GenerationNotFoundError,
    GenerationRestrictionsNotSelectedError,
    GenerationStateChangedError,
    GenerationSuggestionsNotReadyError,
    NoSuitableRecipesError,
    ProductsNotFoundError,
    ProductsViolateRestrictionsError,
    SuggestionNotFoundError,
    SuggestionsPageNotFoundError,
)
from app.application.generation_service import GenerationService
from app.core.config import MAX_DB_ID
from app.domain.entities.user import User
from app.infrastructure.ai.rate_limiter import AIRateLimitExceededError
from app.presentation.api.dependencies import (
    get_current_user,
    get_generation_service,
)


router = APIRouter(prefix="/generations", tags=["generations"])


# exception -> (HTTP-статус, код помилки для фронтенду, повідомлення)
_FLOW_ERRORS: dict[type[Exception], tuple[int, str, str]] = {
    GenerationNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "GENERATION_NOT_FOUND",
        "Генерацію не знайдено або її термін дії минув. Почніть нову генерацію.",
    ),
    GenerationRestrictionsNotSelectedError: (
        status.HTTP_409_CONFLICT,
        "RESTRICTIONS_NOT_SELECTED",
        "Спочатку оберіть дієтичні обмеження (або вкажіть, що їх немає).",
    ),
    GenerationSuggestionsNotReadyError: (
        status.HTTP_409_CONFLICT,
        "SUGGESTIONS_NOT_READY",
        "Варіанти рецептів ще не згенеровані. Спочатку оберіть продукти.",
    ),
    GenerationStateChangedError: (
        status.HTTP_409_CONFLICT,
        "GENERATION_STATE_CHANGED",
        "Під час генерації дані були змінені. Повторіть запит.",
    ),
    DietaryRestrictionsNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "RESTRICTIONS_NOT_FOUND",
        "Одне або декілька дієтичних обмежень не знайдені.",
    ),
    CategoryNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "CATEGORY_NOT_FOUND",
        "Категорія не знайдена.",
    ),
    ProductsNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "PRODUCTS_NOT_FOUND",
        "Один або декілька обраних продуктів не знайдені.",
    ),
    ProductsViolateRestrictionsError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "PRODUCTS_VIOLATE_RESTRICTIONS",
        "Серед обраних продуктів є такі, що не підходять під обрані дієтичні обмеження.",
    ),
    NoSuitableRecipesError: (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "NO_SUITABLE_RECIPES",
        "За обраними інгредієнтами та дієтичними обмеженнями рецептів не знайдено.",
    ),
    SuggestionNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "SUGGESTION_NOT_FOUND",
        "Обраний варіант рецепта не знайдено.",
    ),
    SuggestionsPageNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "SUGGESTIONS_PAGE_NOT_FOUND",
        "Такої сторінки з варіантами рецептів не існує.",
    ),
}

HANDLED_ERRORS = (
    *_FLOW_ERRORS,
    AIRateLimitExceededError,
    AIProviderRateLimitError,
    AIProviderUnavailableError,
    AIProviderInvalidResponseError,
)


def handle_ai_error(exc: Exception) -> NoReturn:
    if isinstance(exc, AIRateLimitExceededError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "AI_REQUEST_LIMIT_REACHED",
                "message": (
                    "Досягнуто ліміту запитів. "
                    "Спробуйте ще раз трохи пізніше."
                ),
            },
            headers={"Retry-After": str(exc.retry_after)},
        )

    if isinstance(exc, AIProviderRateLimitError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AI_PROVIDER_LIMIT_REACHED",
                "message": (
                    "Сервіс генерації рецептів тимчасово досяг ліміту. "
                    "Будь ласка, спробуйте пізніше."
                ),
            },
        )

    if isinstance(exc, AIProviderInvalidResponseError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "AI_INVALID_RESPONSE",
                "message": (
                    "Не вдалося отримати коректну відповідь "
                    "від сервісу генерації рецептів."
                ),
            },
        )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "AI_SERVICE_UNAVAILABLE",
            "message": (
                "Сервіс генерації рецептів тимчасово недоступний. "
                "Спробуйте пізніше."
            ),
        },
    )


def handle_generation_error(exc: Exception) -> NoReturn:
    mapped = _FLOW_ERRORS.get(type(exc))

    if mapped is not None:
        status_code, code, message = mapped

        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": message},
        ) from exc

    handle_ai_error(exc)


# ---------------------------------------------------------------------
# Крок 0. "Почати генерацію"
# ---------------------------------------------------------------------

@router.post(
    "",
    response_model=GenerationStateSchema,
    status_code=status.HTTP_201_CREATED,
)
async def start_generation(
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
) -> GenerationStateSchema:
    return await service.start(current_user.id)


@router.get(
    "/{generation_id}",
    response_model=GenerationStateSchema,
)
async def get_generation(
    generation_id: UUID,
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
) -> GenerationStateSchema:
    try:
        return await service.get_state(current_user.id, generation_id)

    except HANDLED_ERRORS as exc:
        handle_generation_error(exc)


# ---------------------------------------------------------------------
# Крок 1. Дієтичні обмеження (порожній список = "обмежень немає")
# ---------------------------------------------------------------------

@router.put(
    "/{generation_id}/restrictions",
    response_model=GenerationStateSchema,
)
async def set_generation_restrictions(
    generation_id: UUID,
    data: GenerationRestrictionsRequest,
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
) -> GenerationStateSchema:
    try:
        return await service.set_restrictions(
            current_user.id,
            generation_id,
            data.restriction_ids,
        )

    except HANDLED_ERRORS as exc:
        handle_generation_error(exc)


# ---------------------------------------------------------------------
# Крок 2. Продукти, що підходять під обрані обмеження
# ---------------------------------------------------------------------

@router.get(
    "/{generation_id}/categories",
    response_model=list[CategoryResponseSchema],
)
async def get_generation_categories(
    generation_id: UUID,
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.get_available_categories(
            current_user.id,
            generation_id,
        )

    except HANDLED_ERRORS as exc:
        handle_generation_error(exc)


@router.get(
    "/{generation_id}/products",
    response_model=list[ProductResponseSchema],
)
async def get_generation_products(
    generation_id: UUID,
    category_id: int | None = Query(default=None, gt=0, le=MAX_DB_ID),
    search: str | None = Query(default=None, min_length=1, max_length=60),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=MAX_DB_ID),
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.get_available_products(
            current_user.id,
            generation_id,
            category_id=category_id,
            search=search,
            limit=limit,
            offset=offset,
        )

    except HANDLED_ERRORS as exc:
        handle_generation_error(exc)


# ---------------------------------------------------------------------
# Крок 3. Варіанти рецептів (до 16, по 8 на сторінці)
# ---------------------------------------------------------------------

@router.post(
    "/{generation_id}/suggestions",
    response_model=SuggestionsPageSchema,
)
async def suggest_recipes(
    generation_id: UUID,
    data: GenerationSuggestionsRequest,
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
) -> SuggestionsPageSchema:
    try:
        return await service.suggest_recipes(
            current_user.id,
            generation_id,
            data.product_ids,
        )

    except HANDLED_ERRORS as exc:
        handle_generation_error(exc)


@router.get(
    "/{generation_id}/suggestions",
    response_model=SuggestionsPageSchema,
)
async def get_suggestions_page(
    generation_id: UUID,
    page: int = Query(default=1, ge=1),
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
) -> SuggestionsPageSchema:
    try:
        return await service.get_suggestions_page(
            current_user.id,
            generation_id,
            page,
        )

    except HANDLED_ERRORS as exc:
        handle_generation_error(exc)


# ---------------------------------------------------------------------
# Крок 4. Детальний рецепт для обраного варіанта
# ---------------------------------------------------------------------

@router.post(
    "/{generation_id}/recipe",
    response_model=RecipeGenerationSchema,
)
async def generate_full_recipe(
    generation_id: UUID,
    data: GenerationRecipeRequest,
    service: GenerationService = Depends(get_generation_service),
    current_user: User = Depends(get_current_user),
) -> RecipeGenerationSchema:
    try:
        return await service.generate_full_recipe(
            current_user.id,
            generation_id,
            data.suggestion_id,
        )

    except HANDLED_ERRORS as exc:
        handle_generation_error(exc)
