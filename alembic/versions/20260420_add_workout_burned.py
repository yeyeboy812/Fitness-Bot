"""add estimated_calories_burned to workouts

Revision ID: 20260420_burned
Revises:
Create Date: 2026-04-20

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260420_burned"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workouts") as batch:
        batch.add_column(
            sa.Column("estimated_calories_burned", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("workouts") as batch:
        batch.drop_column("estimated_calories_burned")
