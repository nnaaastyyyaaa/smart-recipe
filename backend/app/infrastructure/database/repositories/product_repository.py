from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.entities.product import Product
from app.domain.repositories.product_repository import ProductRepository
from app.infrastructure.database.models.associations import (
    product_restrictions,
)
from app.infrastructure.database.models.dietary_restriction_model import (
    DietaryRestrictionModel,
)
from app.infrastructure.database.models.product_model import ProductModel


class SQLAlchemyProductRepository(ProductRepository):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, product_id: int) -> Product | None:
        model = await self.db.get(ProductModel, product_id)

        if model is None:
            return None

        return self._to_entity(model)

    async def get_by_ids(
        self,
        product_ids: list[int],
        exclude_restriction_ids: list[int] | None = None,
    ) -> list[Product]:
        statement = select(ProductModel).where(
            ProductModel.id.in_(product_ids)
        )

        if exclude_restriction_ids:
            statement = statement.where(
                self._allowed_condition(exclude_restriction_ids)
            )

        result = await self.db.execute(statement)
        models = result.scalars().all()

        return [
            self._to_entity(model)
            for model in models
        ]

    async def get_all(
        self,
        category_id: int | None = None,
        limit: int = 12,
        offset: int = 0,
        search: str | None = None,
        exclude_restriction_ids: list[int] | None = None,
    ) -> list[Product]:
        statement = select(ProductModel)

        if category_id is not None:
            statement = statement.where(ProductModel.category_id == category_id)

        if search:
            statement = statement.where(self._search_condition(search))

        if exclude_restriction_ids:
            statement = statement.where(
                self._allowed_condition(exclude_restriction_ids)
            )

        statement = (
            statement
            .order_by(ProductModel.name)
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(statement)
        models = result.scalars().all()

        return [
            self._to_entity(model)
            for model in models
        ]

    async def get_restrictions(
        self,
        product_id: int,
    ) -> list[DietaryRestriction]:
        statement = (
            select(DietaryRestrictionModel)
            .join(
                product_restrictions,
                product_restrictions.c.restriction_id
                == DietaryRestrictionModel.id,
            )
            .where(product_restrictions.c.product_id == product_id)
            .order_by(DietaryRestrictionModel.name)
        )

        result = await self.db.execute(statement)
        models = result.scalars().all()

        return [
            DietaryRestriction(id=model.id, name=model.name)
            for model in models
        ]

    @staticmethod
    def _allowed_condition(restriction_ids: list[int]):
        return ~ProductModel.restrictions.any(
            DietaryRestrictionModel.id.in_(restriction_ids)
        )

    @staticmethod
    def _search_condition(search: str):
        term = search.strip()
        variants = {term, term.lower(), term.upper(), term.capitalize()}

        def escape(value: str) -> str:
            return (
                value
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )

        return or_(
            *(
                ProductModel.name.like(f"%{escape(variant)}%", escape="\\")
                for variant in variants
            )
        )

    @staticmethod
    def _to_entity(model: ProductModel) -> Product:
        return Product(
            id=model.id,
            name=model.name,
            category_id=model.category_id,
        )