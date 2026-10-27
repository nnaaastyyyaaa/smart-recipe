from abc import ABC, abstractmethod

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