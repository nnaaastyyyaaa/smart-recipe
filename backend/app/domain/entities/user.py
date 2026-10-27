from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class User:
    email: str
    password_hash: str
    name: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        self.validate()

    def validate(self):
        if not (2 <= len(self.name) <= 24):
            raise ValueError("Ім'я користувача має містити від 2 до 24 символів.")