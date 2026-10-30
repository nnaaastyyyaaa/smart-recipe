from uuid import UUID

from sqlalchemy import Column, ForeignKey, Table, Uuid, Integer

from app.infrastructure.database.base import Base


product_restrictions = Table(
    "product_restrictions",
    Base.metadata,
    Column(
        "product_id",
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "restriction_id",
        ForeignKey("dietary_restrictions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

saved_recipes = Table(
    "saved_recipes",
    Base.metadata,

    Column(
        "user_id",
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),

    Column(
        "recipe_id",
        Integer,
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)