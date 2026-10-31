from uuid import UUID

from app.application.dto.recipe_dto import (
    RecipeSuggestionsResponse,
    RecipeSuggestionSchema,
    RecipeGenerationSchema,
)
from app.application.exceptions import (
    DietaryRestrictionsNotFoundError,
    ProductsNotFoundError,
    ProductsViolateRestrictionsError,
    NoSuitableRecipesError,
)
from app.application.interfaces.recipe_generator import RecipeGenerator

from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product
from app.domain.entities.recipe import Recipe
from app.domain.repositories.dietary_restriction_repository import (
    DietaryRestrictionRepository,
)
from app.domain.repositories.user_dietary_restriction_repository import (
    UserDietaryRestrictionRepository,
)
from app.domain.repositories.product_repository import ProductRepository
from app.domain.repositories.recipe_repository import RecipeRepository
from app.domain.repositories.saved_recipe_repository import SavedRecipeRepository


class RecipeService:

    def __init__(
        self,
        products: ProductRepository,
        recipes: RecipeRepository,
        saved_recipes: SavedRecipeRepository,
        restrictions: DietaryRestrictionRepository,
        user_restrictions: UserDietaryRestrictionRepository,
        recipe_generator: RecipeGenerator,
    ) -> None:
        self.products = products
        self.recipes = recipes
        self.saved_recipes = saved_recipes
        self.restrictions = restrictions
        self.user_restrictions = user_restrictions
        self.recipe_generator = recipe_generator

    async def _resolve_restriction_ids(
        self,
        user_id: UUID,
        restriction_ids: list[int] | None,
    ) -> list[int]:
        if restriction_ids is not None:
            return restriction_ids

        profile_restrictions = await self.user_restrictions.get_by_user_id(
            user_id
        )

        return [restriction.id for restriction in profile_restrictions]

    async def _get_restrictions(
        self,
        restriction_ids: list[int],
    ) -> list[DietaryRestriction]:

        if not restriction_ids:
            return []

        restrictions = await self.restrictions.get_by_ids(restriction_ids)

        if len(restrictions) != len(restriction_ids):
            raise DietaryRestrictionsNotFoundError()

        return restrictions

    async def _ensure_products_allowed(
        self,
        products: list[Product],
        restriction_ids: list[int],
    ) -> None:

        if not restriction_ids:
            return

        product_ids = [product.id for product in products]

        allowed = await self.products.get_by_ids(
            product_ids,
            exclude_restriction_ids=restriction_ids,
        )

        if len(allowed) != len(products):
            raise ProductsViolateRestrictionsError()

    async def suggest_recipes(
        self,
        user_id: UUID,
        product_ids: list[int],
        restriction_ids: list[int] | None = None,
    ) -> RecipeSuggestionsResponse:

        restriction_ids = await self._resolve_restriction_ids(
            user_id,
            restriction_ids,
        )

        products = await self.products.get_by_ids(product_ids)

        if len(products) != len(product_ids):
            raise ProductsNotFoundError()

        restrictions = await self._get_restrictions(restriction_ids)

        await self._ensure_products_allowed(products, restriction_ids)

        response = await self.recipe_generator.suggest_recipes(
            products,
            restrictions,
        )

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
        user_id: UUID,
        suggestion: RecipeSuggestionSchema,
        restriction_ids: list[int] | None = None,
    ) -> RecipeGenerationSchema:

        restriction_ids = await self._resolve_restriction_ids(
            user_id,
            restriction_ids,
        )

        products = await self.products.get_by_ids(
            suggestion.used_product_ids
        )

        if len(products) != len(suggestion.used_product_ids):
            raise ProductsNotFoundError()

        restrictions = await self._get_restrictions(restriction_ids)

        await self._ensure_products_allowed(products, restriction_ids)

        return await self.recipe_generator.generate_full_recipe(
            suggestion=suggestion,
            products=products,
            restrictions=restrictions,
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