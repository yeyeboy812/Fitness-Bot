"""body composition: US Navy fields on users

Revision ID: 20260425_body_comp
Revises: 20260424_food_cat
Create Date: 2026-04-25

Adds optional body-composition columns to ``users``. Used to compute a
``macro_basis_weight_kg`` (lean mass for high-BMI users, full weight
otherwise) so that protein/fat targets stay realistic for very heavy
or very lean profiles instead of scaling linearly with total weight.

All columns are nullable — existing rows continue to use ``weight_kg``
as the macro basis.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260425_body_comp"
down_revision = "20260424_food_cat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("neck_cm", sa.Float(), nullable=True))
        batch.add_column(sa.Column("waist_cm", sa.Float(), nullable=True))
        batch.add_column(sa.Column("hip_cm", sa.Float(), nullable=True))
        batch.add_column(sa.Column("body_fat_percent", sa.Float(), nullable=True))
        batch.add_column(sa.Column("lean_mass_kg", sa.Float(), nullable=True))
        batch.add_column(sa.Column("macro_basis_weight_kg", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column("body_composition_method", sa.String(length=32), nullable=True)
        )
        batch.add_column(
            sa.Column("body_composition_updated_at", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("body_composition_updated_at")
        batch.drop_column("body_composition_method")
        batch.drop_column("macro_basis_weight_kg")
        batch.drop_column("lean_mass_kg")
        batch.drop_column("body_fat_percent")
        batch.drop_column("hip_cm")
        batch.drop_column("waist_cm")
        batch.drop_column("neck_cm")
