"""Nutrition service — meal logging and daily tracking."""

from datetime import date
from uuid import UUID

from bot.models.meal import Meal
from bot.repositories.meal import MealRepository
from bot.schemas.nutrition import DailySummary, MealCreate


class NutritionService:
    def __init__(self, meal_repo: MealRepository) -> None:
        self.meal_repo = meal_repo

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
        return DailySummary(
            date=day,
            total_calories=totals["calories"],
            total_protein=totals["protein"],
            total_fat=totals["fat"],
            total_carbs=totals["carbs"],
            calorie_norm=calorie_norm,
            protein_norm=protein_norm,
            fat_norm=fat_norm,
            carb_norm=carb_norm,
        )

    async def delete_meal_item(self, user_id: int, item_id: UUID) -> bool:
        return await self.meal_repo.delete_item(user_id, item_id)
