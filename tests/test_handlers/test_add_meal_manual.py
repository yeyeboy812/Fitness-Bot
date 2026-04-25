"""Manual food entry handler — fixes the infinite-loading callback bug."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.handlers.nutrition.add_meal import (
    back_to_adding_food,
    on_choose_manual,
    on_manual_input,
)
from bot.keyboards.inline import add_meal_method_kb
from bot.keyboards.nutrition import manual_prompt_kb
from bot.models.user import User
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


def _user() -> User:
    return User(id=1001, first_name="igor")


def _callback() -> MagicMock:
    callback = MagicMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def test_keyboard_callback_data_matches_handler_filter():
    """Button callback_data must match the handler's F.data filter."""
    markup = add_meal_method_kb()
    manual_buttons = [
        button
        for row in markup.inline_keyboard
        for button in row
        if "Ввести вручную" in button.text
    ]
    assert len(manual_buttons) == 1
    assert manual_buttons[0].callback_data == "meal_method:manual"


def test_manual_keyboard_has_back_and_cancel():
    markup = manual_prompt_kb()
    callback_data = {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
    }
    assert "back:adding_food" in callback_data
    assert "cancel" in callback_data


@pytest.mark.asyncio
async def test_on_choose_manual_clears_spinner_and_enters_state():
    state = FakeState()
    callback = _callback()

    await on_choose_manual(callback, state)

    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    args, kwargs = callback.message.edit_text.await_args
    assert "Введи продукт и вес" in args[0]
    assert "Вес указывай в сухом/сыром виде" in args[0]
    assert kwargs["reply_markup"] is manual_prompt_kb.__wrapped__() if hasattr(
        manual_prompt_kb, "__wrapped__"
    ) else kwargs["reply_markup"] is not None
    assert state.state == AppState.food_manual_input


@pytest.mark.asyncio
async def test_on_choose_manual_callback_answer_runs_before_edit():
    """Spinner must clear even if edit_text fails — answer() is awaited first."""
    state = FakeState()
    callback = _callback()
    callback.message.edit_text = AsyncMock(side_effect=RuntimeError("telegram down"))

    await on_choose_manual(callback, state)

    # Even if edit_text blew up, callback.answer was awaited (no infinite loading)
    callback.answer.assert_awaited_once()
    # Fallback message rendered to the user.
    callback.message.answer.assert_awaited_once()
    fallback_text = callback.message.answer.await_args.args[0]
    assert "Не получилось открыть ручной ввод" in fallback_text


@pytest.mark.asyncio
async def test_on_manual_input_stub_returns_user_to_method_picker():
    state = FakeState()
    state.state = AppState.food_manual_input
    message = MagicMock()
    message.text = "гречка 150 г"
    message.answer = AsyncMock()

    await on_manual_input(message, state, _user())

    assert state.data["raw_manual_text"] == "гречка 150 г"
    assert state.state == AppState.adding_food
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_back_button_returns_to_method_picker():
    state = FakeState()
    state.state = AppState.food_manual_input
    callback = _callback()

    await back_to_adding_food(callback, state, _user())

    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    assert "Как добавить еду" in callback.message.edit_text.await_args.args[0]
    assert state.state == AppState.adding_food
