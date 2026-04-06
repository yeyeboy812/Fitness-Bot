"""Admin commands — bot stats and management."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.meal import Meal
from bot.models.user import User

logger = logging.getLogger(__name__)

router = Router(name="admin")

# Add your Telegram user ID here to restrict access
ADMIN_IDS: set[int] = set()


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    if ADMIN_IDS and message.from_user.id not in ADMIN_IDS:
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
    if ADMIN_IDS and message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(
        "Broadcast is not implemented yet.\n"
        "Usage: /broadcast <text>"
    )
