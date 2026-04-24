"""Business logic for assistant-managed shortcuts."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from bot.models.agent import ShortcutActionType, UserShortcut
from bot.repositories.agent import UserShortcutRepository
from bot.schemas.agent import ShortcutExecutionResult, UserShortcutCreate
from bot.schemas.nutrition import MealCreate, MealItemCreate
from bot.services.nutrition import NutritionService


class AgentShortcutService:
    def __init__(
        self,
        shortcut_repo: UserShortcutRepository,
        nutrition_service: NutritionService | None = None,
    ) -> None:
        self.shortcut_repo = shortcut_repo
        self.nutrition_service = nutrition_service

    async def create_shortcut(self, data: UserShortcutCreate) -> UserShortcut:
        return await self.shortcut_repo.create_shortcut(
            user_id=data.user_id,
            label=data.label,
            action_type=data.action_type,
            payload=data.payload,
            position=data.position,
            created_by=data.created_by,
        )

    async def list_menu_shortcuts(self, user_id: int, *, limit: int = 6) -> list[UserShortcut]:
        return await self.shortcut_repo.list_active_for_user(user_id, limit=limit)

    async def get_for_user(self, shortcut_id: UUID, user_id: int) -> UserShortcut | None:
        return await self.shortcut_repo.get_active_for_user(shortcut_id, user_id)

    async def execute(self, shortcut: UserShortcut, user_id: int) -> ShortcutExecutionResult:
        if shortcut.action_type == ShortcutActionType.menu_action:
            action = shortcut.payload.get("action")
            if not isinstance(action, str) or not action:
                raise ValueError("Shortcut menu action is missing")
            return ShortcutExecutionResult(
                action="menu_action",
                message="",
                payload={"action": action},
            )

        if shortcut.action_type == ShortcutActionType.log_meal_template:
            if self.nutrition_service is None:
                raise ValueError("Nutrition service is required for meal shortcuts")

            meal = await self.nutrition_service.log_meal(
                user_id,
                _meal_from_template(shortcut.payload),
            )
            return ShortcutExecutionResult(
                action="log_meal",
                message=f"Записано: {shortcut.label}",
                payload={"meal_id": str(meal.id)},
            )

        if shortcut.action_type == ShortcutActionType.open_recipe:
            recipe_id = shortcut.payload.get("recipe_id")
            if not isinstance(recipe_id, str) or not recipe_id:
                raise ValueError("Shortcut recipe_id is missing")
            return ShortcutExecutionResult(
                action="open_recipe",
                message="",
                payload={"recipe_id": recipe_id},
            )

        raise ValueError(f"Unsupported shortcut action: {shortcut.action_type}")


def _meal_from_template(payload: dict) -> MealCreate:
    meal_date = payload.get("meal_date") or date.today()
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        raise ValueError("Meal shortcut requires at least one item")

    return MealCreate(
        meal_type=payload.get("meal_type"),
        meal_date=meal_date,
        note=payload.get("note"),
        items=[MealItemCreate(**item) for item in items],
    )
