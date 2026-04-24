"""Catalog query + pagination: global-before-personal, isolation, wrap."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models.base import Base
from bot.models.exercise import ExerciseType, MuscleGroup
from bot.models.user import Gender, Goal, User
from bot.repositories.exercise import ExerciseRepository


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _make_user(session: AsyncSession, tg_id: int) -> User:
    user = User(
        id=tg_id,
        first_name=f"user{tg_id}",
        gender=Gender.male,
        goal=Goal.maintain,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_list_by_muscle_group_global_before_personal(session: AsyncSession):
    user_a = await _make_user(session, 100)
    user_b = await _make_user(session, 200)
    repo = ExerciseRepository(session)

    # 2 global chest exercises.
    await repo.create(
        name="Жим лёжа",
        user_id=None,
        muscle_group=MuscleGroup.chest,
        exercise_type=ExerciseType.weight_reps,
        is_system=True,
    )
    await repo.create(
        name="Отжимания",
        user_id=None,
        muscle_group=MuscleGroup.chest,
        exercise_type=ExerciseType.bodyweight_reps,
        is_system=True,
    )
    # Personal exercise for user_a.
    await repo.create_personal(
        name="Мой жим",
        user_id=user_a.id,
        muscle_group=MuscleGroup.chest,
    )
    # Personal exercise for user_b — must NOT leak to user_a.
    await repo.create_personal(
        name="Секрет B",
        user_id=user_b.id,
        muscle_group=MuscleGroup.chest,
    )

    items = await repo.list_by_muscle_group(
        MuscleGroup.chest, user_id=user_a.id, limit=10, offset=0
    )
    names = [e.name for e in items]
    assert names == ["Жим лёжа", "Отжимания", "Мой жим"]

    total_a = await repo.count_by_muscle_group(MuscleGroup.chest, user_id=user_a.id)
    assert total_a == 3

    total_b = await repo.count_by_muscle_group(MuscleGroup.chest, user_id=user_b.id)
    assert total_b == 3  # 2 globals + 1 personal


@pytest.mark.asyncio
async def test_pagination_and_empty(session: AsyncSession):
    user = await _make_user(session, 300)
    repo = ExerciseRepository(session)

    for i in range(1, 14):  # 13 exercises → pages of 6: 6/6/1
        await repo.create(
            name=f"Ex{i:02d}",
            user_id=None,
            muscle_group=MuscleGroup.legs,
            exercise_type=ExerciseType.weight_reps,
            is_system=True,
        )

    page0 = await repo.list_by_muscle_group(
        MuscleGroup.legs, user_id=user.id, limit=6, offset=0
    )
    page1 = await repo.list_by_muscle_group(
        MuscleGroup.legs, user_id=user.id, limit=6, offset=6
    )
    page2 = await repo.list_by_muscle_group(
        MuscleGroup.legs, user_id=user.id, limit=6, offset=12
    )

    assert len(page0) == 6
    assert len(page1) == 6
    assert len(page2) == 1
    # No overlap between pages.
    all_ids = [e.id for e in page0 + page1 + page2]
    assert len(set(all_ids)) == len(all_ids)

    # Empty muscle group returns [].
    empty = await repo.list_by_muscle_group(
        MuscleGroup.abs, user_id=user.id, limit=6, offset=0
    )
    assert empty == []
    assert await repo.count_by_muscle_group(MuscleGroup.abs, user.id) == 0


@pytest.mark.asyncio
async def test_arms_includes_legacy_biceps_triceps(session: AsyncSession):
    """UI 'Руки' (arms) must surface older rows saved as biceps/triceps."""
    user = await _make_user(session, 400)
    repo = ExerciseRepository(session)

    await repo.create(
        name="Подъём штанги",
        user_id=None,
        muscle_group=MuscleGroup.biceps,
        exercise_type=ExerciseType.weight_reps,
        is_system=True,
    )
    await repo.create(
        name="Французский жим",
        user_id=None,
        muscle_group=MuscleGroup.triceps,
        exercise_type=ExerciseType.weight_reps,
        is_system=True,
    )
    await repo.create(
        name="Молотки",
        user_id=None,
        muscle_group=MuscleGroup.arms,
        exercise_type=ExerciseType.weight_reps,
        is_system=True,
    )

    total = await repo.count_by_muscle_group(MuscleGroup.arms, user.id)
    assert total == 3

    items = await repo.list_by_muscle_group(
        MuscleGroup.arms, user_id=user.id, limit=10, offset=0
    )
    names = {e.name for e in items}
    assert names == {"Подъём штанги", "Французский жим", "Молотки"}


@pytest.mark.asyncio
async def test_custom_personal_visible_only_to_owner(session: AsyncSession):
    """Personal exercise created by user A stays in A's catalog, not B's."""
    user_a = await _make_user(session, 500)
    user_b = await _make_user(session, 600)
    repo = ExerciseRepository(session)

    ex, created = await repo.get_or_create_user_exercise(
        name="Моё секретное упражнение",
        user_id=user_a.id,
        muscle_group=MuscleGroup.back,
    )
    assert created is True
    assert ex.user_id == user_a.id
    assert ex.muscle_group == MuscleGroup.back

    a_items = await repo.list_by_muscle_group(
        MuscleGroup.back, user_id=user_a.id, limit=10, offset=0
    )
    assert any(e.name == "Моё секретное упражнение" for e in a_items)

    b_items = await repo.list_by_muscle_group(
        MuscleGroup.back, user_id=user_b.id, limit=10, offset=0
    )
    assert all(e.name != "Моё секретное упражнение" for e in b_items)

    # Not leaked into a different muscle group either.
    a_legs = await repo.list_by_muscle_group(
        MuscleGroup.legs, user_id=user_a.id, limit=10, offset=0
    )
    assert all(e.name != "Моё секретное упражнение" for e in a_legs)
