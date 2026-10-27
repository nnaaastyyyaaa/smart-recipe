import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


class UserRegisterSchema(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=24,
        description="Ім'я від 2 до 24 символів",
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=16,
        description="Пароль від 8 до 16 символів",
    )

    @field_validator("password")
    @classmethod
    def validate_password_characters(cls, value: str) -> str:
        pattern = r"""[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?]+"""

        if not re.fullmatch(pattern, value):
            raise ValueError(
                "Пароль може містити лише латинські літери, цифри та дозволені спецсимволи."
            )

        return value

class UserLoginSchema(BaseModel):
    email: EmailStr
    # Без обмежень довжини/символів: при логіні не підказуємо правила пароля
    password: str = Field(min_length=1, max_length=128)


class UserResponseSchema(BaseModel):
    id: UUID
    name: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)