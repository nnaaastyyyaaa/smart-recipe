from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryResponseSchema(BaseModel):
    """Категорія продуктів."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    id: int
    name: str


class ProductResponseSchema(BaseModel):
    """Продукт із каталогу."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    id: int
    name: str
    category_id: int


class DietaryRestrictionResponseSchema(BaseModel):
    """Дієтичне обмеження."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    id: int
    name: str


class RestrictionIdsUpdateSchema(BaseModel):
    """Повний новий набір дієтичних обмежень (порожній список очищає набір)."""

    model_config = ConfigDict(extra="forbid")

    restriction_ids: list[int] = Field(max_length=20)

    @field_validator("restriction_ids")
    @classmethod
    def validate_restriction_ids(cls, value: list[int]) -> list[int]:
        if any(restriction_id <= 0 for restriction_id in value):
            raise ValueError("ID обмежень повинні бути додатними.")

        if len(value) != len(set(value)):
            raise ValueError("ID обмежень не повинні повторюватися.")

        return value
