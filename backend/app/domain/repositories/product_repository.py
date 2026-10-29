from abc import ABC, abstractmethod
from typing import List
from app.domain.entities.product import Product

class ProductRepository(ABC):
    @abstractmethod
    async def get_by_id(self, product_id: int) -> Product | None:
        pass

    @abstractmethod
    async def get_all(
        self, 
        category_id: int | None = None, 
        limit: int = 12, 
        offset: int = 0
    ) -> List[Product]:
        pass