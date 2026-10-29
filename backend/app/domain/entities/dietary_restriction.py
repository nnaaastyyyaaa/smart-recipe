from dataclasses import dataclass

from app.domain.exceptions import InvalidDietaryRestrictionNameError


@dataclass
class DietaryRestriction:
    name: str
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise InvalidDietaryRestrictionNameError("Назва дієтичного обмеження не може бути порожньою.")

        if len(self.name) > 60:
            raise InvalidDietaryRestrictionNameError("Назва дієтичного обмеження не може перевищувати 60 символів.")