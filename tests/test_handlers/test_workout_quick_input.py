"""Workout quick set input handler."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.handlers.workout.start_workout import (
    _begin_exercise_from_message,
    on_quick_set_input,
    on_stepwise_set,
)
from bot.keyboards.workout import quick_set_input_kb
from bot.models.base import Base
from bot.models.exercise import (
    LOAD_EXTERNAL,
    LOG_MODE_REPS,
    SECTION_GYM,
    Exercise,
    ExerciseType,
    MuscleGroup,
)
from bot.models.user import User
from bot.models.workout import Workout, WorkoutSet
from bot.states.app import AppState


class FakeState:
    def __init__(self) -> None:
        self.data: dict = {}
        self.state = None

    async def update_data(self, **kwargs) -> None:
        self.data.update(kwargs)

    async def get_data(self) -> dict:
        return dict(self.data)

    async def set_state(self, state) -> None:
        self.state = state

    async def clear(self) -> None:
        self.data.clear()
        self.state = None


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _make_user_and_exercise(session: AsyncSession) -> tuple[User, Exercise]:
    user = User(id=1001, first_name="igor", weight_kg=80)
    exercise = Exercise(
        name="Махи гантелями перед собой",
        user_id=None,
        muscle_group=MuscleGroup.shoulders,
        exercise_type=ExerciseType.weight_reps,
        section=SECTION_GYM,
        log_mode=LOG_MODE_REPS,
        load_mode=LOAD_EXTERNAL,
    )
    session.add_all([user, exercise])
    await session.flush()
    return user, exercise


def _message(text: str | None = None) -> MagicMock:
    message = MagicMock()
    message.text = text
    message.answer = AsyncMock()
    return message


def _callback() -> MagicMock:
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_after_external_exercise_user_can_send_quick_set(session: AsyncSession):
    user, exercise = await _make_user_and_exercise(session)
    state = FakeState()
    message = _message()
    await state.update_data(
        exercises=[],
        workout_id=None,
        current_workout_exercise_id=None,
        next_exercise_order=1,
        workout_started_at=datetime.now(timezone.utc).isoformat(),
        current_section=SECTION_GYM,
    )

    await _begin_exercise_from_message(message, state, user, exercise)

    assert state.state == AppState.workout_quick_set_input
    prompt = message.answer.await_args.args[0]
    assert "Введи подход одним сообщением" in prompt
    markup = message.answer.await_args.kwargs["reply_markup"]
    assert any(
        button.text == "✍️ Ввести пошагово"
        for row in markup.inline_keyboard
        for button in row
    )

    message.text = "93x15"
    await on_quick_set_input(message, state, session, user)

    saved_set = await session.scalar(select(WorkoutSet))
    workout = await session.scalar(select(Workout))
    assert saved_set is not None
    assert workout is not None
    assert workout.user_id == user.id
    assert saved_set.weight_kg == 93.0
    assert saved_set.reps == 15
    assert state.state == AppState.workout_in_progress
    confirmation = message.answer.await_args.args[0]
    assert "Подход сохранён: 93 кг × 15 повторений" in confirmation
    assert "За сегодня записано: 1 упр., 1 подх." in confirmation

    await state.clear()
    assert await session.scalar(select(WorkoutSet)) is not None


@pytest.mark.asyncio
async def test_quick_set_accepts_pounds_and_converts_to_kg(session: AsyncSession):
    user, exercise = await _make_user_and_exercise(session)
    state = FakeState()
    message = _message()
    await state.update_data(
        exercises=[],
        workout_id=None,
        current_workout_exercise_id=None,
        next_exercise_order=1,
        workout_started_at=datetime.now(timezone.utc).isoformat(),
        current_section=SECTION_GYM,
    )
    await _begin_exercise_from_message(message, state, user, exercise)

    message.text = "200lb x 10"
    await on_quick_set_input(message, state, session, user)

    saved_set = await session.scalar(select(WorkoutSet))
    assert saved_set is not None
    # Stored in kg (canonical), with lb→kg conversion.
    assert round(saved_set.weight_kg, 1) == 90.7
    assert saved_set.reps == 10
    assert state.state == AppState.workout_in_progress

    confirmation = message.answer.await_args.args[0]
    assert "Подход сохранён: 200 lb × 10 повторений ≈ 90.7 кг" in confirmation


@pytest.mark.asyncio
async def test_quick_set_invalid_input_does_not_crash(session: AsyncSession):
    user, exercise = await _make_user_and_exercise(session)
    state = FakeState()
    await state.update_data(
        exercises=[],
        workout_started_at=datetime.now(timezone.utc).isoformat(),
        current_exercise_id=str(exercise.id),
        current_exercise=exercise.name,
        current_log_mode=exercise.log_mode,
        current_load_mode=exercise.load_mode,
        current_section=SECTION_GYM,
    )
    message = _message("abc")

    await on_quick_set_input(message, state, session, user)

    assert await session.scalar(select(WorkoutSet)) is None
    response = message.answer.await_args.args[0]
    assert "Не понял подход" in response


@pytest.mark.asyncio
async def test_stepwise_button_keeps_legacy_weight_prompt():
    state = FakeState()
    callback = _callback()

    await on_stepwise_set(callback, state)

    callback.message.edit_text.assert_awaited_once()
    assert "Введи вес" in callback.message.edit_text.await_args.args[0]
    assert callback.message.edit_text.await_args.kwargs["reply_markup"] is not None
    assert state.state == AppState.workout_weight_input


def test_quick_set_keyboard_has_stepwise_button():
    markup = quick_set_input_kb()

    assert any(
        button.text == "✍️ Ввести пошагово"
        and button.callback_data == "workout:stepwise_set"
        for row in markup.inline_keyboard
        for button in row
    )
