from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.repositories.dietary_restriction_repository import DietaryRestrictionRepository
from app.infrastructure.database.models.dietary_restriction_model import DietaryRestrictionModel


class SQLAlchemyDietaryRestrictionRepository(DietaryRestrictionRepository):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(
        self,
        restriction_id: int,
    ) -> DietaryRestriction | None:
        model = await self.db.get(
            DietaryRestrictionModel,
            restriction_id,
        )

        if model is None:
            return None

        return self._to_entity(model)

    async def get_by_name(
        self,
        name: str,
    ) -> DietaryRestriction | None:
        statement = select(DietaryRestrictionModel).where(
            DietaryRestrictionModel.name == name.strip()
        )

        result = await self.db.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def get_all(self) -> list[DietaryRestriction]:
        statement = select(DietaryRestrictionModel).order_by(
            DietaryRestrictionModel.name
        )

        result = await self.db.execute(statement)
        models = result.scalars().all()

        return [
            self._to_entity(model)
            for model in models
        ]

    @staticmethod
    def _to_entity(
        model: DietaryRestrictionModel,
    ) -> DietaryRestriction:
        return DietaryRestriction(
            id=model.id,
            name=model.name,
        )