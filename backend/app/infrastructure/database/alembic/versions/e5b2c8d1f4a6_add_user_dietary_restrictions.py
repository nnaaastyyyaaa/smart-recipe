"""add user dietary restrictions

Revision ID: e7b3c5d1a9f2
Revises: d4f1a9c2b7e3
Create Date: 2026-10-31 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7b3c5d1a9f2"
down_revision: Union[str, Sequence[str], None] = "d4f1a9c2b7e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_dietary_restrictions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("restriction_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["restriction_id"],
            ["dietary_restrictions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "restriction_id"),
    )


def downgrade() -> None:
    op.drop_table("user_dietary_restrictions")
