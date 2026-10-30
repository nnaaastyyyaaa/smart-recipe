from abc import ABC, abstractmethod

from app.domain.entities.recipe import Recipe


class RecipeRepository(ABC):

    @abstractmethod
    async def get_by_id(self, recipe_id: int) -> Recipe | None:
        pass

    @abstractmethod
    async def save(self, recipe: Recipe) -> Recipe:
        pass