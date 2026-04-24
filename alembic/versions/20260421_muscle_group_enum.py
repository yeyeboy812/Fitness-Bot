"""extend muscle_group_enum with arms and full_body

Revision ID: 20260421_muscle_enum
Revises: 20260420_burned
Create Date: 2026-04-21

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260421_muscle_enum"
down_revision = "20260420_burned"
branch_labels = None
depends_on = None


_NEW_VALUES = ("chest", "back", "shoulders", "arms", "biceps", "triceps",
               "legs", "abs", "full_body", "cardio", "other")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE muscle_group_enum ADD VALUE IF NOT EXISTS 'arms'")
        op.execute("ALTER TYPE muscle_group_enum ADD VALUE IF NOT EXISTS 'full_body'")
    else:
        # SQLite: rebuild CHECK constraint via batch_alter_table
        with op.batch_alter_table("exercises") as batch:
            batch.alter_column(
                "muscle_group",
                type_=sa.Enum(*_NEW_VALUES, name="muscle_group_enum"),
                existing_nullable=False,
            )


def downgrade() -> None:
    # PG doesn't support dropping enum values; leave as no-op.
    pass
