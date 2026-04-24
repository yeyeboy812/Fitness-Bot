"""Admin-only handlers and helpers."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.access import is_admin
from bot.models.meal import Meal
from bot.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="admin")


async def render_admin_dashboard(message: Message, session: AsyncSession) -> None:
    """Send the current admin dashboard to the requesting admin."""
    user_count = await session.scalar(select(func.count()).select_from(User))
    onboarded = await session.scalar(
        select(func.count()).where(User.onboarding_completed.is_(True))
    )
    meal_count = await session.scalar(select(func.count()).select_from(Meal))

    await message.answer(
        "<b>Админ-панель</b>\n\n"
        "<b>Пользователи</b>\n"
        f"Всего: {user_count}\n"
        f"Прошли онбординг: {onboarded}\n\n"
        "<b>Активность</b>\n"
        f"Записей о еде: {meal_count}"
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    user_id = message.from_user.id if message.from_user else None

    if not is_admin(user_id):
        logger.warning("Unauthorized /admin attempt from user_id=%s", user_id)
        await message.answer("У вас нет доступа к этой команде.")
        return

    await render_admin_dashboard(message, session)


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


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None

    if not is_admin(user_id):
        logger.warning("Unauthorized /settings attempt from user_id=%s", user_id)
        return

    await message.answer("Раздел настроек пока в разработке.")
