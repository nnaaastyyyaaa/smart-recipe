from abc import ABC, abstractmethod
from typing import List
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product

class ProductRepository(ABC):
    @abstractmethod
    async def get_by_id(self, product_id: int) -> Product | None:
        pass

    @abstractmethod
    async def get_by_ids(
        self,
        product_ids: list[int],
        exclude_restriction_ids: list[int] | None = None,
    ) -> list[Product]:
        pass

    @abstractmethod
    async def get_all(
        self, 
        category_id: int | None = None, 
        limit: int = 12, 
        offset: int = 0,
        search: str | None = None,
        exclude_restriction_ids: list[int] | None = None,
    ) -> List[Product]:
        pass

    @abstractmethod
    async def get_restrictions(
        self,
        product_id: int,
    ) -> list[DietaryRestriction]:
        pass
