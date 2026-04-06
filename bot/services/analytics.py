"""Analytics service — weekly/monthly summaries."""

from datetime import date, timedelta

from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.schemas.nutrition import DailySummary


class AnalyticsService:
    def __init__(
        self,
        meal_repo: MealRepository,
        workout_repo: WorkoutRepository,
    ) -> None:
        self.meal_repo = meal_repo
        self.workout_repo = workout_repo

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
        summaries = await self.get_week_summary(user_id, end_date)
        total = sum(s.total_calories for s in summaries)
        return round(total / max(len(summaries), 1), 1)
