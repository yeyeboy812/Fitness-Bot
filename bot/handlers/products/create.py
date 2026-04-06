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
from bot.keyboards.reply import MAIN_MENU
from bot.models.user import User
from bot.repositories.product import ProductRepository
from bot.schemas.product import ProductCreate
from bot.services.product import ProductService
from bot.states.nutrition import CreateProductSG
from bot.utils.formatting import format_nutrition_line

router = Router(name="create_product")


async def open_create_product(message: Message, state: FSMContext) -> None:
    await message.answer("Введи название нового продукта:")
    await state.set_state(CreateProductSG.enter_name)


@router.message(CreateProductSG.enter_name, NotMainMenuFilter())
async def on_product_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 256:
        await message.answer("Введи название продукта (до 256 символов):")
        return
    await state.update_data(name=name)
    await message.answer(f"Продукт: <b>{name}</b>\n\nСколько ккал на 100г?")
    await state.set_state(CreateProductSG.enter_calories)


@router.message(CreateProductSG.enter_calories, NotMainMenuFilter())
async def on_calories(message: Message, state: FSMContext) -> None:
    try:
        cal = float((message.text or "").strip().replace(",", "."))
        if cal < 0 or cal > 1000:
            raise ValueError
    except ValueError:
        await message.answer("Введи калорийность на 100г (0–1000):")
        return
    await state.update_data(calories=cal)
    await message.answer("Белки на 100г? (г)")
    await state.set_state(CreateProductSG.enter_protein)


@router.message(CreateProductSG.enter_protein, NotMainMenuFilter())
async def on_protein(message: Message, state: FSMContext) -> None:
    try:
        val = float((message.text or "").strip().replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError
    except ValueError:
        await message.answer("Введи белки на 100г (0–100):")
        return
    await state.update_data(protein=val)
    await message.answer("Жиры на 100г? (г)")
    await state.set_state(CreateProductSG.enter_fat)


@router.message(CreateProductSG.enter_fat, NotMainMenuFilter())
async def on_fat(message: Message, state: FSMContext) -> None:
    try:
        val = float((message.text or "").strip().replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError
    except ValueError:
        await message.answer("Введи жиры на 100г (0–100):")
        return
    await state.update_data(fat=val)
    await message.answer("Углеводы на 100г? (г)")
    await state.set_state(CreateProductSG.enter_carbs)


@router.message(CreateProductSG.enter_carbs, NotMainMenuFilter())
async def on_carbs(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        val = float((message.text or "").strip().replace(",", "."))
        if val < 0 or val > 100:
            raise ValueError
    except ValueError:
        await message.answer("Введи углеводы на 100г (0–100):")
        return

    data = await state.get_data()

    product_data = ProductCreate(
        name=data["name"],
        calories_per_100g=data["calories"],
        protein_per_100g=data["protein"],
        fat_per_100g=data["fat"],
        carbs_per_100g=val,
    )

    service = ProductService(ProductRepository(session))
    product = await service.create_user_product(user.id, product_data)

    await state.clear()
    await message.answer(
        f"Продукт <b>{product.name}</b> создан!\n\n"
        f"{format_nutrition_line(product.calories_per_100g, product.protein_per_100g, product.fat_per_100g, product.carbs_per_100g)}",
        reply_markup=MAIN_MENU,
    )
