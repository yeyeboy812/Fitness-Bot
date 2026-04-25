"""Daily nutrition progress in the main menu header."""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.handlers.main_menu import _render_menu_header
from bot.models.base import Base
from bot.models.meal import Meal, MealItem, MealItemSource, MealType
from bot.models.user import Gender, Goal, User


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _make_user(
    session: AsyncSession,
    *,
    with_norms: bool,
) -> User:
    user = User(
        id=1001,
        first_name="Игорь",
        gender=Gender.male,
        goal=Goal.maintain,
    )
    if with_norms:
        user.calorie_norm = 2000
        user.protein_norm = 120
        user.fat_norm = 70
        user.carb_norm = 250
    session.add(user)
    await session.flush()
    return user


async def _add_meal(
    session: AsyncSession,
    user: User,
    day: date,
    *,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> None:
    meal = Meal(user_id=user.id, meal_type=MealType.lunch, meal_date=day)
    session.add(meal)
    await session.flush()
    session.add(
        MealItem(
            meal_id=meal.id,
            name_snapshot="Рис",
            amount_grams=100,
            calories=calories,
            protein=protein,
            fat=fat,
            carbs=carbs,
            source=MealItemSource.search,
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_main_menu_shows_daily_calories_and_macros_when_norms_exist(
    session: AsyncSession,
):
    today = date.today()
    user = await _make_user(session, with_norms=True)
    await _add_meal(
        session,
        user,
        today,
        calories=543.2,
        protein=30.7,
        fat=12.2,
        carbs=82.4,
    )

    text = await _render_menu_header(user, session, today)

    assert "Сегодня:" in text
    assert "🔥 543 / 2000 ккал" in text
    assert "🥩 Б: 31 / 120 г" in text
    assert "🥑 Ж: 12 / 70 г" in text
    assert "🍚 У: 82 / 250 г" in text


@pytest.mark.asyncio
async def test_main_menu_does_not_crash_without_norms(session: AsyncSession):
    today = date.today()
    user = await _make_user(session, with_norms=False)

    text = await _render_menu_header(user, session, today)

    assert "Сегодня пока нет данных по БЖУ." in text
