"""Multi-period analytics screen.

Three periods: 7 days (default), 30 days, all time. Users switch via the
inline keyboard under the message; the message is edited in place to avoid
chat clutter. Entry point ``show_dashboard`` is reused by the main-menu
dispatcher.
"""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.stats import stats_period_kb
from bot.models.user import User
from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.analytics import AnalyticsService, PeriodStats, StatsPeriod
from bot.services.entitlements import EntitlementService, Feature
from bot.states.app import AppState

router = Router(name="dashboard")


async def show_dashboard(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Render the default (7-day) stats screen as a fresh message."""
    await state.set_state(AppState.viewing_stats)
    stats = await _load(session, user.id, StatsPeriod.week)
    await message.answer(
        _render(stats),
        reply_markup=stats_period_kb(
            stats.period,
            all_time_locked=not EntitlementService().is_pro_active(user),
        ),
    )


@router.callback_query(F.data.startswith("stats:"))
async def on_pick_period(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    raw = callback.data.split(":", 1)[1]
    try:
        period = StatsPeriod(raw)
    except ValueError:
        await callback.answer("Неизвестный период", show_alert=True)
        return

    entitlements = EntitlementService()
    if period is StatsPeriod.all_time:
        decision = entitlements.check(user, Feature.stats_all_time)
        if not decision.allowed:
            await callback.answer(
                decision.reason or "Доступно в Pro.",
                show_alert=True,
            )
            return

    await state.set_state(AppState.viewing_stats)
    stats = await _load(session, user.id, period)
    try:
        await callback.message.edit_text(
            _render(stats),
            reply_markup=stats_period_kb(
                stats.period,
                all_time_locked=not entitlements.is_pro_active(user),
            ),
        )
    except TelegramBadRequest:
        # Telegram raises this when the new text+markup match the existing
        # message byte-for-byte (user re-tapped the active period). Silent.
        pass
    await callback.answer()


async def _load(
    session: AsyncSession, user_id: int, period: StatsPeriod
) -> PeriodStats:
    service = AnalyticsService(
        meal_repo=MealRepository(session),
        workout_repo=WorkoutRepository(session),
    )
    return await service.get_period_summary(user_id, period)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
_SEP = "━━━━━━━━━━━━━━━━━"


def _fmt_int(value: float) -> str:
    """Russian thousand-separated integer: 1807 → '1 807'."""
    return f"{int(round(value)):,}".replace(",", " ")


def _render(stats: PeriodStats) -> str:
    lines: list[str] = ["<b>Твоя статистика</b>", ""]
    lines.append(f"📆 Период: <b>{stats.period.label}</b>")
    if stats.period is StatsPeriod.all_time and stats.has_data:
        lines.append(
            f"<i>c {stats.start.strftime('%d.%m.%Y')} "
            f"({stats.days} дн.)</i>"
        )
    lines.append("")

    if not stats.has_data:
        lines.append("Пока недостаточно данных для статистики.")
        lines.append("Начни с «🍽 Добавить еду» или «🏋️ Тренировка».")
        return "\n".join(lines)

    # A. Totals
    lines.append(f"🍽 Съедено: <b>{_fmt_int(stats.total_calories)}</b> ккал")
    lines.append(f"🔥 Сожжено: <b>{_fmt_int(stats.burned_calories)}</b> ккал")
    lines.append(f"⚖️ Чистые калории: <b>{_fmt_int(stats.net_calories)}</b> ккал")
    lines.append("")

    # B. Averages
    lines.append(f"📊 Среднее съедено/день: <b>{_fmt_int(stats.avg_eaten)}</b> ккал")
    lines.append(f"📊 Среднее сожжено/день: <b>{_fmt_int(stats.avg_burned)}</b> ккал")
    lines.append(f"📊 Средний баланс/день: <b>{_fmt_int(stats.avg_net)}</b> ккал")

    # B2. Streak — compact single line, shown only when user has history.
    if stats.best_streak:
        lines.append(
            f"🔥 Серия: <b>{stats.current_streak}</b> дн. "
            f"(лучшая: <b>{stats.best_streak}</b>)"
        )

    # C. Workouts
    if stats.workouts_count:
        lines.append("")
        lines.append(_SEP)
        lines.append("")
        lines.append(f"🏋️ Тренировок: <b>{stats.workouts_count}</b>")
        lines.append(f"💪 Упражнений: <b>{stats.exercises_count}</b>")
        lines.append(f"🔁 Подходов: <b>{stats.sets_count}</b>")
        lines.append(f"📦 Объём: <b>{_fmt_int(stats.total_volume_kg)}</b> кг")
        lines.append(f"⏱ Время: <b>{stats.training_minutes}</b> мин")

    # D. Nutrition
    if stats.meals_count:
        lines.append("")
        lines.append(_SEP)
        lines.append("")
        lines.append(f"🍴 Приёмов пищи: <b>{stats.meals_count}</b>")
        lines.append(f"🥩 Белки/день: <b>{_fmt_int(stats.avg_protein)}</b> г")
        lines.append(f"🧈 Жиры/день: <b>{_fmt_int(stats.avg_fat)}</b> г")
        lines.append(f"🍞 Углеводы/день: <b>{_fmt_int(stats.avg_carbs)}</b> г")

    return "\n".join(lines)
