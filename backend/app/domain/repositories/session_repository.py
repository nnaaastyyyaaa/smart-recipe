from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.session import Session


class SessionRepository(ABC):

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        pass

    @abstractmethod
    async def save(self, session: Session) -> None:
        pass

    @abstractmethod
    async def delete_by_token_hash(self, token_hash: str) -> None:
        pass

    @abstractmethod
    async def delete_all_by_user_id(
        self,
        user_id: UUID,
        except_token_hash: str | None = None,
    ) -> None:
        pass
