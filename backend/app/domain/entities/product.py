from dataclasses import dataclass

from app.domain.exceptions import InvalidProductNameError

@dataclass
class Product:
    name: str
    category_id: int
    id: int | None = None

    def __post_init__(self):
        self.name = self.name.strip()
        self.validate()

    def validate(self):
        if not self.name or not self.name.strip():
            raise InvalidProductNameError("Назва продукту не може бути порожньою.")
        
        if len(self.name) > 60:
            raise InvalidProductNameError("Назва продукту занадто довга (максимум 60 символів).")