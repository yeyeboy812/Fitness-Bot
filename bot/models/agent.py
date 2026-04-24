"""Agent bridge models.

These tables form a typed bridge between the fitness bot and an assistant bot:
fitness bot writes events, assistant bot enqueues commands, and the fitness bot
executes those commands through application services.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class AgentEventType(enum.Enum):
    user_seen = "user_seen"
    onboarding_updated = "onboarding_updated"
    onboarding_completed = "onboarding_completed"
    menu_opened = "menu_opened"
    menu_action = "menu_action"
    shortcut_used = "shortcut_used"
    meal_logged = "meal_logged"
    product_created = "product_created"
    recipe_created = "recipe_created"
    workout_logged = "workout_logged"
    command_executed = "command_executed"


class AgentCommandType(enum.Enum):
    create_product = "create_product"
    create_recipe = "create_recipe"
    log_meal = "log_meal"
    create_shortcut = "create_shortcut"
    delete_shortcut = "delete_shortcut"
    update_user_norms = "update_user_norms"


class AgentCommandStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ShortcutActionType(enum.Enum):
    menu_action = "menu_action"
    log_meal_template = "log_meal_template"
    open_recipe = "open_recipe"


class AgentEvent(TimestampMixin, Base):
    __tablename__ = "agent_events"
    __table_args__ = (
        Index("ix_agent_events_user_created", "user_id", "created_at"),
        Index("ix_agent_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[AgentEventType] = mapped_column(
        SAEnum(AgentEventType, name="agent_event_type_enum"),
        nullable=False,
        index=True,
    )
    source_bot: Mapped[str] = mapped_column(
        String(32),
        default="fitness",
        server_default="fitness",
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user: Mapped["User | None"] = relationship(lazy="selectin")


class AgentCommand(TimestampMixin, Base):
    __tablename__ = "agent_commands"
    __table_args__ = (
        Index("ix_agent_commands_status_created", "status", "created_at"),
        Index("ix_agent_commands_user_created", "user_id", "created_at"),
        UniqueConstraint("idempotency_key", name="uq_agent_commands_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    command_type: Mapped[AgentCommandType] = mapped_column(
        SAEnum(AgentCommandType, name="agent_command_type_enum"),
        nullable=False,
        index=True,
    )
    status: Mapped[AgentCommandStatus] = mapped_column(
        SAEnum(AgentCommandStatus, name="agent_command_status_enum"),
        default=AgentCommandStatus.pending,
        server_default="pending",
        nullable=False,
        index=True,
    )
    requested_by: Mapped[str] = mapped_column(
        String(64),
        default="assistant",
        server_default="assistant",
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User | None"] = relationship(lazy="selectin")


class UserShortcut(TimestampMixin, Base):
    __tablename__ = "user_shortcuts"
    __table_args__ = (
        Index("ix_user_shortcuts_user_active_position", "user_id", "is_active", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    action_type: Mapped[ShortcutActionType] = mapped_column(
        SAEnum(ShortcutActionType, name="shortcut_action_type_enum"),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    position: Mapped[int] = mapped_column(SmallInteger, default=100, server_default="100")
    created_by: Mapped[str] = mapped_column(
        String(64),
        default="assistant",
        server_default="assistant",
        nullable=False,
    )

    user: Mapped["User | None"] = relationship(lazy="selectin")
