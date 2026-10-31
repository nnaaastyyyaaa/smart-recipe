import re

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=24,
        description="Ім'я від 2 до 24 символів",
    )

    email: EmailStr | None = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> "UserUpdateSchema":
        if self.name is None and self.email is None:
            raise ValueError("Вкажіть ім'я або email для зміни.")

        return self


class ChangePasswordSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)

    new_password: str = Field(
        min_length=8,
        max_length=16,
        description="Пароль від 8 до 16 символів",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_characters(cls, value: str) -> str:
        pattern = r"""[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?]+"""

        if not re.fullmatch(pattern, value):
            raise ValueError(
                "Пароль може містити лише латинські літери, цифри та дозволені спецсимволи."
            )

        return value
