from fastapi import APIRouter, Depends, HTTPException, status

from app.application.dto.recipe_dto import (
    RecipeSuggestionsRequest,
    RecipeSuggestionsResponse,
    GenerateFullRecipeRequest,
    RecipeGenerationSchema,
    RecipeResponseSchema,
)
from app.application.recipe_service import RecipeService
from app.application.exceptions import (
    DietaryRestrictionsNotFoundError,
    ProductsNotFoundError,
    ProductsViolateRestrictionsError,
    NoSuitableRecipesError,
    AIProviderRateLimitError,
    AIProviderUnavailableError,
    AIProviderInvalidResponseError,
)
from app.domain.entities.user import User
from app.infrastructure.ai.rate_limiter import AIRateLimitExceededError
from app.presentation.api.dependencies import (
    get_current_user,
    get_recipe_service,
)


router = APIRouter(prefix="/recipes", tags=["recipes"])


def handle_ai_error(exc: Exception) -> None:
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


@router.post(
    "/suggestions",
    response_model=RecipeSuggestionsResponse,
)
async def suggest_recipes(
    data: RecipeSuggestionsRequest,
    service: RecipeService = Depends(get_recipe_service),
    current_user: User = Depends(get_current_user),
) -> RecipeSuggestionsResponse:
    try:
        return await service.suggest_recipes(
            current_user.id,
            data.product_ids,
            data.restriction_ids,
        )

    except ProductsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Один або декілька обраних продуктів не знайдені.",
        )

    except DietaryRestrictionsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Одне або декілька дієтичних обмежень не знайдені.",
        )

    except ProductsViolateRestrictionsError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Серед обраних продуктів є такі, що не підходять під обрані дієтичні обмеження.",
        )

    except NoSuitableRecipesError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Не вдалося знайти відповідні рецепти.",
        )

    except (
        AIRateLimitExceededError,
        AIProviderRateLimitError,
        AIProviderUnavailableError,
        AIProviderInvalidResponseError,
    ) as exc:
        handle_ai_error(exc)


@router.post(
    "/generate",
    response_model=RecipeGenerationSchema,
)
async def generate_full_recipe(
    data: GenerateFullRecipeRequest,
    service: RecipeService = Depends(get_recipe_service),
    current_user: User = Depends(get_current_user),
) -> RecipeGenerationSchema:
    try:
        return await service.generate_full_recipe(
            current_user.id,
            data.suggestion,
            data.restriction_ids,
        )

    except ProductsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Один або декілька продуктів не знайдені.",
        )

    except DietaryRestrictionsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Одне або декілька дієтичних обмежень не знайдені.",
        )

    except ProductsViolateRestrictionsError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Серед обраних продуктів є такі, що не підходять під обрані дієтичні обмеження.",
        )

    except (
        AIRateLimitExceededError,
        AIProviderRateLimitError,
        AIProviderUnavailableError,
        AIProviderInvalidResponseError,
    ) as exc:
        handle_ai_error(exc)


@router.post(
    "/saved",
    response_model=RecipeResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def save_recipe(
    data: RecipeGenerationSchema,
    service: RecipeService = Depends(get_recipe_service),
    current_user: User = Depends(get_current_user),
) -> RecipeResponseSchema:
    return await service.save_recipe(
        user_id=current_user.id,
        data=data,
    )


@router.get(
    "/saved",
    response_model=list[RecipeResponseSchema],
)
async def get_saved_recipes(
    service: RecipeService = Depends(get_recipe_service),
    current_user: User = Depends(get_current_user),
):
    return await service.get_saved_recipes(current_user.id)


@router.get(
    "/saved/{recipe_id}",
    response_model=RecipeResponseSchema,
)
async def get_saved_recipe(
    recipe_id: int,
    service: RecipeService = Depends(get_recipe_service),
    current_user: User = Depends(get_current_user),
):
    recipe = await service.get_saved_recipe(
        user_id=current_user.id,
        recipe_id=recipe_id,
    )

    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Збережений рецепт не знайдений.",
        )

    return recipe


@router.delete(
    "/saved/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_saved_recipe(
    recipe_id: int,
    service: RecipeService = Depends(get_recipe_service),
    current_user: User = Depends(get_current_user),
) -> None:
    deleted = await service.delete_saved_recipe(
        user_id=current_user.id,
        recipe_id=recipe_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Збережений рецепт не знайдений.",
        )