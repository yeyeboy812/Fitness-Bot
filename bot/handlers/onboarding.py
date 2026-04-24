"""Onboarding FSM handler — collects user profile data step by step."""

from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.onboarding import (
    activity_kb,
    gender_kb,
    goal_kb,
    onboarding_confirm_kb,
    referral_source_kb,
)
from bot.keyboards.reply import MAIN_MENU
from bot.models.user import User
from bot.repositories.agent import AgentEventRepository
from bot.repositories.user import UserRepository
from bot.schemas.user import OnboardingData
from bot.services.agent_events import AgentEventService
from bot.services.calorie_calc import (
    ActivityLevel,
    Gender,
    Goal,
    calculate_norms,
)
from bot.services.user import UserService
from bot.states.onboarding import OnboardingSG

router = Router(name="onboarding")


# --- Step 1: Name (text input) ---
@router.message(OnboardingSG.name)
async def on_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip() if message.text else ""
    if not name or len(name) > 64:
        await message.answer("Введи имя (до 64 символов):")
        return
    await state.update_data(name=name)
    await message.answer("Отлично! Укажи свой пол:", reply_markup=gender_kb())
    await state.set_state(OnboardingSG.gender)


# --- Step 2: Gender (inline) ---
@router.callback_query(OnboardingSG.gender, F.data.startswith("gender:"))
async def on_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = callback.data.split(":")[1]
    await state.update_data(gender=gender)
    await callback.message.edit_text("Какой у тебя год рождения?\n(например: 1995)")
    await state.set_state(OnboardingSG.birth_year)
    await callback.answer()


# --- Step 3: Birth year (text) ---
@router.message(OnboardingSG.birth_year)
async def on_birth_year(message: Message, state: FSMContext) -> None:
    try:
        year = int(message.text.strip())
        if year < 1940 or year > date.today().year - 10:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введи корректный год рождения (например: 1995):")
        return
    await state.update_data(birth_year=year)
    await message.answer("Какой у тебя рост в см?\n(например: 180)")
    await state.set_state(OnboardingSG.height)


# --- Step 4: Height (text) ---
@router.message(OnboardingSG.height)
async def on_height(message: Message, state: FSMContext) -> None:
    try:
        height = int(message.text.strip())
        if height < 100 or height > 250:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введи рост в сантиметрах (100–250):")
        return
    await state.update_data(height_cm=height)
    await message.answer("Какой у тебя вес в кг?\n(например: 75)")
    await state.set_state(OnboardingSG.weight)


# --- Step 5: Weight (text) ---
@router.message(OnboardingSG.weight)
async def on_weight(message: Message, state: FSMContext) -> None:
    try:
        weight = float(message.text.strip().replace(",", "."))
        if weight < 30 or weight > 300:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введи вес в килограммах (30–300):")
        return
    await state.update_data(weight_kg=weight)
    await message.answer("Какая у тебя цель?", reply_markup=goal_kb())
    await state.set_state(OnboardingSG.goal)


# --- Step 6: Goal (inline) ---
@router.callback_query(OnboardingSG.goal, F.data.startswith("goal:"))
async def on_goal(callback: CallbackQuery, state: FSMContext) -> None:
    goal = callback.data.split(":")[1]
    await state.update_data(goal=goal)
    await callback.message.edit_text(
        "Какой у тебя уровень физической активности?",
        reply_markup=activity_kb(),
    )
    await state.set_state(OnboardingSG.activity)
    await callback.answer()


# --- Step 7: Activity (inline) ---
@router.callback_query(OnboardingSG.activity, F.data.startswith("activity:"))
async def on_activity(callback: CallbackQuery, state: FSMContext) -> None:
    activity = callback.data.split(":")[1]
    await state.update_data(activity_level=activity)
    await callback.message.edit_text(
        "Сколько воды ты обычно пьёшь в день (мл)?\n"
        "(например: 2000, или 0 если не отслеживаешь)",
    )
    await state.set_state(OnboardingSG.water)
    await callback.answer()


# --- Step 8: Water (text) ---
@router.message(OnboardingSG.water)
async def on_water(message: Message, state: FSMContext) -> None:
    try:
        water = int(message.text.strip())
        if water < 0 or water > 10000:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("Введи количество воды в мл (0–10000):")
        return
    await state.update_data(daily_water_ml=water if water > 0 else None)
    await message.answer(
        "Как ты узнал о боте?",
        reply_markup=referral_source_kb(),
    )
    await state.set_state(OnboardingSG.referral_source)


# --- Step 9: Referral source (inline) ---
@router.callback_query(OnboardingSG.referral_source, F.data.startswith("ref:"))
async def on_referral(callback: CallbackQuery, state: FSMContext) -> None:
    source = callback.data.split(":")[1]
    await state.update_data(referral_source=source)

    # Calculate norms and show confirmation
    data = await state.get_data()
    age = date.today().year - data["birth_year"]
    norms = calculate_norms(
        gender=Gender(data["gender"]),
        weight_kg=data["weight_kg"],
        height_cm=data["height_cm"],
        age=age,
        activity_level=ActivityLevel(data["activity_level"]),
        goal=Goal(data["goal"]),
    )

    goal_labels = {"lose": "Похудеть", "maintain": "Поддерживать вес", "gain": "Набрать массу"}
    gender_labels = {"male": "Мужской", "female": "Женский"}

    text = (
        "Твой профиль:\n\n"
        f"Имя: <b>{data['name']}</b>\n"
        f"Пол: {gender_labels.get(data['gender'], data['gender'])}\n"
        f"Возраст: {age} лет\n"
        f"Рост: {data['height_cm']} см\n"
        f"Вес: {data['weight_kg']} кг\n"
        f"Цель: {goal_labels.get(data['goal'], data['goal'])}\n\n"
        "Твоя дневная норма:\n"
        f"Калории: <b>{norms.calories}</b> ккал\n"
        f"Белки: <b>{norms.protein_g}</b> г\n"
        f"Жиры: <b>{norms.fat_g}</b> г\n"
        f"Углеводы: <b>{norms.carbs_g}</b> г"
    )

    await callback.message.edit_text(text, reply_markup=onboarding_confirm_kb())
    await state.set_state(OnboardingSG.confirm)
    await callback.answer()


# --- Step 10: Confirm ---
@router.callback_query(OnboardingSG.confirm, F.data == "onb:confirm")
async def on_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    user_repo: UserRepository,
) -> None:
    data = await state.get_data()

    onboarding_data = OnboardingData(
        first_name=data["name"],
        gender=data["gender"],
        birth_year=data["birth_year"],
        height_cm=data["height_cm"],
        weight_kg=data["weight_kg"],
        goal=data["goal"],
        activity_level=data["activity_level"],
        daily_water_ml=data.get("daily_water_ml"),
        referral_source=data.get("referral_source"),
    )

    service = UserService(user_repo)
    updated_user = await service.complete_onboarding(user.id, onboarding_data)
    await AgentEventService(AgentEventRepository(user_repo.session)).onboarding_completed(
        updated_user
    )

    await state.clear()
    await callback.message.edit_text(
        "Отлично! Всё настроено.\n"
        "Теперь ты можешь начать отслеживать питание и тренировки!"
    )
    await callback.message.answer("Выбери действие:", reply_markup=MAIN_MENU)
    await callback.answer()


@router.callback_query(OnboardingSG.confirm, F.data == "onb:restart")
async def on_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Давай заново!\n\nКак тебя зовут?",
    )
    await state.set_state(OnboardingSG.name)
    await callback.answer()
