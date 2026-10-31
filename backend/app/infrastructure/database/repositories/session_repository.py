from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.session import Session
from app.domain.repositories.session_repository import SessionRepository
from app.infrastructure.database.models.session_model import SessionModel


class SqlAlchemySessionRepository(SessionRepository):

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        session_model = await self.db.get(SessionModel, token_hash)

        if session_model is None:
            return None

        return Session(
            token_hash=session_model.token_hash,
            user_id=session_model.user_id,
            expires_at=session_model.expires_at,
            created_at=session_model.created_at,
        )

    async def save(self, session: Session) -> None:
        self.db.add(
            SessionModel(
                token_hash=session.token_hash,
                user_id=session.user_id,
                expires_at=session.expires_at,
                created_at=session.created_at,
            )
        )
        await self.db.flush()

    async def delete_by_token_hash(self, token_hash: str) -> None:
        await self.db.execute(
            delete(SessionModel).where(SessionModel.token_hash == token_hash)
        )

    async def delete_all_by_user_id(
        self,
        user_id: UUID,
        except_token_hash: str | None = None,
    ) -> None:
        statement = delete(SessionModel).where(SessionModel.user_id == user_id)

        if except_token_hash is not None:
            statement = statement.where(
                SessionModel.token_hash != except_token_hash
            )

        await self.db.execute(statement)
