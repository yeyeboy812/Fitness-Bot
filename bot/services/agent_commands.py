"""Executor for assistant-issued commands.

Commands are typed requests stored in SQL. The fitness bot consumes them and
uses normal services/repositories to mutate the database.
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.agent import AgentCommand, AgentCommandType, AgentEventType, ShortcutActionType
from bot.models.product import ProductSource
from bot.repositories.agent import AgentCommandRepository, AgentEventRepository, UserShortcutRepository
from bot.repositories.meal import MealRepository
from bot.repositories.product import ProductRepository
from bot.repositories.recipe import RecipeRepository
from bot.repositories.user import UserRepository
from bot.schemas.agent import UserShortcutCreate
from bot.schemas.nutrition import MealCreate
from bot.schemas.product import ProductCreate
from bot.schemas.recipe import RecipeCreate
from bot.services.agent_events import AgentEventService, _jsonable
from bot.services.agent_shortcuts import AgentShortcutService
from bot.services.nutrition import NutritionService
from bot.services.product import ProductService
from bot.services.recipe import RecipeService


class AgentCommandExecutor:
    def __init__(
        self,
        session: AsyncSession,
        command_repo: AgentCommandRepository | None = None,
        event_service: AgentEventService | None = None,
    ) -> None:
        self.session = session
        self.command_repo = command_repo or AgentCommandRepository(session)
        self.event_service = event_service or AgentEventService(AgentEventRepository(session))

    async def execute_pending(self, *, limit: int = 25) -> list[AgentCommand]:
        commands = await self.command_repo.list_pending(limit=limit)
        return [await self.execute(command) for command in commands]

    async def execute(self, command: AgentCommand) -> AgentCommand:
        command = await self.command_repo.mark_processing(command.id)
        try:
            result = await self._run(command)
        except Exception as exc:  # noqa: BLE001 - command failures are persisted, not leaked
            return await self.command_repo.mark_failed(command.id, str(exc))

        completed = await self.command_repo.mark_completed(
            command.id,
            result_payload=_jsonable(result),
        )
        await self.event_service.record(
            AgentEventType.command_executed,
            user_id=command.user_id,
            payload={
                "command_id": command.id,
                "command_type": command.command_type,
                "result": result,
            },
        )
        return completed

    async def _run(self, command: AgentCommand) -> dict[str, Any]:
        if command.command_type == AgentCommandType.create_product:
            return await self._create_product(command)
        if command.command_type == AgentCommandType.create_recipe:
            return await self._create_recipe(command)
        if command.command_type == AgentCommandType.log_meal:
            return await self._log_meal(command)
        if command.command_type == AgentCommandType.create_shortcut:
            return await self._create_shortcut(command)
        if command.command_type == AgentCommandType.delete_shortcut:
            return await self._delete_shortcut(command)
        if command.command_type == AgentCommandType.update_user_norms:
            return await self._update_user_norms(command)
        raise ValueError(f"Unsupported command type: {command.command_type}")

    async def _create_product(self, command: AgentCommand) -> dict[str, Any]:
        payload = command.payload
        product_data = ProductCreate(**payload.get("product", payload))
        scope = payload.get("scope", "user")

        if scope == "system":
            product = await ProductRepository(self.session).create(
                user_id=None,
                name=product_data.name,
                brand=product_data.brand,
                calories_per_100g=product_data.calories_per_100g,
                protein_per_100g=product_data.protein_per_100g,
                fat_per_100g=product_data.fat_per_100g,
                carbs_per_100g=product_data.carbs_per_100g,
                is_verified=True,
                source=ProductSource.system,
            )
        else:
            user_id = _required_user_id(command)
            product = await ProductService(ProductRepository(self.session)).create_user_product(
                user_id,
                product_data,
            )

        return {"entity": "product", "id": str(product.id), "name": product.name}

    async def _create_recipe(self, command: AgentCommand) -> dict[str, Any]:
        user_id = _required_user_id(command)
        recipe_data = RecipeCreate(**command.payload.get("recipe", command.payload))
        recipe = await RecipeService(
            RecipeRepository(self.session),
            ProductRepository(self.session),
        ).create_recipe(user_id, recipe_data)
        return {"entity": "recipe", "id": str(recipe.id), "name": recipe.name}

    async def _log_meal(self, command: AgentCommand) -> dict[str, Any]:
        user_id = _required_user_id(command)
        payload = dict(command.payload.get("meal", command.payload))
        payload.setdefault("meal_date", date.today())
        meal = await NutritionService(MealRepository(self.session)).log_meal(
            user_id,
            MealCreate(**payload),
        )
        return {"entity": "meal", "id": str(meal.id)}

    async def _create_shortcut(self, command: AgentCommand) -> dict[str, Any]:
        payload = dict(command.payload.get("shortcut", command.payload))
        payload.setdefault("user_id", command.user_id)
        if payload.get("action_type") == ShortcutActionType.menu_action.value:
            action = payload.get("payload", {}).get("action")
            if not isinstance(action, str) or not action:
                raise ValueError("menu_action shortcut requires payload.action")

        shortcut = await AgentShortcutService(
            UserShortcutRepository(self.session)
        ).create_shortcut(UserShortcutCreate(**payload))
        return {"entity": "shortcut", "id": str(shortcut.id), "label": shortcut.label}

    async def _delete_shortcut(self, command: AgentCommand) -> dict[str, Any]:
        shortcut_id = UUID(str(command.payload["shortcut_id"]))
        deleted = await UserShortcutRepository(self.session).deactivate(shortcut_id)
        return {"entity": "shortcut", "id": str(shortcut_id), "deactivated": deleted}

    async def _update_user_norms(self, command: AgentCommand) -> dict[str, Any]:
        user_id = _required_user_id(command)
        allowed = {"calorie_norm", "protein_norm", "fat_norm", "carb_norm"}
        values = {
            key: value
            for key, value in command.payload.items()
            if key in allowed and (value is None or isinstance(value, int))
        }
        if not values:
            raise ValueError("No valid norm fields supplied")

        user = await UserRepository(self.session).update_profile(user_id, **values)
        return {
            "entity": "user",
            "id": user.id,
            "calorie_norm": user.calorie_norm,
            "protein_norm": user.protein_norm,
            "fat_norm": user.fat_norm,
            "carb_norm": user.carb_norm,
        }


def _required_user_id(command: AgentCommand) -> int:
    user_id = command.user_id or command.payload.get("user_id")
    if not isinstance(user_id, int):
        raise ValueError("Command requires user_id")
    return user_id
