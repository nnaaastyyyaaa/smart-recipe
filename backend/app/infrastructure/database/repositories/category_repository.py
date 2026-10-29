from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.category import Category
from app.domain.repositories.category_repository import CategoryRepository
from app.infrastructure.database.models.category_model import CategoryModel


class SQLAlchemyCategoryRepository(CategoryRepository):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, category_id: int) -> Category | None:
        model = await self.db.get(CategoryModel, category_id)

        if model is None:
            return None

        return self._to_entity(model)

    async def get_by_name(self, name: str) -> Category | None:
        statement = select(CategoryModel).where(CategoryModel.name == name.strip())

        result = await self.db.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def get_all(self) -> list[Category]:
        statement = select(CategoryModel).order_by(CategoryModel.name)

        result = await self.db.execute(statement)
        models = result.scalars().all()

        return [
            self._to_entity(model)
            for model in models
        ]

    @staticmethod
    def _to_entity(model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            name=model.name,
        )