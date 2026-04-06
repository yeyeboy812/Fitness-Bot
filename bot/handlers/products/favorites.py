"""Show user's frequently used products."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.repositories.product import ProductRepository
from bot.services.product import ProductService
from bot.utils.formatting import format_nutrition_line

router = Router(name="favorites")


@router.message(F.text == "Частые продукты")
async def show_favorites(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    service = ProductService(ProductRepository(session))
    products = await service.get_frequent(user.id)

    if not products:
        await message.answer("У тебя пока нет часто используемых продуктов.")
        return

    lines = ["<b>Часто используемые продукты:</b>\n"]
    for i, p in enumerate(products, 1):
        lines.append(
            f"{i}. <b>{p.name}</b>\n"
            f"   {format_nutrition_line(p.calories_per_100g, p.protein_per_100g, p.fat_per_100g, p.carbs_per_100g)}"
        )

    await message.answer("\n".join(lines))
