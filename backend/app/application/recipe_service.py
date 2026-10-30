from uuid import UUID

from app.application.dto.recipe_dto import (
    RecipeSuggestionsResponse,
    RecipeSuggestionSchema,
    RecipeGenerationSchema,
)
from app.application.exceptions import (
    ProductsNotFoundError,
    NoSuitableRecipesError,
)
from app.application.interfaces.recipe_generator import RecipeGenerator

from app.domain.entities.recipe import Recipe
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.recipe_repository import RecipeRepository
from app.domain.repositories.saved_recipe_repository import SavedRecipeRepository


class RecipeService:

    def __init__(
        self,
        products: ProductRepository,
        recipes: RecipeRepository,
        saved_recipes: SavedRecipeRepository,
        recipe_generator: RecipeGenerator,
    ) -> None:
        self.products = products
        self.recipes = recipes
        self.saved_recipes = saved_recipes
        self.recipe_generator = recipe_generator

    async def suggest_recipes(
        self,
        product_ids: list[int],
    ) -> RecipeSuggestionsResponse:

        products = await self.products.get_by_ids(product_ids)

        if len(products) != len(product_ids):
            raise ProductsNotFoundError()

        response = await self.recipe_generator.suggest_recipes(products)

        selected_ids = set(product_ids)

        valid_recipes = []
        seen_titles = set()

        for recipe in response.recipes:
            used_ids = set(recipe.used_product_ids)

            if len(used_ids) < 2:
                continue

            if not used_ids.issubset(selected_ids):
                continue

            normalized_title = recipe.title.casefold()

            if normalized_title in seen_titles:
                continue

            seen_titles.add(normalized_title)
            valid_recipes.append(recipe)


        valid_recipes.sort(
            key=lambda recipe: len(recipe.used_product_ids),
            reverse=True,
        )

        if not valid_recipes:
            raise NoSuitableRecipesError()

        return RecipeSuggestionsResponse(
            recipes=valid_recipes[:8],
        )

    async def generate_full_recipe(
        self,
        suggestion: RecipeSuggestionSchema,
    ) -> RecipeGenerationSchema:

        products = await self.products.get_by_ids(
            suggestion.used_product_ids
        )

        if len(products) != len(suggestion.used_product_ids):
            raise ProductsNotFoundError()

        return await self.recipe_generator.generate_full_recipe(
            suggestion=suggestion,
            products=products,
        )

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