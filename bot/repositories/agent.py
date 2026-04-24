"""Repositories for the agent bridge."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.agent import (
    AgentCommand,
    AgentCommandStatus,
    AgentCommandType,
    AgentEvent,
    AgentEventType,
    ShortcutActionType,
    UserShortcut,
)

from .base import BaseRepository


class AgentEventRepository(BaseRepository[AgentEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentEvent)

    async def record(
        self,
        event_type: AgentEventType,
        *,
        user_id: int | None = None,
        payload: dict[str, Any] | None = None,
        source_bot: str = "fitness",
    ) -> AgentEvent:
        return await self.create(
            user_id=user_id,
            event_type=event_type,
            payload=payload or {},
            source_bot=source_bot,
        )

    async def list_recent(
        self,
        *,
        user_id: int | None = None,
        event_type: AgentEventType | None = None,
        limit: int = 100,
    ) -> list[AgentEvent]:
        stmt = select(AgentEvent).order_by(AgentEvent.created_at.desc()).limit(limit)
        if user_id is not None:
            stmt = stmt.where(AgentEvent.user_id == user_id)
        if event_type is not None:
            stmt = stmt.where(AgentEvent.event_type == event_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AgentCommandRepository(BaseRepository[AgentCommand]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentCommand)

    async def enqueue(
        self,
        command_type: AgentCommandType,
        *,
        user_id: int | None = None,
        payload: dict[str, Any] | None = None,
        requested_by: str = "assistant",
        idempotency_key: str | None = None,
    ) -> AgentCommand:
        if idempotency_key:
            existing = await self.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        return await self.create(
            user_id=user_id,
            command_type=command_type,
            payload=payload or {},
            requested_by=requested_by,
            idempotency_key=idempotency_key,
        )

    async def get_by_idempotency_key(self, idempotency_key: str) -> AgentCommand | None:
        stmt = select(AgentCommand).where(AgentCommand.idempotency_key == idempotency_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_pending(self, *, limit: int = 25) -> list[AgentCommand]:
        stmt = (
            select(AgentCommand)
            .where(AgentCommand.status == AgentCommandStatus.pending)
            .order_by(AgentCommand.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_processing(self, command_id: UUID) -> AgentCommand:
        command = await self.get_by_id(command_id)
        if command is None:
            raise ValueError(f"Agent command {command_id} not found")
        command.status = AgentCommandStatus.processing
        command.attempts += 1
        command.locked_at = datetime.now(UTC).replace(tzinfo=None)
        command.error = None
        await self.session.flush()
        return command

    async def mark_completed(
        self,
        command_id: UUID,
        *,
        result_payload: dict[str, Any] | None = None,
    ) -> AgentCommand:
        command = await self.get_by_id(command_id)
        if command is None:
            raise ValueError(f"Agent command {command_id} not found")
        command.status = AgentCommandStatus.completed
        command.result_payload = result_payload or {}
        command.error = None
        command.processed_at = datetime.now(UTC).replace(tzinfo=None)
        await self.session.flush()
        return command

    async def mark_failed(self, command_id: UUID, error: str) -> AgentCommand:
        command = await self.get_by_id(command_id)
        if command is None:
            raise ValueError(f"Agent command {command_id} not found")
        command.status = AgentCommandStatus.failed
        command.error = error[:4000]
        command.processed_at = datetime.now(UTC).replace(tzinfo=None)
        await self.session.flush()
        return command


class UserShortcutRepository(BaseRepository[UserShortcut]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserShortcut)

    async def create_shortcut(
        self,
        *,
        label: str,
        action_type: ShortcutActionType,
        payload: dict[str, Any] | None = None,
        user_id: int | None = None,
        position: int = 100,
        created_by: str = "assistant",
    ) -> UserShortcut:
        return await self.create(
            user_id=user_id,
            label=label,
            action_type=action_type,
            payload=payload or {},
            position=position,
            created_by=created_by,
        )

    async def list_active_for_user(
        self,
        user_id: int,
        *,
        limit: int = 6,
    ) -> list[UserShortcut]:
        personal_first = case((UserShortcut.user_id == user_id, 0), else_=1)
        stmt = (
            select(UserShortcut)
            .where(
                UserShortcut.is_active.is_(True),
                or_(UserShortcut.user_id == user_id, UserShortcut.user_id.is_(None)),
            )
            .order_by(personal_first, UserShortcut.position, UserShortcut.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_for_user(
        self,
        shortcut_id: UUID,
        user_id: int,
    ) -> UserShortcut | None:
        stmt = select(UserShortcut).where(
            UserShortcut.id == shortcut_id,
            UserShortcut.is_active.is_(True),
            or_(UserShortcut.user_id == user_id, UserShortcut.user_id.is_(None)),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate(self, shortcut_id: UUID) -> bool:
        shortcut = await self.get_by_id(shortcut_id)
        if shortcut is None:
            return False
        shortcut.is_active = False
        await self.session.flush()
        return True
