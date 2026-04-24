"""Recipe creation FSM flow — step-by-step ingredient adding.

Entry point (``open_create_recipe``) is called by the main-menu dispatcher
for the "Рецепты" button. Free-text handlers apply ``NotMainMenuFilter``
so menu button labels are never captured as recipe names / amounts.
"""

from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.menu import NotMainMenuFilter
from bot.keyboards.inline import back_to_menu_kb
from bot.keyboards.nutrition import product_list_kb
from bot.keyboards.reply import MAIN_MENU
from bot.models.user import User
from bot.repositories.agent import AgentEventRepository
from bot.repositories.product import ProductRepository
from bot.repositories.recipe import RecipeRepository
from bot.schemas.recipe import RecipeCreate, RecipeIngredientCreate
from bot.services.agent_events import AgentEventService
from bot.services.product import ProductService
from bot.services.recipe import RecipeService
from bot.states.recipe import CreateRecipeSG
from bot.utils.formatting import format_nutrition_line

router = Router(name="create_recipe")


async def open_create_recipe(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Введи название нового рецепта:",
        reply_markup=back_to_menu_kb(),
    )
    await state.set_state(CreateRecipeSG.enter_name)


@router.message(CreateRecipeSG.enter_name, NotMainMenuFilter())
async def on_recipe_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name or len(name) > 128:
        await message.answer("Введи название рецепта (до 128 символов):")
        return
    await state.update_data(recipe_name=name, ingredients=[])
    await message.answer(
        f"Рецепт: <b>{name}</b>\n\n"
        "Найди первый ингредиент — введи название продукта:"
    )
    await state.set_state(CreateRecipeSG.search_ingredient)


@router.message(CreateRecipeSG.search_ingredient, NotMainMenuFilter())
async def on_search_ingredient(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Введи название продукта для поиска:")
        return

    service = ProductService(ProductRepository(session))
    products = await service.search(query, user.id)

    if not products:
        await message.answer("Ничего не найдено. Попробуй другой запрос:")
        return

    await message.answer(
        f"Результаты по «{query}»:",
        reply_markup=product_list_kb(products),
    )
    await state.set_state(CreateRecipeSG.select_ingredient)


@router.callback_query(CreateRecipeSG.select_ingredient, F.data.startswith("product:"))
async def on_select_ingredient(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    try:
        product_id = UUID(callback.data.split(":")[1])
    except ValueError:
        await callback.answer("Ошибка: неверный ID", show_alert=True)
        return
    service = ProductService(ProductRepository(session))
    product = await service.get_by_id(product_id)

    if not product:
        await callback.answer("Продукт не найден", show_alert=True)
        return

    await state.update_data(
        current_ingredient_id=str(product.id),
        current_ingredient_name=product.name,
        current_cal_100=product.calories_per_100g,
        current_pro_100=product.protein_per_100g,
        current_fat_100=product.fat_per_100g,
        current_carb_100=product.carbs_per_100g,
    )
    await callback.message.edit_text(
        f"<b>{product.name}</b>\n"
        f"{format_nutrition_line(product.calories_per_100g, product.protein_per_100g, product.fat_per_100g, product.carbs_per_100g)}\n\n"
        "Сколько грамм этого продукта в рецепте?"
    )
    await state.set_state(CreateRecipeSG.enter_ingredient_amount)
    await callback.answer()


@router.message(CreateRecipeSG.enter_ingredient_amount, NotMainMenuFilter())
async def on_ingredient_amount(message: Message, state: FSMContext) -> None:
    try:
        grams = float((message.text or "").strip().replace(",", "."))
        if grams <= 0 or grams > 10000:
            raise ValueError
    except ValueError:
        await message.answer("Введи вес в граммах (1–10000):")
        return

    data = await state.get_data()
    ingredients = data.get("ingredients", [])
    ingredients.append({
        "product_id": data["current_ingredient_id"],
        "product_name": data["current_ingredient_name"],
        "amount_grams": grams,
        "cal_100": data["current_cal_100"],
        "pro_100": data["current_pro_100"],
        "fat_100": data["current_fat_100"],
        "carb_100": data["current_carb_100"],
    })
    await state.update_data(ingredients=ingredients)

    # Show current ingredients list
    lines = [f"<b>{data['recipe_name']}</b> — ингредиенты:\n"]
    for i, ing in enumerate(ingredients, 1):
        lines.append(f"  {i}. {ing['product_name']} — {ing['amount_grams']:.0f}г")

    from bot.keyboards.inline import InlineKeyboardButton, InlineKeyboardMarkup

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить ингредиент", callback_data="recipe:add_more")],
        [InlineKeyboardButton(text="Готово — сохранить", callback_data="recipe:finish")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
    ])

    await message.answer("\n".join(lines), reply_markup=kb)
    await state.set_state(CreateRecipeSG.ingredient_added)


@router.callback_query(CreateRecipeSG.ingredient_added, F.data == "recipe:add_more")
async def on_add_more(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Введи название следующего ингредиента:")
    await state.set_state(CreateRecipeSG.search_ingredient)
    await callback.answer()


@router.callback_query(CreateRecipeSG.ingredient_added, F.data == "recipe:finish")
async def on_finish_recipe(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Сколько порций получается из этого рецепта?\n(например: 4)"
    )
    await state.set_state(CreateRecipeSG.enter_servings)
    await callback.answer()


@router.message(CreateRecipeSG.enter_servings, NotMainMenuFilter())
async def on_servings(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        servings = int((message.text or "").strip())
        if servings < 1 or servings > 100:
            raise ValueError
    except ValueError:
        await message.answer("Введи количество порций (1–100):")
        return

    data = await state.get_data()
    ingredients_schema = [
        RecipeIngredientCreate(
            product_id=ing["product_id"],
            product_name=ing["product_name"],
            amount_grams=ing["amount_grams"],
            calories_per_100g=ing["cal_100"],
            protein_per_100g=ing["pro_100"],
            fat_per_100g=ing["fat_100"],
            carbs_per_100g=ing["carb_100"],
        )
        for ing in data["ingredients"]
    ]

    recipe_data = RecipeCreate(
        name=data["recipe_name"],
        servings=servings,
        ingredients=ingredients_schema,
    )

    service = RecipeService(RecipeRepository(session), ProductRepository(session))
    recipe = await service.create_recipe(user.id, recipe_data)
    await AgentEventService(AgentEventRepository(session)).recipe_created(
        user.id,
        recipe.id,
        recipe.name,
    )

    await state.clear()

    serving_weight = recipe.total_weight_grams / recipe.servings
    serving_cal = recipe.calories_per_100g * serving_weight / 100

    await message.answer(
        f"Рецепт <b>{recipe.name}</b> сохранён!\n\n"
        f"Общий вес: {recipe.total_weight_grams:.0f}г\n"
        f"Порций: {recipe.servings}\n"
        f"Вес порции: {serving_weight:.0f}г\n\n"
        f"На 100г: {format_nutrition_line(recipe.calories_per_100g, recipe.protein_per_100g, recipe.fat_per_100g, recipe.carbs_per_100g)}\n"
        f"На порцию: ~{serving_cal:.0f} ккал",
        reply_markup=MAIN_MENU,
    )
