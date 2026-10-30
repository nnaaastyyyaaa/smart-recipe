from pydantic import BaseModel, ConfigDict


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