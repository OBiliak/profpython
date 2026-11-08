"""add vin to cars

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-08

Generated with: alembic revision --autogenerate --rev-id 0002 -m "add vin to cars"
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the column cars.vin and a UNIQUE index on it (one VIN = one car)."""
    with op.batch_alter_table("cars") as batch_op:
        batch_op.add_column(sa.Column("vin", sa.String(length=17), nullable=True))
        batch_op.create_index("ix_cars_vin", ["vin"], unique=True)


def downgrade() -> None:
    """Remove the UNIQUE index and the column vin."""
    with op.batch_alter_table("cars") as batch_op:
        batch_op.drop_index("ix_cars_vin")
        batch_op.drop_column("vin")
