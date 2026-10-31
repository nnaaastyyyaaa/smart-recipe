from abc import ABC, abstractmethod

from app.application.dto.recipe_dto import (
    RecipeSuggestionSchema,
    RecipeSuggestionsResponse,
    RecipeGenerationSchema,
)
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product


class RecipeGenerator(ABC):

    @abstractmethod
    async def suggest_recipes(
        self,
        products: list[Product],
        restrictions: list[DietaryRestriction],
    ) -> RecipeSuggestionsResponse:
        pass

    @abstractmethod
    async def generate_full_recipe(
        self,
        suggestion: RecipeSuggestionSchema,
        products: list[Product],
        restrictions: list[DietaryRestriction],
    ) -> RecipeGenerationSchema:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass