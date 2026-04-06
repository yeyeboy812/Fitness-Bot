"""List user's saved recipes."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.repositories.product import ProductRepository
from bot.repositories.recipe import RecipeRepository
from bot.services.recipe import RecipeService
from bot.utils.formatting import format_nutrition_line

router = Router(name="list_recipes")


@router.message(F.text == "Мои рецепты")
async def list_recipes(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    service = RecipeService(RecipeRepository(session), ProductRepository(session))
    recipes = await service.get_user_recipes(user.id)

    if not recipes:
        await message.answer(
            "У тебя пока нет рецептов.\n"
            "Нажми «Рецепты», чтобы создать первый!"
        )
        return

    lines = ["<b>Твои рецепты:</b>\n"]
    for i, r in enumerate(recipes, 1):
        lines.append(
            f"{i}. <b>{r.name}</b> ({r.total_weight_grams:.0f}г, {r.servings} порц.)\n"
            f"   {format_nutrition_line(r.calories_per_100g, r.protein_per_100g, r.fat_per_100g, r.carbs_per_100g)}"
        )

    await message.answer("\n".join(lines))
