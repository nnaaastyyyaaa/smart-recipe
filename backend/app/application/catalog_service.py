from app.application.exceptions import (
    CategoryNotFoundError,
    DietaryRestrictionsNotFoundError,
    ProductNotFoundError,
)
from app.domain.entities.category import Category
from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product
from app.domain.repositories.category_repository import CategoryRepository
from app.domain.repositories.dietary_restriction_repository import (
    DietaryRestrictionRepository,
)
from app.domain.repositories.product_repository import ProductRepository


class CatalogService:

    def __init__(
        self,
        categories: CategoryRepository,
        products: ProductRepository,
        restrictions: DietaryRestrictionRepository,
    ) -> None:
        self.categories = categories
        self.products = products
        self.restrictions = restrictions

    async def get_categories(self) -> list[Category]:
        return await self.categories.get_all()

    async def get_category(self, category_id: int) -> Category | None:
        return await self.categories.get_by_id(category_id)

    async def get_dietary_restrictions(self) -> list[DietaryRestriction]:
        return await self.restrictions.get_all()

    async def get_products(
        self,
        category_id: int | None,
        search: str | None,
        limit: int,
        offset: int,
        restriction_ids: list[int] | None = None,
    ) -> list[Product]:

        if category_id is not None:
            category = await self.categories.get_by_id(category_id)

            if category is None:
                raise CategoryNotFoundError()

        if restriction_ids:
            restrictions = await self.restrictions.get_by_ids(restriction_ids)

            if len(restrictions) != len(set(restriction_ids)):
                raise DietaryRestrictionsNotFoundError()

        return await self.products.get_all(
            category_id=category_id,
            limit=limit,
            offset=offset,
            search=search,
            exclude_restriction_ids=restriction_ids,
        )

    async def get_product(self, product_id: int) -> Product | None:
        return await self.products.get_by_id(product_id)

    async def get_dietary_restriction(
        self,
        restriction_id: int,
    ) -> DietaryRestriction | None:
        return await self.restrictions.get_by_id(restriction_id)

    async def get_product_restrictions(
        self,
        product_id: int,
    ) -> list[DietaryRestriction]:

        product = await self.products.get_by_id(product_id)

        if product is None:
            raise ProductNotFoundError()

        return await self.products.get_restrictions(product_id)