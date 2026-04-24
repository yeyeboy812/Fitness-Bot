"""Agent bridge schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from bot.models.agent import (
    AgentCommandStatus,
    AgentCommandType,
    AgentEventType,
    ShortcutActionType,
)


class AgentEventCreate(BaseModel):
    user_id: int | None = None
    event_type: AgentEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    source_bot: str = "fitness"


class AgentEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int | None
    event_type: AgentEventType
    source_bot: str
    payload: dict[str, Any]
    created_at: datetime


class AgentCommandCreate(BaseModel):
    user_id: int | None = None
    command_type: AgentCommandType
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "assistant"
    idempotency_key: str | None = None


class AgentCommandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int | None
    command_type: AgentCommandType
    status: AgentCommandStatus
    requested_by: str
    payload: dict[str, Any]
    result_payload: dict[str, Any] | None = None
    error: str | None = None
    attempts: int
    idempotency_key: str | None = None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None


class UserShortcutCreate(BaseModel):
    user_id: int | None = None
    label: str = Field(min_length=1, max_length=64)
    action_type: ShortcutActionType
    payload: dict[str, Any] = Field(default_factory=dict)
    position: int = 100
    created_by: str = "assistant"


class UserShortcutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int | None
    label: str
    action_type: ShortcutActionType
    payload: dict[str, Any]
    is_active: bool
    position: int
    created_by: str
    created_at: datetime


class ShortcutExecutionResult(BaseModel):
    action: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
