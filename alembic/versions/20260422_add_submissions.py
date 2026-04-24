"""add submissions table for collector bot

Revision ID: 20260422_submissions
Revises: 20260421_muscle_enum
Create Date: 2026-04-22

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260422_submissions"
down_revision = "20260421_muscle_enum"
branch_labels = None
depends_on = None


submission_kind_enum = sa.Enum(
    "product",
    "recipe",
    "exercise",
    name="submission_kind_enum",
)
submission_status_enum = sa.Enum(
    "pending",
    "approved",
    "rejected",
    name="submission_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        submission_kind_enum.create(bind, checkfirst=True)
        submission_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", submission_kind_enum, nullable=False),
        sa.Column(
            "status",
            submission_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "source_bot",
            sa.String(length=32),
            nullable=False,
            server_default="collector",
        ),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("target_entity", sa.String(length=32), nullable=True),
        sa.Column("target_entity_id", sa.String(length=64), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["telegram_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_submissions_status"), "submissions", ["status"], unique=False)
    op.create_index(
        op.f("ix_submissions_telegram_user_id"),
        "submissions",
        ["telegram_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_submissions_telegram_user_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_status"), table_name="submissions")
    op.drop_table("submissions")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        submission_status_enum.drop(bind, checkfirst=True)
        submission_kind_enum.drop(bind, checkfirst=True)
