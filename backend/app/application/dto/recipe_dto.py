from pydantic import BaseModel, ConfigDict, Field, field_validator


def validate_restriction_ids(value: list[int] | None) -> list[int] | None:
    if value is None:
        return value

    if any(restriction_id <= 0 for restriction_id in value):
        raise ValueError("ID обмежень повинні бути додатними.")

    if len(value) != len(set(value)):
        raise ValueError("ID обмежень не повинні повторюватися.")

    return value


class RecipeSuggestionsRequest(BaseModel):
    """Продукти, для яких потрібно підібрати рецепти."""

    model_config = ConfigDict(extra="forbid")

    product_ids: list[int] = Field(
        min_length=2,
        max_length=30,
    )

    restriction_ids: list[int] | None = Field(
        default=None,
        max_length=20,
    )

    @field_validator("restriction_ids")
    @classmethod
    def validate_restrictions(cls, value: list[int] | None) -> list[int] | None:
        return validate_restriction_ids(value)

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, value: list[int]) -> list[int]:
        if any(product_id <= 0 for product_id in value):
            raise ValueError("ID продуктів повинні бути додатними.")

        if len(value) != len(set(value)):
            raise ValueError("ID продуктів не повинні повторюватися.")

        return value


class RecipeSuggestionSchema(BaseModel):
    """Короткий варіант рецепта від Gemini."""

    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    cooking_time: int = Field(ge=1)

    used_product_ids: list[int] = Field(
        min_length=2,
        max_length=30,
    )

    @field_validator("title", "description")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Поле не може бути порожнім.")

        return value

    @field_validator("used_product_ids")
    @classmethod
    def validate_used_product_ids(cls, value: list[int]) -> list[int]:
        if any(product_id <= 0 for product_id in value):
            raise ValueError("ID продуктів повинні бути додатними.")

        if len(value) != len(set(value)):
            raise ValueError("ID продуктів не повинні повторюватися.")

        return value


class RecipeSuggestionsResponse(BaseModel):
    """Список запропонованих рецептів."""

    recipes: list[RecipeSuggestionSchema] = Field(max_length=8)


class GenerateFullRecipeRequest(BaseModel):
    """Вибраний користувачем варіант для повної генерації."""

    model_config = ConfigDict(extra="forbid")

    suggestion: RecipeSuggestionSchema

    restriction_ids: list[int] | None = Field(
        default=None,
        max_length=20,
    )

    @field_validator("restriction_ids")
    @classmethod
    def validate_restrictions(cls, value: list[int] | None) -> list[int] | None:
        return validate_restriction_ids(value)


class RecipeGenerationSchema(BaseModel):
    """Повний рецепт від Gemini."""

    title: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1)
    ingredients: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    cooking_time: int = Field(ge=1)

    @field_validator(
        "title",
        "description",
        "ingredients",
        "instructions",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Поле не може бути порожнім.")

        return value


class RecipeResponseSchema(RecipeGenerationSchema):
    """Рецепт, який уже збережений у базі даних."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    id: int