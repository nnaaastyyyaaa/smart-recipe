from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from app.application.dto.recipe_dto import (
    RecipeGenerationSchema,
    RecipeResponseSchema,
)
from app.application.recipe_service import RecipeService
from app.core.config import MAX_DB_ID
from app.domain.entities.user import User
from app.presentation.api.dependencies import (
    get_current_user,
    get_recipe_service,
)


router = APIRouter(prefix="/recipes", tags=["recipes"])


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
    response: Response,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=MAX_DB_ID),
    service: RecipeService = Depends(get_recipe_service),
    current_user: User = Depends(get_current_user),
):
    recipes = await service.get_saved_recipes(
        current_user.id,
        limit=limit,
        offset=offset,
    )

    response.headers["X-Total-Count"] = str(
        await service.count_saved_recipes(current_user.id)
    )

    return recipes


@router.get(
    "/saved/{recipe_id}",
    response_model=RecipeResponseSchema,
)
async def get_saved_recipe(
    recipe_id: int = Path(gt=0, le=MAX_DB_ID),
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
    recipe_id: int = Path(gt=0, le=MAX_DB_ID),
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
