from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.dietary_restriction import DietaryRestriction


class UserDietaryRestrictionRepository(ABC):

    @abstractmethod
    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> list[DietaryRestriction]:
        pass

    @abstractmethod
    async def replace(
        self,
        user_id: UUID,
        restriction_ids: list[int],
    ) -> None:
        pass
