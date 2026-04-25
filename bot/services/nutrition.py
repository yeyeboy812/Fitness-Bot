"""Nutrition service — meal logging and daily tracking."""

from datetime import date
from uuid import UUID

from bot.models.meal import Meal
from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.schemas.nutrition import DailySummary, MealCreate, WorkoutActivityItem


class NutritionService:
    def __init__(
        self,
        meal_repo: MealRepository,
        workout_repo: WorkoutRepository | None = None,
    ) -> None:
        self.meal_repo = meal_repo
        self.workout_repo = workout_repo

    async def log_meal(self, user_id: int, data: MealCreate) -> Meal:
        return await self.meal_repo.create_with_items(user_id, data)

    async def get_daily_meals(self, user_id: int, day: date) -> list[Meal]:
        return await self.meal_repo.get_by_date(user_id, day)

    async def get_daily_summary(
        self,
        user_id: int,
        day: date,
        *,
        calorie_norm: int | None = None,
        protein_norm: int | None = None,
        fat_norm: int | None = None,
        carb_norm: int | None = None,
    ) -> DailySummary:
        totals = await self.meal_repo.get_daily_totals(user_id, day)
        activity: dict[str, float | int] = {}
        if self.workout_repo is not None:
            activity = await self.workout_repo.get_daily_activity(user_id, day)

        eaten = float(totals["calories"])
        burned = float(activity.get("burned_calories", 0.0))

        return DailySummary(
            date=day,
            total_calories=eaten,
            total_protein=totals["protein"],
            total_fat=totals["fat"],
            total_carbs=totals["carbs"],
            calorie_norm=calorie_norm,
            protein_norm=protein_norm,
            fat_norm=fat_norm,
            carb_norm=carb_norm,
            burned_calories=burned,
            net_calories=round(eaten - burned, 1),
            workouts_count=int(activity.get("workouts_count", 0)),
            exercises_count=int(activity.get("exercises_count", 0)),
            sets_count=int(activity.get("sets_count", 0)),
            reps_count=int(activity.get("reps_count", 0)),
            duration_seconds=int(activity.get("duration_seconds", 0)),
            total_volume_kg=float(activity.get("total_volume_kg", 0.0)),
            training_minutes=int(activity.get("training_minutes", 0)),
            workout_items=[
                WorkoutActivityItem(**item)
                for item in activity.get("items", [])
            ],
        )

    async def delete_meal_item(self, user_id: int, item_id: UUID) -> bool:
        return await self.meal_repo.delete_item(user_id, item_id)
