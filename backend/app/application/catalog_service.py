from app.application.exceptions import CategoryNotFoundError
from app.domain.entities.category import Category
from app.domain.entities.product import Product
from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.product_repository import ProductRepository


class CatalogService:

    def __init__(
        self,
        categories: CategoryRepository,
        products: ProductRepository,
    ) -> None:
        self.categories = categories
        self.products = products

    async def get_categories(self) -> list[Category]:
        return await self.categories.get_all()

    async def get_products(
        self,
        category_id: int | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[Product]:

        if category_id is not None:
            category = await self.categories.get_by_id(category_id)

            if category is None:
                raise CategoryNotFoundError()

        return await self.products.get_all(
            category_id=category_id,
            limit=limit,
            offset=offset,
            search=search,
        )

    async def get_product(self, product_id: int) -> Product | None:
        return await self.products.get_by_id(product_id)