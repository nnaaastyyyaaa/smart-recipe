from uuid import UUID

from app.domain.entities.generation_session import GenerationSession
from app.domain.repositories.generation_session_repository import (
    GenerationSessionRepository,
)


class InMemoryGenerationSessionRepository(GenerationSessionRepository):
    """Сховище сесій генерації в пам'яті процесу.

    Сесії короткоживучі, тому БД не потрібна. Якщо застосунок
    перезапустити, активні сесії зникнуть і користувач просто почне нову.
    """

    def __init__(self) -> None:
        self._sessions: dict[UUID, GenerationSession] = {}
        self._by_user: dict[UUID, UUID] = {}

    async def get(self, generation_id: UUID) -> GenerationSession | None:
        session = self._sessions.get(generation_id)

        if session is None:
            return None

        if session.is_expired():
            self._remove(session)
            return None

        return session

    async def save(self, session: GenerationSession) -> None:
        self._purge_expired()

        previous_id = self._by_user.get(session.user_id)

        if previous_id is not None and previous_id != session.id:
            self._sessions.pop(previous_id, None)

        self._sessions[session.id] = session
        self._by_user[session.user_id] = session.id

    def _remove(self, session: GenerationSession) -> None:
        self._sessions.pop(session.id, None)

        if self._by_user.get(session.user_id) == session.id:
            del self._by_user[session.user_id]

    def _purge_expired(self) -> None:
        expired = [
            session
            for session in self._sessions.values()
            if session.is_expired()
        ]

        for session in expired:
            self._remove(session)
