"""Multi-period analytics aggregation."""

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
from bot.services.analytics import AnalyticsService, StatsPeriod


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _make_user(session: AsyncSession, tg_id: int = 777) -> User:
    user = User(
        id=tg_id,
        first_name="igor",
        gender=Gender.male,
        goal=Goal.maintain,
    )
    session.add(user)
    await session.flush()
    return user


def _make_service(session: AsyncSession) -> AnalyticsService:
    return AnalyticsService(
        meal_repo=MealRepository(session),
        workout_repo=WorkoutRepository(session),
    )


async def _add_meal(
    session: AsyncSession, user: User, day: date, calories: float, protein: float = 0.0
) -> None:
    meal = Meal(user_id=user.id, meal_type=MealType.lunch, meal_date=day)
    session.add(meal)
    await session.flush()
    session.add(MealItem(
        meal_id=meal.id,
        name_snapshot="x",
        amount_grams=100,
        calories=calories,
        protein=protein,
        fat=0,
        carbs=0,
        source=MealItemSource.manual,
    ))
    await session.flush()


async def _add_workout(
    session: AsyncSession,
    user: User,
    day: date,
    *,
    burned: float | None = 300.0,
    minutes: int = 60,
    sets: int = 3,
    weight: float = 50.0,
    reps: int = 10,
) -> None:
    started = datetime(day.year, day.month, day.day, 10, 0, tzinfo=timezone.utc)
    finished = started + timedelta(minutes=minutes)
    ex = Exercise(
        name="Жим",
        user_id=None,
        muscle_group=MuscleGroup.chest,
        exercise_type=ExerciseType.weight_reps,
    )
    session.add(ex)
    await session.flush()

    workout = Workout(
        user_id=user.id,
        workout_date=day,
        started_at=started,
        finished_at=finished,
        estimated_calories_burned=burned,
    )
    session.add(workout)
    await session.flush()

    we = WorkoutExercise(workout_id=workout.id, exercise_id=ex.id, order=1)
    session.add(we)
    await session.flush()

    for i in range(1, sets + 1):
        session.add(WorkoutSet(
            workout_exercise_id=we.id,
            set_number=i,
            weight_kg=weight,
            reps=reps,
        ))
    await session.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_week_aggregates_meals_and_workouts(session: AsyncSession):
    user = await _make_user(session)
    today = date(2026, 4, 21)

    # 3 meals over 3 days, 2 workouts.
    await _add_meal(session, user, today, 600, protein=30)
    await _add_meal(session, user, today - timedelta(days=1), 1200, protein=50)
    await _add_meal(session, user, today - timedelta(days=2), 900, protein=40)
    await _add_workout(session, user, today, burned=400, minutes=45, sets=4)
    await _add_workout(session, user, today - timedelta(days=3), burned=250, minutes=30, sets=3)

    service = _make_service(session)
    stats = await service.get_period_summary(user.id, StatsPeriod.week, today=today)

    assert stats.days == 7
    assert stats.has_data is True
    assert stats.total_calories == pytest.approx(2700)
    assert stats.meals_count == 3
    assert stats.workouts_count == 2
    assert stats.sets_count == 7
    assert stats.burned_calories == pytest.approx(650)
    assert stats.training_minutes == 75
    assert stats.net_calories == pytest.approx(2050)
    assert stats.avg_eaten == pytest.approx(2700 / 7)
    assert stats.avg_burned == pytest.approx(650 / 7)


@pytest.mark.asyncio
async def test_all_time_with_only_meals(session: AsyncSession):
    """All-time must not crash if the user has only meals, no workouts."""
    user = await _make_user(session)
    today = date(2026, 4, 21)
    first = today - timedelta(days=9)  # 10 calendar days inclusive

    await _add_meal(session, user, first, 1000)
    await _add_meal(session, user, today, 1500)

    service = _make_service(session)
    stats = await service.get_period_summary(user.id, StatsPeriod.all_time, today=today)

    assert stats.start == first
    assert stats.days == 10
    assert stats.workouts_count == 0
    assert stats.burned_calories == 0.0
    assert stats.total_calories == pytest.approx(2500)
    assert stats.avg_burned == 0.0
    assert stats.has_data is True


@pytest.mark.asyncio
async def test_all_time_with_only_workouts(session: AsyncSession):
    """All-time must not crash if the user has only workouts, no meals."""
    user = await _make_user(session)
    today = date(2026, 4, 21)
    first = today - timedelta(days=4)

    await _add_workout(session, user, first, burned=200, minutes=40, sets=2)
    await _add_workout(session, user, today, burned=None, minutes=30, sets=1)  # null burn

    service = _make_service(session)
    stats = await service.get_period_summary(user.id, StatsPeriod.all_time, today=today)

    assert stats.start == first
    assert stats.days == 5
    assert stats.meals_count == 0
    assert stats.total_calories == 0.0
    assert stats.workouts_count == 2
    # NULL estimated_calories_burned treated as 0.
    assert stats.burned_calories == pytest.approx(200)
    assert stats.avg_eaten == 0.0


@pytest.mark.asyncio
async def test_empty_user_does_not_crash(session: AsyncSession):
    user = await _make_user(session)
    today = date(2026, 4, 21)
    service = _make_service(session)

    for period in StatsPeriod:
        stats = await service.get_period_summary(user.id, period, today=today)
        assert stats.has_data is False
        assert stats.days >= 1
        assert stats.total_calories == 0.0
        assert stats.burned_calories == 0.0
        assert stats.avg_eaten == 0.0
