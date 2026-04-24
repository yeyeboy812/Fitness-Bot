"""Streak computation — pure helper + service integration."""

from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models.base import Base
from bot.models.exercise import Exercise, ExerciseType, MuscleGroup
from bot.models.meal import Meal, MealItem, MealItemSource, MealType
from bot.models.user import Gender, Goal, User
from bot.models.workout import Workout, WorkoutExercise, WorkoutSet
from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.analytics import (
    AnalyticsService,
    StatsPeriod,
    _compute_streaks,
)


# ---------------------------------------------------------------------------
# Pure unit tests for _compute_streaks
# ---------------------------------------------------------------------------
TODAY = date(2026, 4, 21)


def test_empty_returns_zero_zero():
    assert _compute_streaks(set(), TODAY) == (0, 0)


def test_single_day_today():
    assert _compute_streaks({TODAY}, TODAY) == (1, 1)


def test_single_day_yesterday_gets_grace():
    """Yesterday-only should still count as 1 — avoids post-midnight reset."""
    assert _compute_streaks({TODAY - timedelta(days=1)}, TODAY) == (1, 1)


def test_single_day_two_days_ago_breaks_current():
    """Two days ago is past the 1-day grace window."""
    assert _compute_streaks({TODAY - timedelta(days=2)}, TODAY) == (0, 1)


def test_three_consecutive_days_ending_today():
    days = {TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
    assert _compute_streaks(days, TODAY) == (3, 3)


def test_gap_between_runs():
    """[t-5, t-4, t-3, t-1, t] — current=2, best=3."""
    days = {
        TODAY - timedelta(days=5),
        TODAY - timedelta(days=4),
        TODAY - timedelta(days=3),
        TODAY - timedelta(days=1),
        TODAY,
    }
    current, best = _compute_streaks(days, TODAY)
    assert current == 2
    assert best == 3


def test_old_streak_no_recent_activity():
    """Past streak counts for `best` but `current` is 0."""
    days = {
        TODAY - timedelta(days=30),
        TODAY - timedelta(days=29),
        TODAY - timedelta(days=28),
        TODAY - timedelta(days=27),
    }
    current, best = _compute_streaks(days, TODAY)
    assert current == 0
    assert best == 4


def test_current_can_equal_best():
    days = {TODAY - timedelta(days=i) for i in range(5)}
    assert _compute_streaks(days, TODAY) == (5, 5)


def test_grace_day_extends_into_earlier_run():
    """Today inactive, yesterday active, day-before-yesterday active → current=2."""
    days = {TODAY - timedelta(days=1), TODAY - timedelta(days=2)}
    current, best = _compute_streaks(days, TODAY)
    assert current == 2
    assert best == 2


# ---------------------------------------------------------------------------
# Service-level integration tests
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _make_user(session: AsyncSession, uid: int = 1) -> User:
    u = User(id=uid, first_name="igor", gender=Gender.male, goal=Goal.maintain)
    session.add(u)
    await session.flush()
    return u


async def _add_meal(session: AsyncSession, user: User, day: date) -> None:
    meal = Meal(user_id=user.id, meal_type=MealType.lunch, meal_date=day)
    session.add(meal)
    await session.flush()
    session.add(MealItem(
        meal_id=meal.id, name_snapshot="x", amount_grams=100,
        calories=500, protein=20, fat=10, carbs=50,
        source=MealItemSource.manual,
    ))
    await session.flush()


async def _add_workout(session: AsyncSession, user: User, day: date) -> None:
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
        finished_at=started + timedelta(minutes=30),
        estimated_calories_burned=200.0,
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


def _service(session: AsyncSession) -> AnalyticsService:
    return AnalyticsService(
        meal_repo=MealRepository(session),
        workout_repo=WorkoutRepository(session),
    )


@pytest.mark.asyncio
async def test_streak_empty_user(session: AsyncSession):
    user = await _make_user(session)
    stats = await _service(session).get_period_summary(
        user.id, StatsPeriod.week, today=TODAY
    )
    assert stats.current_streak == 0
    assert stats.best_streak == 0


@pytest.mark.asyncio
async def test_streak_food_and_workout_same_day_count_once(session: AsyncSession):
    """Meal + workout on the same day = one active day, not two."""
    user = await _make_user(session)
    await _add_meal(session, user, TODAY)
    await _add_workout(session, user, TODAY)

    stats = await _service(session).get_period_summary(
        user.id, StatsPeriod.week, today=TODAY
    )
    assert stats.current_streak == 1
    assert stats.best_streak == 1


@pytest.mark.asyncio
async def test_streak_only_food_counts_activity(session: AsyncSession):
    user = await _make_user(session)
    for i in range(3):
        await _add_meal(session, user, TODAY - timedelta(days=i))

    stats = await _service(session).get_period_summary(
        user.id, StatsPeriod.week, today=TODAY
    )
    assert stats.current_streak == 3
    assert stats.best_streak == 3


@pytest.mark.asyncio
async def test_streak_only_workouts_counts_activity(session: AsyncSession):
    user = await _make_user(session)
    for i in range(4):
        await _add_workout(session, user, TODAY - timedelta(days=i))

    stats = await _service(session).get_period_summary(
        user.id, StatsPeriod.week, today=TODAY
    )
    assert stats.current_streak == 4
    assert stats.best_streak == 4


@pytest.mark.asyncio
async def test_streak_mixed_sources_merge_into_one_streak(session: AsyncSession):
    """Meal on day A + workout on day A+1 = consecutive active days."""
    user = await _make_user(session)
    await _add_meal(session, user, TODAY - timedelta(days=1))
    await _add_workout(session, user, TODAY)

    stats = await _service(session).get_period_summary(
        user.id, StatsPeriod.week, today=TODAY
    )
    assert stats.current_streak == 2
    assert stats.best_streak == 2


@pytest.mark.asyncio
async def test_streak_period_agnostic(session: AsyncSession):
    """Streak uses full history — same value on every period tab."""
    user = await _make_user(session)
    # One run 40 days ago (outside 7/30-day windows).
    for i in range(40, 44):
        await _add_meal(session, user, TODAY - timedelta(days=i))
    # Short current run today.
    await _add_meal(session, user, TODAY)

    svc = _service(session)
    for period in StatsPeriod:
        stats = await svc.get_period_summary(user.id, period, today=TODAY)
        assert stats.current_streak == 1
        assert stats.best_streak == 4


@pytest.mark.asyncio
async def test_streak_with_gap_shows_best_from_past(session: AsyncSession):
    user = await _make_user(session)
    # Old 3-day run.
    for i in (10, 11, 12):
        await _add_meal(session, user, TODAY - timedelta(days=i))
    # Fresh 2-day run ending today.
    await _add_meal(session, user, TODAY - timedelta(days=1))
    await _add_workout(session, user, TODAY)

    stats = await _service(session).get_period_summary(
        user.id, StatsPeriod.all_time, today=TODAY
    )
    assert stats.current_streak == 2
    assert stats.best_streak == 3
