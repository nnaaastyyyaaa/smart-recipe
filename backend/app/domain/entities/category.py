from dataclasses import dataclass

from app.domain.exceptions import InvalidCategoryNameError

@dataclass
class Category:
    name: str
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise InvalidCategoryNameError("Назва категорії не може бути порожньою.")

        if len(self.name) > 60:
            raise InvalidCategoryNameError("Назва категорії занадто довга (максимум 60 символів).")