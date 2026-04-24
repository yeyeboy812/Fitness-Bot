"""Regression tests for the multi-period stats dashboard handler + keyboard."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.handlers.analytics.dashboard import on_pick_period
from bot.keyboards.stats import stats_period_kb
from bot.models.base import Base
from bot.models.exercise import Exercise, ExerciseType, MuscleGroup
from bot.models.meal import Meal, MealItem, MealItemSource, MealType
from bot.models.user import Gender, Goal, SubscriptionTier, User
from bot.models.workout import Workout, WorkoutExercise, WorkoutSet
from bot.services.analytics import StatsPeriod


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def state() -> AsyncMock:
    """A minimal async stand-in for FSMContext — handler only calls set_state."""
    return AsyncMock()


async def _make_user(
    session: AsyncSession,
    uid: int = 1,
    *,
    pro: bool = False,
) -> User:
    u = User(id=uid, first_name="igor", gender=Gender.male, goal=Goal.maintain)
    if pro:
        u.subscription_tier = SubscriptionTier.pro
        u.subscription_expires_at = datetime(2099, 1, 1)
    session.add(u)
    await session.flush()
    return u


async def _add_meal(session: AsyncSession, user: User, day: date, cal: float) -> None:
    meal = Meal(user_id=user.id, meal_type=MealType.lunch, meal_date=day)
    session.add(meal)
    await session.flush()
    session.add(MealItem(
        meal_id=meal.id, name_snapshot="x", amount_grams=100,
        calories=cal, protein=0, fat=0, carbs=0,
        source=MealItemSource.manual,
    ))
    await session.flush()


async def _add_workout(
    session: AsyncSession, user: User, day: date,
    burned: float = 300.0, minutes: int = 45,
) -> None:
    started = datetime(day.year, day.month, day.day, 10, 0, tzinfo=timezone.utc)
    ex = Exercise(
        name="Жим", user_id=None,
        muscle_group=MuscleGroup.chest,
        exercise_type=ExerciseType.weight_reps,
    )
    session.add(ex)
    await session.flush()
    w = Workout(
        user_id=user.id, workout_date=day,
        started_at=started,
        finished_at=started + timedelta(minutes=minutes),
        estimated_calories_burned=burned,
    )
    session.add(w)
    await session.flush()
    we = WorkoutExercise(workout_id=w.id, exercise_id=ex.id, order=1)
    session.add(we)
    await session.flush()
    session.add(WorkoutSet(
        workout_exercise_id=we.id, set_number=1, weight_kg=40, reps=10,
    ))
    await session.flush()


def _mock_cb(data: str) -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.answer = AsyncMock()
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    return cb


def _edit_text_of(cb: MagicMock) -> str:
    return cb.message.edit_text.await_args.args[0]


def _edit_kb_of(cb: MagicMock):
    return cb.message.edit_text.await_args.kwargs["reply_markup"]


# ---------------------------------------------------------------------------
# Callback routing — stats:7 / stats:30 / stats:all
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,label", [
    (StatsPeriod.week.value, "7 дней"),
    (StatsPeriod.month.value, "30 дней"),
    (StatsPeriod.all_time.value, "всё время"),
])
@pytest.mark.asyncio
async def test_pick_period_renders_expected_label(session, state, raw, label):
    user = await _make_user(session, pro=raw == StatsPeriod.all_time.value)
    await _add_meal(session, user, date.today(), 500)

    cb = _mock_cb(f"stats:{raw}")
    await on_pick_period(cb, state, session, user)

    cb.message.edit_text.assert_awaited_once()
    cb.answer.assert_awaited_once_with()  # no-arg = plain ack, not alert
    text = _edit_text_of(cb)
    assert "Твоя статистика" in text
    assert label in text


@pytest.mark.asyncio
async def test_pick_period_marks_active_in_keyboard(session, state):
    user = await _make_user(session)
    await _add_meal(session, user, date.today(), 500)

    cb = _mock_cb(f"stats:{StatsPeriod.month.value}")
    await on_pick_period(cb, state, session, user)

    kb = _edit_kb_of(cb)
    marked = [
        b for row in kb.inline_keyboard for b in row
        if b.callback_data and b.callback_data.startswith("stats:")
        and b.text.startswith("• ")
    ]
    assert len(marked) == 1
    assert marked[0].callback_data == f"stats:{StatsPeriod.month.value}"


@pytest.mark.asyncio
async def test_pick_period_unknown_callback_does_not_crash(session, state):
    user = await _make_user(session)

    cb = _mock_cb("stats:999")
    await on_pick_period(cb, state, session, user)

    cb.answer.assert_awaited_once()
    assert cb.answer.await_args.kwargs.get("show_alert") is True
    cb.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_pick_period_empty_user_renders_placeholder(session, state):
    user = await _make_user(session, pro=True)

    cb = _mock_cb(f"stats:{StatsPeriod.all_time.value}")
    await on_pick_period(cb, state, session, user)

    text = _edit_text_of(cb)
    assert "недостаточно данных" in text.lower()
    # tip points to both entry points
    assert "Добавить еду" in text or "Тренировка" in text


@pytest.mark.asyncio
async def test_pick_period_only_food(session, state):
    user = await _make_user(session)
    await _add_meal(session, user, date.today(), 700)

    cb = _mock_cb(f"stats:{StatsPeriod.week.value}")
    await on_pick_period(cb, state, session, user)

    text = _edit_text_of(cb)
    assert "Съедено" in text
    assert "Приёмов пищи" in text
    # Workouts block hidden when there are none.
    assert "Тренировок" not in text


@pytest.mark.asyncio
async def test_pick_period_only_workouts(session, state):
    user = await _make_user(session)
    await _add_workout(session, user, date.today(), burned=250, minutes=30)

    cb = _mock_cb(f"stats:{StatsPeriod.week.value}")
    await on_pick_period(cb, state, session, user)

    text = _edit_text_of(cb)
    assert "Сожжено" in text
    assert "Тренировок" in text
    # Nutrition block hidden when there are no meals.
    assert "Приёмов пищи" not in text


@pytest.mark.asyncio
async def test_pick_period_all_time_shows_real_start_date(session, state):
    user = await _make_user(session, pro=True)
    today = date.today()
    first = today - timedelta(days=5)
    await _add_meal(session, user, first, 800)
    await _add_meal(session, user, today, 600)

    cb = _mock_cb(f"stats:{StatsPeriod.all_time.value}")
    await on_pick_period(cb, state, session, user)

    text = _edit_text_of(cb)
    assert "всё время" in text
    assert first.strftime("%d.%m.%Y") in text


@pytest.mark.asyncio
async def test_pick_period_all_time_requires_pro(session, state):
    user = await _make_user(session)
    await _add_meal(session, user, date.today(), 500)

    cb = _mock_cb(f"stats:{StatsPeriod.all_time.value}")
    await on_pick_period(cb, state, session, user)

    cb.answer.assert_awaited_once()
    assert cb.answer.await_args.kwargs.get("show_alert") is True
    cb.message.edit_text.assert_not_awaited()
    state.set_state.assert_not_awaited()


# ---------------------------------------------------------------------------
# Keyboard (pure UI): exactly one active period is dotted.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("active", list(StatsPeriod))
def test_stats_kb_marks_only_active_period(active):
    kb = stats_period_kb(active)
    period_buttons = [
        b for row in kb.inline_keyboard for b in row
        if b.callback_data and b.callback_data.startswith("stats:")
    ]
    assert len(period_buttons) == 3
    dotted = [b for b in period_buttons if b.text.startswith("• ")]
    assert len(dotted) == 1
    assert dotted[0].callback_data == f"stats:{active.value}"


def test_stats_kb_can_mark_all_time_as_locked():
    kb = stats_period_kb(StatsPeriod.week, all_time_locked=True)
    period_buttons = [
        b for row in kb.inline_keyboard for b in row
        if b.callback_data and b.callback_data.startswith("stats:")
    ]

    all_time = [
        b for b in period_buttons
        if b.callback_data == f"stats:{StatsPeriod.all_time.value}"
    ][0]
    assert all_time.text.startswith("🔒 ")
