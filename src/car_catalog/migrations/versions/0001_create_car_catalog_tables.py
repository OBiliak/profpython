"""create tables manufacturers and cars

Revision ID: 0001
Revises:
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create manufacturers (PRIMARY KEY, UNIQUE name) and cars (FOREIGN KEY, CHECK)."""
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("mileage", sa.Integer(), nullable=False),
        sa.Column(
            "manufacturer_id",
            sa.Integer(),
            sa.ForeignKey("manufacturers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.CheckConstraint("year BETWEEN 1950 AND 2026", name="ck_cars_year"),
        sa.CheckConstraint("price > 0", name="ck_cars_price"),
        sa.CheckConstraint("mileage >= 0", name="ck_cars_mileage"),
    )


def downgrade() -> None:
    """Drop both tables (cars first because of the foreign key)."""
    op.drop_table("cars")
    op.drop_table("manufacturers")
