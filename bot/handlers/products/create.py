"""Manual product creation FSM flow.

Entry point (``open_create_product``) is called by the main-menu dispatcher
for the "Продукты" button. Free-text handlers apply ``NotMainMenuFilter``
so menu button labels are never captured as nutrition field values.
"""

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.menu import NotMainMenuFilter
from bot.keyboards.inline import back_to_menu_kb
from bot.keyboards.reply import MAIN_MENU
from bot.models.user import User
from bot.repositories.agent import AgentEventRepository
from bot.repositories.product import ProductRepository
from bot.schemas.product import ProductCreate
from bot.services.agent_events import AgentEventService
from bot.services.product import ProductService
from bot.states.nutrition import CreateProductSG
from bot.utils.formatting import format_nutrition_line

router = Router(name="create_product")


async def open_create_product(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Введи название нового продукта:",
        reply_markup=back_to_menu_kb(),
    )
    await state.set_state(CreateProductSG.enter_name)


@router.message(CreateProductSG.enter_name, NotMainMenuFilter())
async def on_product_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 256:
        await message.answer("Введи название продукта (до 256 символов):")
        return
    await state.update_data(name=name)
    await message.answer(
        f"Продукт: <b>{name}</b>\n\n"
        "Введи КБЖУ на 100г в одну строку через пробел:\n"
        "<code>ккал белки жиры углеводы</code>\n\n"
        "Например: <code>157 14 11 0</code>",
    )
    await state.set_state(CreateProductSG.enter_nutrition)


@router.message(CreateProductSG.enter_nutrition, NotMainMenuFilter())
async def on_nutrition(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    text = (message.text or "").strip()
    parts = text.replace(",", ".").split()

    if len(parts) != 4:
        await message.answer(
            "Нужно 4 числа через пробел: ккал белки жиры углеводы\n"
            "Например: <code>157 14 11 0</code>",
        )
        return

    try:
        cal = float(parts[0])
        protein = float(parts[1])
        fat = float(parts[2])
        carbs = float(parts[3])
    except ValueError:
        await message.answer(
            "Не удалось разобрать числа. Формат:\n"
            "<code>ккал белки жиры углеводы</code>",
        )
        return

    if not (0 <= cal <= 1000):
        await message.answer("Калорийность должна быть от 0 до 1000.")
        return
    for val, label in [(protein, "Белки"), (fat, "Жиры"), (carbs, "Углеводы")]:
        if not (0 <= val <= 100):
            await message.answer(f"{label} должны быть от 0 до 100г.")
            return

    data = await state.get_data()
    product_data = ProductCreate(
        name=data["name"],
        calories_per_100g=cal,
        protein_per_100g=protein,
        fat_per_100g=fat,
        carbs_per_100g=carbs,
    )

    service = ProductService(ProductRepository(session))
    product = await service.create_user_product(user.id, product_data)
    await AgentEventService(AgentEventRepository(session)).product_created(
        user.id,
        product.id,
        product.name,
    )

    await state.clear()
    await message.answer(
        f"Продукт <b>{product.name}</b> создан!\n\n"
        f"{format_nutrition_line(product.calories_per_100g, product.protein_per_100g, product.fat_per_100g, product.carbs_per_100g)}",
        reply_markup=MAIN_MENU,
    )
