"""Meal repository."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.models.meal import Meal, MealItem
from bot.schemas.nutrition import MealCreate

from .base import BaseRepository


class MealRepository(BaseRepository[Meal]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Meal)

    async def get_by_date(self, user_id: int, day: date) -> list[Meal]:
        """Get all meals for a user on a given date, with items loaded."""
        stmt = (
            select(Meal)
            .where(Meal.user_id == user_id, Meal.meal_date == day)
            .options(selectinload(Meal.items))
            .order_by(Meal.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_daily_totals(
        self, user_id: int, day: date
    ) -> dict[str, float]:
        """Sum of calories/protein/fat/carbs for a given date."""
        stmt = (
            select(
                func.coalesce(func.sum(MealItem.calories), 0).label("calories"),
                func.coalesce(func.sum(MealItem.protein), 0).label("protein"),
                func.coalesce(func.sum(MealItem.fat), 0).label("fat"),
                func.coalesce(func.sum(MealItem.carbs), 0).label("carbs"),
            )
            .join(Meal, MealItem.meal_id == Meal.id)
            .where(Meal.user_id == user_id, Meal.meal_date == day)
        )
        result = await self.session.execute(stmt)
        row = result.one()
        return {
            "calories": float(row.calories),
            "protein": float(row.protein),
            "fat": float(row.fat),
            "carbs": float(row.carbs),
        }

    async def create_with_items(self, user_id: int, data: MealCreate) -> Meal:
        """Create a meal with all its items in one flush."""
        meal = Meal(
            user_id=user_id,
            meal_type=data.meal_type,
            meal_date=data.meal_date,
            note=data.note,
        )
        self.session.add(meal)
        await self.session.flush()

        for item_data in data.items:
            item = MealItem(
                meal_id=meal.id,
                product_id=item_data.product_id,
                recipe_id=item_data.recipe_id,
                name_snapshot=item_data.name_snapshot,
                amount_grams=item_data.amount_grams,
                calories=item_data.calories,
                protein=item_data.protein,
                fat=item_data.fat,
                carbs=item_data.carbs,
                source=item_data.source,
            )
            self.session.add(item)

        await self.session.flush()
        return meal

    async def delete_item(self, user_id: int, item_id: UUID) -> bool:
        """Delete a meal item, ensuring the user owns it (IDOR protection)."""
        stmt = (
            select(MealItem)
            .join(Meal)
            .where(MealItem.id == item_id, Meal.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            return False
        await self.session.delete(item)
        return True
