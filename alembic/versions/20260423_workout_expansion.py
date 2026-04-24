"""workout expansion: exercise sections/modes + set load metadata

Revision ID: 20260423_workout_exp
Revises: 20260422_submissions
Create Date: 2026-04-23

Adds:
  - exercises.section        (nullable -> default 'gym')
  - exercises.log_mode       ('reps' | 'time')
  - exercises.load_mode      ('external_weight' | 'bodyweight_optional_extra'
                               | 'no_weight' | 'time_only')
  - workout_sets.load_mode
  - workout_sets.user_body_weight_snapshot
  - workout_sets.extra_weight_kg
  - workout_sets.effective_weight_kg

All new columns are non-destructive. Defaults fill existing rows with the
legacy assumption: gym / reps / external_weight. Workout sets fields are
all NULL for historical rows.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260423_workout_exp"
down_revision = "20260422_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exercises") as batch:
        batch.add_column(
            sa.Column(
                "section",
                sa.String(length=16),
                nullable=False,
                server_default="gym",
            )
        )
        batch.add_column(
            sa.Column(
                "log_mode",
                sa.String(length=8),
                nullable=False,
                server_default="reps",
            )
        )
        batch.add_column(
            sa.Column(
                "load_mode",
                sa.String(length=32),
                nullable=False,
                server_default="external_weight",
            )
        )

    with op.batch_alter_table("workout_sets") as batch:
        batch.add_column(sa.Column("load_mode", sa.String(length=32), nullable=True))
        batch.add_column(
            sa.Column("user_body_weight_snapshot", sa.Float(), nullable=True)
        )
        batch.add_column(sa.Column("extra_weight_kg", sa.Float(), nullable=True))
        batch.add_column(sa.Column("effective_weight_kg", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workout_sets") as batch:
        batch.drop_column("effective_weight_kg")
        batch.drop_column("extra_weight_kg")
        batch.drop_column("user_body_weight_snapshot")
        batch.drop_column("load_mode")

    with op.batch_alter_table("exercises") as batch:
        batch.drop_column("load_mode")
        batch.drop_column("log_mode")
        batch.drop_column("section")
