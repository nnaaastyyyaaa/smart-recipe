from abc import ABC, abstractmethod

from app.domain.entities.category import Category


class CategoryRepository(ABC):

    @abstractmethod
    async def get_by_id(self, category_id: int) -> Category | None:
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Category | None:
        pass

    @abstractmethod
    async def get_all(self) -> list[Category]:
        pass