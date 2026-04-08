"""Admin commands — bot stats and management."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.models.meal import Meal
from bot.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="admin")


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.admin_ids_set


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    user_id = message.from_user.id if message.from_user else None

    if not is_admin(user_id):
        logger.warning("Unauthorized /admin attempt from user_id=%s", user_id)
        await message.answer("У вас нет доступа к этой команде.")
        return

    user_count = await session.scalar(select(func.count()).select_from(User))
    onboarded = await session.scalar(
        select(func.count()).where(User.onboarding_completed.is_(True))
    )
    meal_count = await session.scalar(select(func.count()).select_from(Meal))

    await message.answer(
        "<b>Admin Dashboard</b>\n\n"
        f"Users total: {user_count}\n"
        f"Onboarded: {onboarded}\n"
        f"Meals logged: {meal_count}"
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None

    if not is_admin(user_id):
        logger.warning("Unauthorized /broadcast attempt from user_id=%s", user_id)
        await message.answer("У вас нет доступа к этой команде.")
        return

    await message.answer(
        "Broadcast is not implemented yet.\n"
        "Usage: /broadcast <text>"
    )
