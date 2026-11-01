from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.generation_session import GenerationSession


class GenerationSessionRepository(ABC):

    @abstractmethod
    async def get(self, generation_id: UUID) -> GenerationSession | None:
        """Повертає сесію або None, якщо її немає чи термін дії минув."""

    @abstractmethod
    async def save(self, session: GenerationSession) -> None:
        """Зберігає сесію. У користувача є лише одна активна сесія."""
