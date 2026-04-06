"""Recipe repository."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.models.recipe import Recipe, RecipeIngredient

from .base import BaseRepository


class RecipeRepository(BaseRepository[Recipe]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Recipe)

    async def get_by_user(self, user_id: int, limit: int = 20) -> list[Recipe]:
        stmt = (
            select(Recipe)
            .where(Recipe.user_id == user_id)
            .options(selectinload(Recipe.ingredients))
            .order_by(Recipe.usage_count.desc(), Recipe.name)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_with_ingredients(
        self,
        user_id: int,
        name: str,
        total_weight_grams: float,
        servings: int,
        calories_per_100g: float,
        protein_per_100g: float,
        fat_per_100g: float,
        carbs_per_100g: float,
        ingredients: list[dict],
    ) -> Recipe:
        recipe = Recipe(
            user_id=user_id,
            name=name,
            total_weight_grams=total_weight_grams,
            servings=servings,
            calories_per_100g=calories_per_100g,
            protein_per_100g=protein_per_100g,
            fat_per_100g=fat_per_100g,
            carbs_per_100g=carbs_per_100g,
        )
        self.session.add(recipe)
        await self.session.flush()

        for ing in ingredients:
            ri = RecipeIngredient(
                recipe_id=recipe.id,
                product_id=ing["product_id"],
                amount_grams=ing["amount_grams"],
            )
            self.session.add(ri)

        await self.session.flush()
        return recipe

    async def increment_usage(self, recipe_id) -> None:
        stmt = (
            update(Recipe)
            .where(Recipe.id == recipe_id)
            .values(usage_count=Recipe.usage_count + 1)
        )
        await self.session.execute(stmt)
