"""Daily nutrition summary handler.

``show_today`` is reused by both the ``/today`` command and the main-menu
dispatcher. It briefly enters the ``AppState.viewing_day`` state while
rendering so the transition shows up in the FSM logger, then clears.
"""

from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import my_day_kb
from bot.models.user import User
from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.nutrition import NutritionService
from bot.states.app import AppState
from bot.utils.formatting import format_daily_summary

router = Router(name="daily_summary")


async def show_today(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    await state.set_state(AppState.viewing_day)
    try:
        service = NutritionService(
            MealRepository(session),
            WorkoutRepository(session),
        )
        today = date.today()

        summary = await service.get_daily_summary(
            user.id,
            today,
            calorie_norm=user.calorie_norm,
            protein_norm=user.protein_norm,
            fat_norm=user.fat_norm,
            carb_norm=user.carb_norm,
        )
        meals = await service.get_daily_meals(user.id, today)

        text = format_daily_summary(summary, meals)
        await message.answer(text, reply_markup=my_day_kb())
    finally:
        await state.clear()


@router.message(Command("today"))
async def cmd_today(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    await show_today(message, state, session, user)
