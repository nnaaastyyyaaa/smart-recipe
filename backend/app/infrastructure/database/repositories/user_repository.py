from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.domain.interfaces.user_repository import UserRepository
from app.infrastructure.database.models.user_model import UserModel


class SqlAlchemyUserRepository(UserRepository):

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        statement = select(UserModel).where(UserModel.email == email)
        user_model = self.db.scalar(statement)

        if user_model is None:
            return None

        return self._to_entity(user_model)

    def get_by_id(self, user_id: UUID) -> User | None:
        user_model = self.db.get(UserModel, user_id)

        if user_model is None:
            return None

        return self._to_entity(user_model)

    def save(self, user: User) -> None:
        user_model = UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            name=user.name,
        )

        self.db.add(user_model)
        self.db.commit()

    @staticmethod
    def _to_entity(user_model: UserModel) -> User:
        return User(
            id=user_model.id,
            email=user_model.email,
            password_hash=user_model.password_hash,
            name=user_model.name,
        )