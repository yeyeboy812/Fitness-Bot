"""add agent bridge tables

Revision ID: 20260423_agent_bridge
Revises: 20260423_workout_exp
Create Date: 2026-04-23

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260423_agent_bridge"
down_revision = "20260423_workout_exp"
branch_labels = None
depends_on = None


agent_event_type_enum = sa.Enum(
    "user_seen",
    "onboarding_updated",
    "onboarding_completed",
    "menu_opened",
    "menu_action",
    "shortcut_used",
    "meal_logged",
    "product_created",
    "recipe_created",
    "workout_logged",
    "command_executed",
    name="agent_event_type_enum",
)
agent_command_type_enum = sa.Enum(
    "create_product",
    "create_recipe",
    "log_meal",
    "create_shortcut",
    "delete_shortcut",
    "update_user_norms",
    name="agent_command_type_enum",
)
agent_command_status_enum = sa.Enum(
    "pending",
    "processing",
    "completed",
    "failed",
    "cancelled",
    name="agent_command_status_enum",
)
shortcut_action_type_enum = sa.Enum(
    "menu_action",
    "log_meal_template",
    "open_recipe",
    name="shortcut_action_type_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        agent_event_type_enum.create(bind, checkfirst=True)
        agent_command_type_enum.create(bind, checkfirst=True)
        agent_command_status_enum.create(bind, checkfirst=True)
        shortcut_action_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "agent_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", agent_event_type_enum, nullable=False),
        sa.Column("source_bot", sa.String(length=32), server_default="fitness", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_events_event_type"), "agent_events", ["event_type"])
    op.create_index(op.f("ix_agent_events_user_id"), "agent_events", ["user_id"])
    op.create_index(
        "ix_agent_events_type_created",
        "agent_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_agent_events_user_created",
        "agent_events",
        ["user_id", "created_at"],
    )

    op.create_table(
        "agent_commands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("command_type", agent_command_type_enum, nullable=False),
        sa.Column(
            "status",
            agent_command_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            sa.String(length=64),
            server_default="assistant",
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_agent_commands_idempotency_key"),
    )
    op.create_index(op.f("ix_agent_commands_command_type"), "agent_commands", ["command_type"])
    op.create_index(op.f("ix_agent_commands_status"), "agent_commands", ["status"])
    op.create_index(op.f("ix_agent_commands_user_id"), "agent_commands", ["user_id"])
    op.create_index(
        "ix_agent_commands_status_created",
        "agent_commands",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_agent_commands_user_created",
        "agent_commands",
        ["user_id", "created_at"],
    )

    op.create_table(
        "user_shortcuts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("action_type", shortcut_action_type_enum, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("position", sa.SmallInteger(), server_default="100", nullable=False),
        sa.Column(
            "created_by",
            sa.String(length=64),
            server_default="assistant",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_shortcuts_user_id"), "user_shortcuts", ["user_id"])
    op.create_index(
        "ix_user_shortcuts_user_active_position",
        "user_shortcuts",
        ["user_id", "is_active", "position"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_shortcuts_user_active_position", table_name="user_shortcuts")
    op.drop_index(op.f("ix_user_shortcuts_user_id"), table_name="user_shortcuts")
    op.drop_table("user_shortcuts")

    op.drop_index("ix_agent_commands_user_created", table_name="agent_commands")
    op.drop_index("ix_agent_commands_status_created", table_name="agent_commands")
    op.drop_index(op.f("ix_agent_commands_user_id"), table_name="agent_commands")
    op.drop_index(op.f("ix_agent_commands_status"), table_name="agent_commands")
    op.drop_index(op.f("ix_agent_commands_command_type"), table_name="agent_commands")
    op.drop_table("agent_commands")

    op.drop_index("ix_agent_events_user_created", table_name="agent_events")
    op.drop_index("ix_agent_events_type_created", table_name="agent_events")
    op.drop_index(op.f("ix_agent_events_user_id"), table_name="agent_events")
    op.drop_index(op.f("ix_agent_events_event_type"), table_name="agent_events")
    op.drop_table("agent_events")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        shortcut_action_type_enum.drop(bind, checkfirst=True)
        agent_command_status_enum.drop(bind, checkfirst=True)
        agent_command_type_enum.drop(bind, checkfirst=True)
        agent_event_type_enum.drop(bind, checkfirst=True)
