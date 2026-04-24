"""Pro gating for AI meal entry points."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.handlers.nutrition.add_meal import on_choose_photo, on_choose_text, open_add_food
from bot.keyboards.inline import add_meal_method_kb
from bot.models.user import SubscriptionTier, User
from bot.states.app import AppState


def _user(*, pro: bool = False) -> User:
    user = User(id=1001, first_name="igor")
    if pro:
        user.subscription_tier = SubscriptionTier.pro
        user.subscription_expires_at = datetime(2099, 1, 1)
    return user


def _callback(data: str) -> MagicMock:
    callback = MagicMock()
    callback.data = data
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    return callback


def _button_texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


@pytest.mark.asyncio
async def test_open_add_food_marks_ai_methods_locked_for_free_user():
    message = MagicMock()
    message.answer = AsyncMock()
    state = AsyncMock()

    await open_add_food(message, state, _user())

    markup = message.answer.await_args.kwargs["reply_markup"]
    texts = _button_texts(markup)
    assert "🔒 Описать текстом" in texts
    assert "🔒 Отправить фото" in texts
    state.set_state.assert_awaited_once_with(AppState.adding_food)


def test_add_meal_method_keyboard_keeps_callback_data_when_locked():
    markup = add_meal_method_kb(ai_features_locked=True)
    layout = [
        (button.text, button.callback_data)
        for row in markup.inline_keyboard
        for button in row
    ]

    assert ("🔒 Описать текстом", "meal_method:text") in layout
    assert ("🔒 Отправить фото", "meal_method:photo") in layout


@pytest.mark.asyncio
async def test_free_user_cannot_choose_ai_text_entry():
    callback = _callback("meal_method:text")
    state = AsyncMock()

    await on_choose_text(callback, state, _user())

    callback.answer.assert_awaited_once()
    assert callback.answer.await_args.kwargs.get("show_alert") is True
    callback.message.edit_text.assert_not_awaited()
    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_active_pro_user_can_choose_ai_text_entry():
    callback = _callback("meal_method:text")
    state = AsyncMock()

    await on_choose_text(callback, state, _user(pro=True))

    callback.message.edit_text.assert_awaited_once()
    state.set_state.assert_awaited_once_with(AppState.food_text_description)
    callback.answer.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_free_user_cannot_choose_ai_photo_entry():
    callback = _callback("meal_method:photo")
    state = AsyncMock()

    await on_choose_photo(callback, state, _user())

    callback.answer.assert_awaited_once()
    assert callback.answer.await_args.kwargs.get("show_alert") is True
    callback.message.edit_text.assert_not_awaited()
    state.set_state.assert_not_awaited()
