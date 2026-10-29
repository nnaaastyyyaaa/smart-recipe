from sqlalchemy import Column, ForeignKey, Table

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