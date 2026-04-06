"""Recipe service — create, list, calculate nutrition."""

from uuid import UUID

from bot.models.recipe import Recipe
from bot.repositories.product import ProductRepository
from bot.repositories.recipe import RecipeRepository
from bot.schemas.recipe import RecipeCreate


class RecipeService:
    def __init__(
        self,
        recipe_repo: RecipeRepository,
        product_repo: ProductRepository,
    ) -> None:
        self.recipe_repo = recipe_repo
        self.product_repo = product_repo

    async def create_recipe(self, user_id: int, data: RecipeCreate) -> Recipe:
        """Calculate nutrition from ingredients and persist the recipe."""
        total_weight = 0.0
        total_cal = 0.0
        total_pro = 0.0
        total_fat = 0.0
        total_carb = 0.0

        ingredients_data: list[dict] = []

        for ing in data.ingredients:
            ratio = ing.amount_grams / 100.0
            total_weight += ing.amount_grams
            total_cal += ing.calories_per_100g * ratio
            total_pro += ing.protein_per_100g * ratio
            total_fat += ing.fat_per_100g * ratio
            total_carb += ing.carbs_per_100g * ratio

            ingredients_data.append({
                "product_id": ing.product_id,
                "amount_grams": ing.amount_grams,
            })

        if total_weight == 0:
            raise ValueError("Recipe must have at least one ingredient")

        per_100_ratio = 100.0 / total_weight

        return await self.recipe_repo.create_with_ingredients(
            user_id=user_id,
            name=data.name,
            total_weight_grams=total_weight,
            servings=data.servings,
            calories_per_100g=round(total_cal * per_100_ratio, 1),
            protein_per_100g=round(total_pro * per_100_ratio, 1),
            fat_per_100g=round(total_fat * per_100_ratio, 1),
            carbs_per_100g=round(total_carb * per_100_ratio, 1),
            ingredients=ingredients_data,
        )

    async def get_user_recipes(self, user_id: int) -> list[Recipe]:
        return await self.recipe_repo.get_by_user(user_id)

    async def get_by_id(self, recipe_id: UUID) -> Recipe | None:
        return await self.recipe_repo.get_by_id(recipe_id)

    async def increment_usage(self, recipe_id: UUID) -> None:
        await self.recipe_repo.increment_usage(recipe_id)
