from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class RecipeModel(Base):
    __tablename__ = "recipes"

    __table_args__ = (
        CheckConstraint(
            "cooking_time > 0",
            name="ck_recipes_cooking_time_positive",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    ingredients: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    instructions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    cooking_time: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )