"""Follow-up actions after saving a food item."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.handlers.nutrition.add_meal import (
    on_add_another_product,
    on_choose_manual,
    on_meal_type,
    on_select_product,
)
from bot.models.base import Base
from bot.models.meal import MealItemSource
from bot.models.product import Product, ProductSource
from bot.models.user import User
from bot.repositories.meal import MealRepository
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


async def _make_user(session: AsyncSession) -> User:
    user = User(id=1001, first_name="Игорь")
    session.add(user)
    await session.flush()
    return user


def _callback(data: str = "") -> MagicMock:
    callback = MagicMock()
    callback.data = data
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def _saved_markup(callback: MagicMock):
    return callback.message.edit_text.await_args.kwargs["reply_markup"]


def _button_texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def _button_callbacks(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def _fill_food_state(
    state: FakeState,
    *,
    name: str,
    grams: float,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> None:
    state.data = {
        "selected_product_name": name,
        "amount_grams": grams,
        "cal": calories,
        "pro": protein,
        "fat": fat,
        "carb": carbs,
        "source": MealItemSource.search.value,
    }
    state.state = AppState.food_meal_type


@pytest.mark.asyncio
async def test_manual_food_prompt_mentions_dry_raw_weight():
    state = FakeState()
    callback = _callback("meal_method:manual")

    await on_choose_manual(callback, state)

    text = callback.message.edit_text.await_args.args[0]
    assert "Вес указывай в сухом/сыром виде" in text
    assert "80 г сухого риса до варки" in text
    assert state.state == AppState.food_manual_input


@pytest.mark.asyncio
async def test_catalog_amount_prompt_mentions_dry_raw_weight(session: AsyncSession):
    product = Product(
        name="Рис",
        source=ProductSource.system,
        calories_per_100g=350,
        protein_per_100g=7,
        fat_per_100g=1,
        carbs_per_100g=75,
    )
    session.add(product)
    await session.flush()

    state = FakeState()
    callback = _callback(f"product:{product.id}")

    await on_select_product(callback, state, session)

    text = callback.message.edit_text.await_args.args[0]
    assert "Вес указывай в сухом/сыром виде" in text
    assert state.state == AppState.food_amount


@pytest.mark.asyncio
async def test_saved_food_confirmation_has_add_another_button(session: AsyncSession):
    user = await _make_user(session)
    state = FakeState()
    _fill_food_state(
        state,
        name="Рис",
        grams=80,
        calories=280,
        protein=6.2,
        fat=0.8,
        carbs=62,
    )
    callback = _callback("meal_type:lunch")

    await on_meal_type(callback, state, session, user)

    text = callback.message.edit_text.await_args.args[0]
    assert "Добавлено:" in text
    assert "Рис — 80 г" in text
    assert "≈ 280 ккал / Б 6.2 / Ж 0.8 / У 62" in text
    assert "Что дальше?" in text

    markup = _saved_markup(callback)
    assert "➕ Добавить ещё продукт" in _button_texts(markup)
    assert "meal:add_another" in _button_callbacks(markup)


@pytest.mark.asyncio
async def test_add_another_moves_fsm_to_next_product_input():
    state = FakeState()
    state.data = {"selected_product_name": "Рис", "amount_grams": 80}
    callback = _callback("meal:add_another")

    await on_add_another_product(callback, state)

    assert state.data == {}
    assert state.state == AppState.food_search
    callback.message.edit_text.assert_awaited_once()
    assert "Введи название продукта для поиска" in callback.message.edit_text.await_args.args[0]


@pytest.mark.asyncio
async def test_can_add_two_products_in_a_row(session: AsyncSession):
    user = await _make_user(session)
    state = FakeState()

    _fill_food_state(
        state,
        name="Рис",
        grams=80,
        calories=280,
        protein=6,
        fat=1,
        carbs=62,
    )
    await on_meal_type(_callback("meal_type:lunch"), state, session, user)

    await on_add_another_product(_callback("meal:add_another"), state)
    assert state.state == AppState.food_search

    _fill_food_state(
        state,
        name="Курица",
        grams=150,
        calories=165,
        protein=33,
        fat=3,
        carbs=0,
    )
    await on_meal_type(_callback("meal_type:dinner"), state, session, user)

    repo = MealRepository(session)
    meals = await repo.get_by_date(user.id, date.today())
    items = [item for meal in meals for item in meal.items]
    assert [item.name_snapshot for item in items] == ["Рис", "Курица"]

    totals = await repo.get_daily_totals(user.id, date.today())
    assert totals["calories"] == 445
    assert totals["protein"] == 39
