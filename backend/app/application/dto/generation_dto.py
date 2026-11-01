from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.dto.catalog_dto import DietaryRestrictionResponseSchema
from app.application.dto.recipe_dto import RecipeSuggestionSchema
from app.domain.entities.generation_session import GenerationStatus


# ---------- Запити ----------

class GenerationRestrictionsRequest(BaseModel):
    """Крок 1: обрані дієтичні обмеження.

    Порожній список означає "обмежень немає" — це теж свідомий вибір,
    тому поле обов'язкове.
    """

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


class GenerationSuggestionsRequest(BaseModel):
    """Крок 3: обрані продукти, для яких потрібно підібрати рецепти."""

    model_config = ConfigDict(extra="forbid")

    product_ids: list[int] = Field(min_length=2, max_length=30)

    @field_validator("product_ids")
    @classmethod
    def validate_product_ids(cls, value: list[int]) -> list[int]:
        if any(product_id <= 0 for product_id in value):
            raise ValueError("ID продуктів повинні бути додатними.")

        if len(value) != len(set(value)):
            raise ValueError("ID продуктів не повинні повторюватися.")

        return value


class GenerationRecipeRequest(BaseModel):
    """Крок 4: обраний варіант рецепта (id із сторінки варіантів)."""

    model_config = ConfigDict(extra="forbid")

    suggestion_id: int = Field(ge=0)


# ---------- Відповіді ----------

class GenerationStateSchema(BaseModel):
    """Поточний стан сесії генерації."""

    id: UUID
    status: GenerationStatus
    restrictions: list[DietaryRestrictionResponseSchema]
    product_ids: list[int]
    suggestions_total: int
    expires_at: datetime


class SuggestionItemSchema(RecipeSuggestionSchema):
    """Варіант рецепта з ідентифікатором у межах сесії генерації."""

    id: int


class SuggestionsPageSchema(BaseModel):
    """Одна сторінка варіантів рецептів."""

    items: list[SuggestionItemSchema]
    page: int
    page_size: int
    total: int
    total_pages: int
