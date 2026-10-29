from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.associations import product_restrictions


class DietaryRestrictionModel(Base):
    __tablename__ = "dietary_restrictions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        unique=True,
    )

    products: Mapped[list["ProductModel"]] = relationship(
        secondary=product_restrictions,
        back_populates="restrictions",
    )