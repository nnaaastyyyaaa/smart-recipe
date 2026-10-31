from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models.user_model import UserModel


class SqlAlchemyUserRepository(UserRepository):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        statement = select(UserModel).where(UserModel.email == email)
        result = await self.db.execute(statement)
        user_model = result.scalar_one_or_none()

        if user_model is None:
            return None

        return self._to_entity(user_model)

    async def get_by_id(self, user_id: UUID) -> User | None:
        user_model = await self.db.get(UserModel, user_id)

        if user_model is None:
            return None

        return self._to_entity(user_model)

    async def save(self, user: User) -> None:
        user_model = await self.db.get(UserModel, user.id)

        if user_model is None:
            user_model = UserModel(
                id=user.id,
                email=user.email,
                password_hash=user.password_hash,
                name=user.name,
            )

            self.db.add(user_model)
        
        else:
            user_model.email = user.email
            user_model.password_hash = user.password_hash
            user_model.name = user.name
        
        await self.db.flush()

    async def delete(self, user_id: UUID) -> None:
        await self.db.execute(
            delete(UserModel).where(UserModel.id == user_id)
        )

    @staticmethod
    def _to_entity(user_model: UserModel) -> User:
        return User(
            id=user_model.id,
            email=user_model.email,
            password_hash=user_model.password_hash,
            name=user_model.name,
        )