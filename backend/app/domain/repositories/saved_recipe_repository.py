from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.recipe import Recipe


class SavedRecipeRepository(ABC):

    @abstractmethod
    async def save(self, user_id: UUID, recipe_id: int) -> bool:
        pass

    @abstractmethod
    async def get_all_by_user_id(
        self,
        user_id: UUID,
    ) -> list[Recipe]:
        pass

    @abstractmethod
    async def get_by_id(
        self,
        user_id: UUID,
        recipe_id: int,
    ) -> Recipe | None:
        pass

    @abstractmethod
    async def delete(
        self,
        user_id: UUID,
        recipe_id: int,
    ) -> bool:
        pass