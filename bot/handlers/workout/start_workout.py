"""Workout session handlers — start, log sets, finish.

The section's entry point is exposed as ``open_workout()`` and reused by
both the ``/workout`` command and the main-menu dispatcher. State-bound
text handlers apply ``NotMainMenuFilter`` so a main-menu button label can
never be misinterpreted as free text (e.g. an exercise name or a set).
"""

from datetime import date, datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.menu import NotMainMenuFilter
from bot.keyboards.reply import MAIN_MENU
from bot.keyboards.workout import workout_action_kb, workout_start_kb
from bot.models.user import User
from bot.repositories.exercise import ExerciseRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.workout import WorkoutService, estimate_calories_burned
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
        reply_markup=workout_start_kb(),
    )
    await state.update_data(
        exercises=[],
        workout_started_at=datetime.now(timezone.utc).isoformat(),
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


def _parse_started_at(raw: object, *, fallback: datetime) -> datetime:
    """Parse ISO started_at from FSM data. Fallback on missing/bad value."""
    if not isinstance(raw, str) or not raw:
        return fallback
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _flush_current_exercise(data: dict) -> list[dict]:
    """Append the current exercise+sets to the exercises list and return it."""
    exercises = data.get("exercises", [])
    if data.get("current_exercise") and data.get("sets"):
        exercises.append({
            "name": data["current_exercise"],
            "sets": list(data["sets"]),
        })
    return exercises


@router.callback_query(AppState.workout_in_progress, F.data == "workout:next_exercise")
async def on_next_exercise(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    exercises = _flush_current_exercise(data)
    await state.update_data(exercises=exercises, current_exercise=None, sets=[])
    await callback.message.edit_text(
        "Введи название следующего упражнения:",
        reply_markup=workout_start_kb(),
    )
    await state.set_state(AppState.workout_name_input)
    await callback.answer()


@router.callback_query(AppState.workout_in_progress, F.data == "workout:finish")
async def on_finish_workout(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    data = await state.get_data()
    exercises = _flush_current_exercise(data)

    if not exercises:
        await state.clear()
        await callback.message.edit_text("Тренировка пуста — ничего не сохранено.")
        await callback.message.answer("Выбери действие:", reply_markup=MAIN_MENU)
        await callback.answer()
        return

    workout_service = WorkoutService(
        WorkoutRepository(session),
        ExerciseRepository(session),
    )

    finished_at = datetime.now(timezone.utc)
    started_at = _parse_started_at(data.get("workout_started_at"), fallback=finished_at)

    workout = await workout_service.start_workout(
        user_id=user.id,
        workout_date=date.today(),
        name=None,
        started_at=started_at,
        finished_at=finished_at,
    )

    total_sets = 0
    total_volume = 0.0
    for order, ex in enumerate(exercises, 1):
        we = await workout_service.add_exercise_to_workout(
            workout_id=workout.id,
            user_id=user.id,
            exercise_name=ex["name"],
            order=order,
        )
        for set_num, s in enumerate(ex["sets"], 1):
            await workout_service.log_set(
                workout_exercise_id=we.id,
                set_number=set_num,
                weight_kg=s.get("weight"),
                reps=s.get("reps"),
            )
            total_sets += 1
            total_volume += (s.get("weight") or 0) * (s.get("reps") or 0)

    duration_minutes = max(1, round((finished_at - started_at).total_seconds() / 60))
    workout.estimated_calories_burned = estimate_calories_burned(
        duration_minutes=duration_minutes,
        user_weight_kg=user.weight_kg,
        total_sets=total_sets,
        total_volume_kg=total_volume,
    )

    await state.clear()

    lines = ["Тренировка завершена! Отличная работа!\n"]
    for ex in exercises:
        lines.append(f"<b>{ex['name']}</b>")
        for i, s in enumerate(ex["sets"], 1):
            lines.append(f"  {i}. {s['weight']}кг × {s['reps']}")
    lines.append(
        f"\nИтого: {len(exercises)} упр., {total_sets} подх., "
        f"объём {total_volume:.0f} кг"
    )
    lines.append(
        f"⏱ Время: {duration_minutes} мин · 🔥 ~{workout.estimated_calories_burned:.0f} ккал"
    )

    await callback.message.edit_text("\n".join(lines))
    await callback.message.answer("Выбери действие:", reply_markup=MAIN_MENU)
    await callback.answer("Сохранено!")
