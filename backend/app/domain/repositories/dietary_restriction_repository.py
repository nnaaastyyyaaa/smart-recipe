from abc import ABC, abstractmethod

from app.domain.entities.dietary_restriction import DietaryRestriction


class DietaryRestrictionRepository(ABC):

    @abstractmethod
    async def get_by_id(
        self,
        restriction_id: int,
    ) -> DietaryRestriction | None:
        pass

    @abstractmethod
    async def get_by_name(
        self,
        name: str,
    ) -> DietaryRestriction | None:
        pass

    @abstractmethod
    async def get_by_ids(
        self,
        restriction_ids: list[int],
    ) -> list[DietaryRestriction]:
        pass

    @abstractmethod
    async def get_all(self) -> list[DietaryRestriction]:
        pass