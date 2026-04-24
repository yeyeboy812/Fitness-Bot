"""Middleware that loads or creates the User record and injects it into handler data."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.repositories.agent import AgentEventRepository
from bot.repositories.user import UserRepository
from bot.services.agent_events import AgentEventService


class UserInjectMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession | None = data.get("session")
        tg_user = data.get("event_from_user")

        if session and tg_user:
            repo = UserRepository(session)
            user, created = await repo.get_or_create(
                telegram_id=tg_user.id,
                first_name=tg_user.first_name or "",
                username=tg_user.username,
            )
            if created:
                await AgentEventService(AgentEventRepository(session)).user_seen(
                    user,
                    created=True,
                )
            data["user"] = user
            data["user_repo"] = repo

        return await handler(event, data)
