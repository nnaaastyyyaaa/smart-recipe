from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.domain.exceptions import InvalidUserNameError
from app.domain.exceptions import InvalidUserPasswordHashError

@dataclass
class User:
    email: str
    password_hash: str
    name: str
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self):
        self.name = self.name.strip()
        self.validate()

    def validate(self):
        if not (2 <= len(self.name) <= 24):
            raise InvalidUserNameError("Ім'я користувача має містити від 2 до 24 символів.")
    
    def update_password_hash(self, new_password_hash: str) -> None:
        if not new_password_hash.strip():
            raise InvalidUserPasswordHashError("Хеш пароля не може бути порожнім.")

        self.password_hash = new_password_hash
    