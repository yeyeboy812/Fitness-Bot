"""Agent event recording service."""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any
from uuid import UUID

from bot.models.agent import AgentEvent, AgentEventType
from bot.models.user import User
from bot.repositories.agent import AgentEventRepository


def _jsonable(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value


class AgentEventService:
    def __init__(self, repo: AgentEventRepository) -> None:
        self.repo = repo

    async def record(
        self,
        event_type: AgentEventType,
        *,
        user_id: int | None = None,
        payload: dict[str, Any] | None = None,
        source_bot: str = "fitness",
    ) -> AgentEvent:
        return await self.repo.record(
            event_type,
            user_id=user_id,
            payload=_jsonable(payload or {}),
            source_bot=source_bot,
        )

    async def user_seen(self, user: User, *, created: bool) -> AgentEvent:
        return await self.record(
            AgentEventType.user_seen,
            user_id=user.id,
            payload={
                "created": created,
                "username": user.username,
                "first_name": user.first_name,
                "onboarding_completed": user.onboarding_completed,
            },
        )

    async def onboarding_completed(self, user: User) -> AgentEvent:
        return await self.record(
            AgentEventType.onboarding_completed,
            user_id=user.id,
            payload={
                "gender": user.gender,
                "birth_year": user.birth_year,
                "height_cm": user.height_cm,
                "weight_kg": user.weight_kg,
                "goal": user.goal,
                "activity_level": user.activity_level,
                "referral_source": user.referral_source,
                "calorie_norm": user.calorie_norm,
                "protein_norm": user.protein_norm,
                "fat_norm": user.fat_norm,
                "carb_norm": user.carb_norm,
            },
        )

    async def menu_action(self, user_id: int, action: str, *, current_state: str | None) -> AgentEvent:
        return await self.record(
            AgentEventType.menu_action,
            user_id=user_id,
            payload={"action": action, "current_state": current_state},
        )

    async def shortcut_used(self, user_id: int, shortcut_id: UUID, label: str) -> AgentEvent:
        return await self.record(
            AgentEventType.shortcut_used,
            user_id=user_id,
            payload={"shortcut_id": shortcut_id, "label": label},
        )

    async def meal_logged(
        self,
        user_id: int,
        *,
        meal_id: UUID,
        source: str,
        payload: dict[str, Any],
    ) -> AgentEvent:
        return await self.record(
            AgentEventType.meal_logged,
            user_id=user_id,
            payload={"meal_id": meal_id, "source": source, **payload},
        )

    async def product_created(self, user_id: int, product_id: UUID, name: str) -> AgentEvent:
        return await self.record(
            AgentEventType.product_created,
            user_id=user_id,
            payload={"product_id": product_id, "name": name},
        )

    async def recipe_created(self, user_id: int, recipe_id: UUID, name: str) -> AgentEvent:
        return await self.record(
            AgentEventType.recipe_created,
            user_id=user_id,
            payload={"recipe_id": recipe_id, "name": name},
        )
