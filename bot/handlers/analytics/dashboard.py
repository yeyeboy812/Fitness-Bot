"""Weekly analytics dashboard.

Only entry point is the main-menu dispatcher (``show_dashboard`` is called
from ``bot.handlers.main_menu``). The router is kept for future command
bindings and for consistency with other handler modules.
"""

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import back_to_menu_kb
from bot.models.user import User
from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.analytics import AnalyticsService
from bot.states.app import AppState

router = Router(name="dashboard")


async def show_dashboard(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    await state.set_state(AppState.viewing_stats)
    try:
        service = AnalyticsService(
            meal_repo=MealRepository(session),
            workout_repo=WorkoutRepository(session),
        )

        summaries = await service.get_week_summary(user.id)
        avg_cal = await service.get_weekly_avg_calories(user.id)
        workout_count = await WorkoutRepository(session).count_user_workouts(user.id)

        lines = ["<b>Статистика за неделю:</b>\n"]
        for s in summaries:
            day_str = s.date.strftime("%d.%m")
            cal_str = f"{s.total_calories:.0f}" if s.total_calories > 0 else "—"
            lines.append(f"  {day_str}: {cal_str} ккал")

        lines.append(f"\nСреднее: <b>{avg_cal:.0f}</b> ккал/день")

        if user.calorie_norm:
            lines.append(f"Норма: {user.calorie_norm} ккал/день")

        lines.append(f"\nВсего тренировок: <b>{workout_count}</b>")

        workout_repo = WorkoutRepository(session)
        recent = await workout_repo.get_recent(user.id, limit=5)
        if recent:
            lines.append("\n<b>Последние тренировки:</b>")
            for w in recent:
                day_str = w.workout_date.strftime("%d.%m")
                total_ex = len(w.exercises)
                total_sets = sum(len(we.sets) for we in w.exercises)
                lines.append(f"  {day_str} — {total_ex} упр., {total_sets} подх.")

        await message.answer("\n".join(lines), reply_markup=back_to_menu_kb())
    finally:
        await state.clear()
