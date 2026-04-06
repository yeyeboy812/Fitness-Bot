"""Workout session handlers — start, log sets, finish.

The section's entry point is exposed as ``open_workout()`` and reused by
both the ``/workout`` command and the main-menu dispatcher. State-bound
text handlers apply ``NotMainMenuFilter`` so a main-menu button label can
never be misinterpreted as free text (e.g. an exercise name or a set).
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters.menu import NotMainMenuFilter
from bot.keyboards.reply import MAIN_MENU
from bot.keyboards.workout import workout_action_kb
from bot.states.app import AppState

router = Router(name="start_workout")


# ---------------------------------------------------------------------------
# Section entry point (called from /workout and from main_menu dispatcher)
# ---------------------------------------------------------------------------
async def open_workout(message: Message, state: FSMContext) -> None:
    await message.answer(
        "Начинаем тренировку!\n\n"
        "Введи название упражнения\n"
        "(например: «Жим лёжа» или «Приседания»):",
    )
    await state.set_state(AppState.workout_name_input)


@router.message(Command("workout"))
async def cmd_start_workout(message: Message, state: FSMContext) -> None:
    await open_workout(message, state)


# ---------------------------------------------------------------------------
# Free text: exercise name
# ---------------------------------------------------------------------------
@router.message(AppState.workout_name_input, NotMainMenuFilter())
async def on_select_exercise(message: Message, state: FSMContext) -> None:
    exercise_name = (message.text or "").strip()
    if not exercise_name:
        await message.answer("Введи название упражнения:")
        return

    await state.update_data(
        current_exercise=exercise_name,
        sets=[],
    )
    await message.answer(
        f"Упражнение: <b>{exercise_name}</b>\n\n"
        "Введи подход в формате: <code>вес x повторения</code>\n"
        "(например: <code>80x10</code> или <code>80 10</code>)",
    )
    await state.set_state(AppState.workout_set_input)


# ---------------------------------------------------------------------------
# Free text: set (weight x reps)
# ---------------------------------------------------------------------------
@router.message(AppState.workout_set_input, NotMainMenuFilter())
async def on_log_set(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()

    # Parse "80x10", "80 x 10", "80 10"
    parts = text.replace("х", "x").replace("X", "x").replace("×", "x").split("x")
    if len(parts) != 2:
        parts = text.split()
    if len(parts) != 2:
        await message.answer("Формат: <code>вес x повторения</code> (например: 80x10)")
        return

    try:
        weight = float(parts[0].strip().replace(",", "."))
        reps = int(parts[1].strip())
    except ValueError:
        await message.answer("Формат: <code>вес x повторения</code> (например: 80x10)")
        return

    data = await state.get_data()
    sets = data.get("sets", [])
    sets.append({"weight": weight, "reps": reps})
    await state.update_data(sets=sets)

    sets_text = "\n".join(
        f"  {i+1}. {s['weight']}кг × {s['reps']}"
        for i, s in enumerate(sets)
    )
    await message.answer(
        f"<b>{data['current_exercise']}</b>\n{sets_text}\n\n"
        "Что дальше?",
        reply_markup=workout_action_kb(),
    )
    await state.set_state(AppState.workout_in_progress)


# ---------------------------------------------------------------------------
# Contextual inline actions (between-sets choice)
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_in_progress, F.data == "workout:add_set")
async def on_add_set(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Введи следующий подход: <code>вес x повторения</code>"
    )
    await state.set_state(AppState.workout_set_input)
    await callback.answer()


@router.callback_query(AppState.workout_in_progress, F.data == "workout:next_exercise")
async def on_next_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Введи название следующего упражнения:")
    await state.set_state(AppState.workout_name_input)
    await callback.answer()


@router.callback_query(AppState.workout_in_progress, F.data == "workout:finish")
async def on_finish_workout(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Тренировка завершена! Отличная работа!")
    await callback.message.answer("Выбери действие:", reply_markup=MAIN_MENU)
    await callback.answer()
