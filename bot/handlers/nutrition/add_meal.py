"""Handlers for adding a meal — search, text parse, photo, manual.

``open_add_food`` is the section entry point, reused by the ``/add`` command
and by the main-menu dispatcher. Free-text state handlers apply
``NotMainMenuFilter`` so menu button labels never become search queries or
gram amounts.
"""

from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.menu import NotMainMenuFilter
from bot.keyboards.inline import add_meal_method_kb, meal_type_kb
from bot.keyboards.nutrition import product_list_kb
from bot.models.user import User
from bot.repositories.meal import MealRepository
from bot.repositories.product import ProductRepository
from bot.schemas.nutrition import MealCreate, MealItemCreate, MealItemSource
from bot.services.nutrition import NutritionService
from bot.services.product import ProductService
from bot.states.app import AppState
from bot.utils.formatting import format_nutrition_line

router = Router(name="add_meal")


# ---------------------------------------------------------------------------
# Section entry point
# ---------------------------------------------------------------------------
async def open_add_food(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Как добавить еду?",
        reply_markup=add_meal_method_kb(),
    )
    await state.set_state(AppState.adding_food)


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await open_add_food(message, state)


# ---------------------------------------------------------------------------
# --- Search path ---
# ---------------------------------------------------------------------------
@router.callback_query(AppState.adding_food, F.data == "meal_method:search")
async def on_choose_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Введи название продукта для поиска:")
    await state.set_state(AppState.food_search)
    await callback.answer()


@router.message(AppState.food_search, NotMainMenuFilter())
async def on_search_query(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Введи название продукта:")
        return

    service = ProductService(ProductRepository(session))
    products = await service.search(query, user.id)

    if not products:
        await message.answer(
            "Ничего не найдено. Попробуй другой запрос или создай продукт вручную."
        )
        return

    await message.answer(
        f"Результаты по запросу «{query}»:",
        reply_markup=product_list_kb(products),
    )
    await state.set_state(AppState.food_search_results)


@router.callback_query(AppState.food_search_results, F.data.startswith("product:"))
async def on_select_product(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    product_id = callback.data.split(":")[1]
    service = ProductService(ProductRepository(session))
    product = await service.get_by_id(product_id)

    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return

    await state.update_data(
        selected_product_id=str(product.id),
        selected_product_name=product.name,
        cal_100=product.calories_per_100g,
        pro_100=product.protein_per_100g,
        fat_100=product.fat_per_100g,
        carb_100=product.carbs_per_100g,
    )
    await callback.message.edit_text(
        f"<b>{product.name}</b>\n"
        f"{format_nutrition_line(product.calories_per_100g, product.protein_per_100g, product.fat_per_100g, product.carbs_per_100g)}\n\n"
        "Сколько грамм? (например: 250)"
    )
    await state.set_state(AppState.food_amount)
    await callback.answer()


@router.message(AppState.food_amount, NotMainMenuFilter())
async def on_set_amount(message: Message, state: FSMContext) -> None:
    try:
        grams = float((message.text or "").strip().replace(",", "."))
        if grams <= 0 or grams > 5000:
            raise ValueError
    except ValueError:
        await message.answer("Введи вес в граммах (1–5000):")
        return

    data = await state.get_data()
    ratio = grams / 100.0
    cal = round(data["cal_100"] * ratio, 1)
    pro = round(data["pro_100"] * ratio, 1)
    fat = round(data["fat_100"] * ratio, 1)
    carb = round(data["carb_100"] * ratio, 1)

    await state.update_data(
        amount_grams=grams,
        cal=cal, pro=pro, fat=fat, carb=carb,
        source="search",
    )
    await message.answer(
        f"<b>{data['selected_product_name']}</b> — {grams:.0f}г\n"
        f"{format_nutrition_line(cal, pro, fat, carb)}\n\n"
        "Выбери тип приёма пищи:",
        reply_markup=meal_type_kb(),
    )
    await state.set_state(AppState.food_meal_type)


# ---------------------------------------------------------------------------
# --- Free text path ---
# ---------------------------------------------------------------------------
@router.callback_query(AppState.adding_food, F.data == "meal_method:text")
async def on_choose_text(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Опиши, что ты съел:\n"
        "(например: «250г курицы и 150г риса»)"
    )
    await state.set_state(AppState.food_text_description)
    await callback.answer()


@router.message(AppState.food_text_description, NotMainMenuFilter())
async def on_text_input(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Опиши, что ты съел:")
        return

    # AI parsing will be connected here
    await state.update_data(raw_text=text)
    await message.answer(
        "Анализ текста с помощью ИИ пока в разработке.\n"
        "Используй поиск продукта или ручной ввод.",
        reply_markup=add_meal_method_kb(),
    )
    await state.set_state(AppState.adding_food)


# ---------------------------------------------------------------------------
# --- Photo path ---
# ---------------------------------------------------------------------------
@router.callback_query(AppState.adding_food, F.data == "meal_method:photo")
async def on_choose_photo(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Отправь фото еды:")
    await state.set_state(AppState.food_photo_input)
    await callback.answer()


@router.message(AppState.food_photo_input, F.photo)
async def on_photo_input(message: Message, state: FSMContext) -> None:
    # AI photo analysis will be connected here
    await message.answer(
        "Анализ фото с помощью ИИ пока в разработке.\n"
        "Используй поиск продукта или ручной ввод.",
        reply_markup=add_meal_method_kb(),
    )
    await state.set_state(AppState.adding_food)


# ---------------------------------------------------------------------------
# --- Meal type selection and save ---
# ---------------------------------------------------------------------------
@router.callback_query(AppState.food_meal_type, F.data.startswith("meal_type:"))
async def on_meal_type(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    meal_type = callback.data.split(":")[1]
    data = await state.get_data()

    meal_data = MealCreate(
        meal_type=meal_type,
        meal_date=date.today(),
        items=[
            MealItemCreate(
                product_id=data.get("selected_product_id"),
                name_snapshot=data.get("selected_product_name", "Без названия"),
                amount_grams=data["amount_grams"],
                calories=data["cal"],
                protein=data["pro"],
                fat=data["fat"],
                carbs=data["carb"],
                source=MealItemSource(data.get("source", "manual")),
            )
        ],
    )

    service = NutritionService(MealRepository(session))
    await service.log_meal(user.id, meal_data)

    # Increment product usage if from search
    if data.get("selected_product_id"):
        product_repo = ProductRepository(session)
        await product_repo.increment_usage(data["selected_product_id"])

    await state.clear()

    type_labels = {
        "breakfast": "Завтрак",
        "lunch": "Обед",
        "dinner": "Ужин",
        "snack": "Перекус",
    }
    await callback.message.edit_text(
        f"Записано! {type_labels.get(meal_type, meal_type)}:\n"
        f"<b>{data.get('selected_product_name', '')}</b> — {data['amount_grams']:.0f}г\n"
        f"{format_nutrition_line(data['cal'], data['pro'], data['fat'], data['carb'])}"
    )
    await callback.answer("Сохранено!")
