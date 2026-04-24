"""food catalog: category / barcode / default_unit / confidence + alias normalization

Revision ID: 20260424_food_cat
Revises: 20260423_agent_bridge
Create Date: 2026-04-24

Adds food-catalog metadata to products:
  - category   (nullable, indexed)   — 'крупы' / 'мясо' / 'молочка' / ...
  - barcode    (nullable)            — EAN/UPC when known
  - default_unit (NOT NULL, 'g')     — 'g' | 'ml' | 'piece'
  - confidence (NOT NULL, 1.0)       — 0..1, lower for unverified brand data

Adds normalized_alias to product_aliases (NOT NULL, '') and indexes it for
fast search lookup.

Extends product_source_enum with: label, openfoodfacts, manual_pending.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260424_food_cat"
down_revision = "20260423_agent_bridge"
branch_labels = None
depends_on = None


_NEW_SOURCE_VALUES = ("label", "openfoodfacts", "manual_pending")


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # --- products: new columns -------------------------------------------
    with op.batch_alter_table("products") as batch:
        batch.add_column(
            sa.Column("category", sa.String(length=64), nullable=True)
        )
        batch.add_column(
            sa.Column("barcode", sa.String(length=32), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "default_unit",
                sa.String(length=16),
                nullable=False,
                server_default="g",
            )
        )
        batch.add_column(
            sa.Column(
                "confidence",
                sa.Float(),
                nullable=False,
                server_default="1.0",
            )
        )
    op.create_index(
        "ix_products_category", "products", ["category"], unique=False
    )

    # --- product_aliases: normalized_alias -------------------------------
    with op.batch_alter_table("product_aliases") as batch:
        batch.add_column(
            sa.Column(
                "normalized_alias",
                sa.String(length=256),
                nullable=False,
                server_default="",
            )
        )
    op.create_index(
        "ix_product_aliases_normalized",
        "product_aliases",
        ["normalized_alias"],
        unique=False,
    )

    # --- enum extension --------------------------------------------------
    if is_pg:
        for value in _NEW_SOURCE_VALUES:
            op.execute(
                f"ALTER TYPE product_source_enum ADD VALUE IF NOT EXISTS '{value}'"
            )
    # SQLite: SAEnum is a VARCHAR + CHECK constraint; batch_alter_table above
    # already rebuilt the table without the old CHECK, so new values insert
    # freely. No explicit action required.


def downgrade() -> None:
    op.drop_index("ix_product_aliases_normalized", table_name="product_aliases")
    with op.batch_alter_table("product_aliases") as batch:
        batch.drop_column("normalized_alias")

    op.drop_index("ix_products_category", table_name="products")
    with op.batch_alter_table("products") as batch:
        batch.drop_column("confidence")
        batch.drop_column("default_unit")
        batch.drop_column("barcode")
        batch.drop_column("category")

    # Note: PostgreSQL does not support removing enum values without
    # rebuilding the type — downgrade leaves the added values in place.
