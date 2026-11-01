from uuid import UUID

from app.application.dto.recipe_dto import RecipeGenerationSchema
from app.domain.entities.recipe import Recipe
from app.domain.repositories.recipe_repository import RecipeRepository
from app.domain.repositories.saved_recipe_repository import SavedRecipeRepository


class RecipeService:
    """Збережені рецепти користувача ("Кулінарна книга")."""

    def __init__(
        self,
        recipes: RecipeRepository,
        saved_recipes: SavedRecipeRepository,
    ) -> None:
        self.recipes = recipes
        self.saved_recipes = saved_recipes

    async def save_recipe(
        self,
        user_id: UUID,
        data: RecipeGenerationSchema,
    ) -> Recipe:

        recipe = Recipe(
            title=data.title,
            description=data.description,
            ingredients=data.ingredients,
            instructions=data.instructions,
            cooking_time=data.cooking_time,
        )

        saved_recipe = await self.recipes.save(recipe)

        if saved_recipe.id is None:
            raise RuntimeError("Не вдалося отримати ID рецепта.")

        link_created = await self.saved_recipes.save(
            user_id=user_id,
            recipe_id=saved_recipe.id,
        )

        if not link_created:
            raise RuntimeError("Не вдалося створити зв'язок із рецептом.")

        return saved_recipe

    async def get_saved_recipes(self, user_id: UUID) -> list[Recipe]:
        return await self.saved_recipes.get_all_by_user_id(user_id)

    async def get_saved_recipe(
        self,
        user_id: UUID,
        recipe_id: int,
    ) -> Recipe | None:
        return await self.saved_recipes.get_by_id(
            user_id=user_id,
            recipe_id=recipe_id,
        )

    async def delete_saved_recipe(
        self,
        user_id: UUID,
        recipe_id: int,
    ) -> bool:
        return await self.saved_recipes.delete(
            user_id=user_id,
            recipe_id=recipe_id,
        )
