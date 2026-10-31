from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.dietary_restriction import DietaryRestriction
from app.domain.repositories.user_dietary_restriction_repository import (
    UserDietaryRestrictionRepository,
)
from app.infrastructure.database.models.associations import (
    user_dietary_restrictions,
)
from app.infrastructure.database.models.dietary_restriction_model import (
    DietaryRestrictionModel,
)


class SQLAlchemyUserDietaryRestrictionRepository(
    UserDietaryRestrictionRepository
):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> list[DietaryRestriction]:
        statement = (
            select(DietaryRestrictionModel)
            .join(
                user_dietary_restrictions,
                user_dietary_restrictions.c.restriction_id
                == DietaryRestrictionModel.id,
            )
            .where(user_dietary_restrictions.c.user_id == user_id)
            .order_by(DietaryRestrictionModel.name)
        )

        result = await self.db.execute(statement)
        models = result.scalars().all()

        return [
            DietaryRestriction(id=model.id, name=model.name)
            for model in models
        ]

    async def replace(
        self,
        user_id: UUID,
        restriction_ids: list[int],
    ) -> None:
        await self.db.execute(
            delete(user_dietary_restrictions).where(
                user_dietary_restrictions.c.user_id == user_id
            )
        )

        if restriction_ids:
            await self.db.execute(
                insert(user_dietary_restrictions),
                [
                    {"user_id": user_id, "restriction_id": restriction_id}
                    for restriction_id in restriction_ids
                ],
            )

        await self.db.flush()
