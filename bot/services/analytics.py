"""Analytics service — daily/period summaries.

The period summary powers the multi-period «Статистика» screen.
``get_week_summary`` is kept for callers that still need a per-day
breakdown; ``get_weekly_avg_calories`` delegates to the range aggregation.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date, timedelta

from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.schemas.nutrition import DailySummary


def _compute_streaks(
    active_days: set[date], today: date
) -> tuple[int, int]:
    """Compute (current, best) streaks over a set of active calendar days.

    An "active day" is a day on which the user logged any meal or workout.
    Current streak counts back from ``today`` (with a one-day grace: if
    today is inactive but yesterday is active, we still count the run
    ending yesterday — avoids a post-midnight streak reset).
    """
    if not active_days:
        return 0, 0

    if today in active_days:
        cursor = today
    elif (today - timedelta(days=1)) in active_days:
        cursor = today - timedelta(days=1)
    else:
        cursor = None

    current = 0
    while cursor is not None and cursor in active_days:
        current += 1
        cursor -= timedelta(days=1)

    best = 0
    run = 0
    prev: date | None = None
    for d in sorted(active_days):
        if prev is not None and (d - prev).days == 1:
            run += 1
        else:
            run = 1
        if run > best:
            best = run
        prev = d

    return current, best


class StatsPeriod(str, enum.Enum):
    week = "7"
    month = "30"
    all_time = "all"

    @property
    def label(self) -> str:
        return {
            StatsPeriod.week: "7 дней",
            StatsPeriod.month: "30 дней",
            StatsPeriod.all_time: "всё время",
        }[self]


@dataclass
class PeriodStats:
    period: StatsPeriod
    start: date
    end: date
    days: int           # divisor for averages; >= 1
    has_data: bool

    # Nutrition
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    meals_count: int

    # Workout
    burned_calories: float
    workouts_count: int
    exercises_count: int
    sets_count: int
    total_volume_kg: float
    training_minutes: int

    # Activity streak (period-agnostic — computed from all user history)
    current_streak: int
    best_streak: int

    @property
    def net_calories(self) -> float:
        return self.total_calories - self.burned_calories

    @property
    def avg_eaten(self) -> float:
        return self.total_calories / self.days

    @property
    def avg_burned(self) -> float:
        return self.burned_calories / self.days

    @property
    def avg_net(self) -> float:
        return self.net_calories / self.days

    @property
    def avg_protein(self) -> float:
        return self.total_protein / self.days

    @property
    def avg_fat(self) -> float:
        return self.total_fat / self.days

    @property
    def avg_carbs(self) -> float:
        return self.total_carbs / self.days


class AnalyticsService:
    def __init__(
        self,
        meal_repo: MealRepository,
        workout_repo: WorkoutRepository,
    ) -> None:
        self.meal_repo = meal_repo
        self.workout_repo = workout_repo

    # --- period summary -----------------------------------------------------
    async def get_period_summary(
        self,
        user_id: int,
        period: StatsPeriod,
        today: date | None = None,
    ) -> PeriodStats:
        end = today or date.today()
        start, days = await self._resolve_range(user_id, period, end)

        totals = await self.meal_repo.get_range_totals(user_id, start, end)
        activity = await self.workout_repo.get_range_activity(user_id, start, end)

        has_data = bool(totals["meals_count"] or activity["workouts_count"])

        meal_days = await self.meal_repo.get_active_dates(user_id)
        workout_days = await self.workout_repo.get_active_dates(user_id)
        current_streak, best_streak = _compute_streaks(
            meal_days | workout_days, end
        )

        return PeriodStats(
            period=period,
            start=start,
            end=end,
            days=days,
            has_data=has_data,
            total_calories=float(totals["calories"]),
            total_protein=float(totals["protein"]),
            total_fat=float(totals["fat"]),
            total_carbs=float(totals["carbs"]),
            meals_count=int(totals["meals_count"]),
            burned_calories=float(activity["burned_calories"]),
            workouts_count=int(activity["workouts_count"]),
            exercises_count=int(activity["exercises_count"]),
            sets_count=int(activity["sets_count"]),
            total_volume_kg=float(activity["total_volume_kg"]),
            training_minutes=int(activity["training_minutes"]),
            current_streak=current_streak,
            best_streak=best_streak,
        )

    async def _resolve_range(
        self, user_id: int, period: StatsPeriod, end: date
    ) -> tuple[date, int]:
        """Return (start_date, days_divisor). Divisor is never zero."""
        if period is StatsPeriod.week:
            return end - timedelta(days=6), 7
        if period is StatsPeriod.month:
            return end - timedelta(days=29), 30

        # all_time: earliest of meal/workout first date, fallback to today.
        first_meal = await self.meal_repo.get_first_meal_date(user_id)
        first_workout = await self.workout_repo.get_first_workout_date(user_id)
        candidates = [d for d in (first_meal, first_workout) if d is not None]
        if not candidates:
            return end, 1
        start = min(candidates)
        if start > end:
            start = end
        days = max((end - start).days + 1, 1)
        return start, days

    # --- per-day view (kept for callers that need a day-by-day breakdown) --
    async def get_week_summary(
        self,
        user_id: int,
        end_date: date | None = None,
    ) -> list[DailySummary]:
        """Get daily summaries for the last 7 days."""
        end = end_date or date.today()
        summaries: list[DailySummary] = []

        for i in range(7):
            day = end - timedelta(days=i)
            totals = await self.meal_repo.get_daily_totals(user_id, day)
            summaries.append(DailySummary(
                date=day,
                total_calories=totals["calories"],
                total_protein=totals["protein"],
                total_fat=totals["fat"],
                total_carbs=totals["carbs"],
            ))

        return summaries

    async def get_weekly_avg_calories(
        self, user_id: int, end_date: date | None = None
    ) -> float:
        """Average daily calories across the trailing 7-day window.

        Delegates to ``MealRepository.get_range_totals`` — one aggregate
        query instead of seven per-day lookups. Public signature preserved.
        """
        end = end_date or date.today()
        start = end - timedelta(days=6)
        totals = await self.meal_repo.get_range_totals(user_id, start, end)
        return round(float(totals["calories"]) / 7, 1)
