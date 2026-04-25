"""Workout activity aggregation for «Мой день»."""

from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models.base import Base
from bot.models.exercise import (
    LOAD_EXTERNAL,
    LOAD_NO_WEIGHT,
    LOAD_TIME_ONLY,
    LOG_MODE_REPS,
    LOG_MODE_TIME,
    SECTION_COOLDOWN,
    SECTION_GYM,
    Exercise,
    ExerciseType,
    MuscleGroup,
)
from bot.models.workout import Workout, WorkoutExercise, WorkoutSet
from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.nutrition import NutritionService
from bot.utils.formatting import format_daily_summary


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _add_exercise(
    session: AsyncSession,
    *,
    name: str,
    muscle_group: MuscleGroup = MuscleGroup.shoulders,
    exercise_type: ExerciseType = ExerciseType.weight_reps,
    section: str = SECTION_GYM,
    log_mode: str = LOG_MODE_REPS,
    load_mode: str = LOAD_EXTERNAL,
) -> Exercise:
    exercise = Exercise(
        name=name,
        user_id=None,
        muscle_group=muscle_group,
        exercise_type=exercise_type,
        section=section,
        log_mode=log_mode,
        load_mode=load_mode,
    )
    session.add(exercise)
    await session.flush()
    return exercise


async def _add_workout_with_sets(
    session: AsyncSession,
    *,
    user_id: int,
    day: date,
    exercise: Exercise,
    sets: list[dict],
) -> None:
    workout = Workout(
        user_id=user_id,
        workout_date=day,
        started_at=datetime(day.year, day.month, day.day, 10, 0, tzinfo=timezone.utc),
    )
    session.add(workout)
    await session.flush()
    workout_exercise = WorkoutExercise(
        workout_id=workout.id,
        exercise_id=exercise.id,
        order=1,
    )
    session.add(workout_exercise)
    await session.flush()
    for index, set_data in enumerate(sets, 1):
        session.add(
            WorkoutSet(
                workout_exercise_id=workout_exercise.id,
                set_number=index,
                **set_data,
            )
        )
    await session.flush()


async def _summary_text(session: AsyncSession, user_id: int, day: date) -> str:
    service = NutritionService(MealRepository(session), WorkoutRepository(session))
    summary = await service.get_daily_summary(user_id, day)
    return format_daily_summary(summary, [])


@pytest.mark.asyncio
async def test_saved_external_sets_are_shown_in_my_day(session: AsyncSession):
    day = date(2026, 4, 25)
    exercise = await _add_exercise(session, name="Махи гантелями перед собой")
    await _add_workout_with_sets(
        session,
        user_id=1001,
        day=day,
        exercise=exercise,
        sets=[
            {"weight_kg": 5.0, "reps": 12, "load_mode": LOAD_EXTERNAL},
            {"weight_kg": 5.0, "reps": 12, "load_mode": LOAD_EXTERNAL},
            {"weight_kg": 5.0, "reps": 12, "load_mode": LOAD_EXTERNAL},
            {"weight_kg": 5.0, "reps": 12, "load_mode": LOAD_EXTERNAL},
        ],
    )

    text = await _summary_text(session, 1001, day)

    assert "🏋️ <b>Тренировка сегодня</b>" in text
    assert "• упражнений: 1" in text
    assert "• подходов: 4" in text
    assert "• повторений: 48" in text
    assert "• объём: 240 кг" in text
    assert "Махи гантелями перед собой — 5 кг × 12 × 4" in text


@pytest.mark.asyncio
async def test_multiple_exercises_are_aggregated_for_day(session: AsyncSession):
    day = date(2026, 4, 25)
    press = await _add_exercise(session, name="Жим")
    raise_side = await _add_exercise(session, name="Махи в стороны")
    await _add_workout_with_sets(
        session,
        user_id=1001,
        day=day,
        exercise=press,
        sets=[{"weight_kg": 40.0, "reps": 10, "load_mode": LOAD_EXTERNAL}],
    )
    await _add_workout_with_sets(
        session,
        user_id=1001,
        day=day,
        exercise=raise_side,
        sets=[
            {"weight_kg": 8.0, "reps": 12, "load_mode": LOAD_EXTERNAL},
            {"weight_kg": 8.0, "reps": 12, "load_mode": LOAD_EXTERNAL},
        ],
    )

    text = await _summary_text(session, 1001, day)

    assert "• упражнений: 2" in text
    assert "• подходов: 3" in text
    assert "Жим — 40 кг × 10 × 1" in text
    assert "Махи в стороны — 8 кг × 12 × 2" in text


@pytest.mark.asyncio
async def test_no_weight_exercise_is_displayed_without_weight(session: AsyncSession):
    day = date(2026, 4, 25)
    exercise = await _add_exercise(
        session,
        name="Скручивания",
        muscle_group=MuscleGroup.abs,
        exercise_type=ExerciseType.bodyweight_reps,
        load_mode=LOAD_NO_WEIGHT,
    )
    await _add_workout_with_sets(
        session,
        user_id=1001,
        day=day,
        exercise=exercise,
        sets=[
            {"reps": 20, "load_mode": LOAD_NO_WEIGHT},
            {"reps": 20, "load_mode": LOAD_NO_WEIGHT},
        ],
    )

    text = await _summary_text(session, 1001, day)

    assert "Скручивания — 20 × 2" in text
    assert "Скручивания — 0 кг" not in text


@pytest.mark.asyncio
async def test_time_based_exercise_is_displayed_by_duration(session: AsyncSession):
    day = date(2026, 4, 25)
    exercise = await _add_exercise(
        session,
        name="Планка",
        muscle_group=MuscleGroup.abs,
        exercise_type=ExerciseType.timed,
        section=SECTION_COOLDOWN,
        log_mode=LOG_MODE_TIME,
        load_mode=LOAD_TIME_ONLY,
    )
    await _add_workout_with_sets(
        session,
        user_id=1001,
        day=day,
        exercise=exercise,
        sets=[
            {"duration_seconds": 60, "load_mode": LOAD_TIME_ONLY},
            {"duration_seconds": 90, "load_mode": LOAD_TIME_ONLY},
        ],
    )

    text = await _summary_text(session, 1001, day)

    assert "• длительность: 2:30" in text
    assert "Планка — 2:30" in text


@pytest.mark.asyncio
async def test_empty_workout_session_is_not_counted(session: AsyncSession):
    day = date(2026, 4, 25)
    session.add(
        Workout(
            user_id=1001,
            workout_date=day,
            started_at=datetime(day.year, day.month, day.day, 10, 0, tzinfo=timezone.utc),
        )
    )
    await session.flush()

    text = await _summary_text(session, 1001, day)

    assert "🏋️ Тренировка сегодня: пока нет записанных подходов." in text
