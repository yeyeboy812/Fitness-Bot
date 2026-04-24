from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.handlers import profile, settings
from bot.models.user import ActivityLevel, Gender, Goal, User
from bot.services.user import UserService
from bot.states.app import AppState


def _user() -> User:
    user = User(id=1001, first_name="Ivan")
    user.onboarding_completed = True
    user.gender = Gender.male
    user.birth_year = 1995
    user.height_cm = 180
    user.weight_kg = 75.0
    user.goal = Goal.maintain
    user.activity_level = ActivityLevel.moderate
    user.calorie_norm = 2500
    user.protein_norm = 135
    user.fat_norm = 75
    user.carb_norm = 320
    return user


def _message() -> MagicMock:
    message = MagicMock()
    message.text = ""
    message.answer = AsyncMock()
    message.edit_text = AsyncMock()
    return message


def _callback(data: str = "") -> MagicMock:
    callback = MagicMock()
    callback.data = data
    callback.answer = AsyncMock()
    callback.message = _message()
    return callback


class FakeRepo:
    def __init__(self, user: User) -> None:
        self.user = user

    async def get_by_id(self, user_id):
        assert user_id == self.user.id
        return self.user

    async def update_profile(self, user_id, **kwargs):
        assert user_id == self.user.id
        for key, value in kwargs.items():
            setattr(self.user, key, value)
        return self.user


@pytest.mark.asyncio
async def test_existing_user_opens_profile_and_sees_data():
    message = _message()
    state = AsyncMock()
    state.get_data.return_value = {}
    user = _user()

    await profile.open_profile(message, state, user)

    text = message.answer.await_args.args[0]
    assert "Профиль" in text
    assert "Ivan" in text
    assert "Мужской" in text
    assert "1995" in text
    assert "180 см" in text
    assert "75 кг" in text
    assert "2500" in text
    state.set_state.assert_awaited_once_with(AppState.viewing_profile)


@pytest.mark.asyncio
async def test_settings_screen_opens_and_links_to_profile():
    message = _message()
    state = AsyncMock()

    await settings.open_settings(message, state)

    text = message.answer.await_args.args[0]
    markup = message.answer.await_args.kwargs["reply_markup"]
    buttons = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert "Настройки" in text
    assert "settings:profile" in buttons
    state.set_state.assert_awaited_once_with(AppState.viewing_settings)


@pytest.mark.asyncio
async def test_settings_profile_callback_opens_personalization():
    callback = _callback("settings:profile")
    state = AsyncMock()
    state.get_data.return_value = {}
    user = _user()

    await settings.on_settings_profile(callback, state, user)

    callback.message.edit_text.assert_awaited_once()
    text = callback.message.edit_text.await_args.args[0]
    assert "Профиль" in text
    assert "Ivan" in text


@pytest.mark.asyncio
async def test_profile_back_returns_to_settings():
    callback = _callback("profile:back_settings")
    state = AsyncMock()

    await profile.on_profile_back_settings(callback, state)

    callback.message.edit_text.assert_awaited_once()
    text = callback.message.edit_text.await_args.args[0]
    assert "Настройки" in text
    state.set_state.assert_awaited_once_with(AppState.viewing_settings)


@pytest.mark.asyncio
async def test_settings_back_returns_to_main_menu(monkeypatch):
    render_header = AsyncMock(return_value="menu")
    build_markup = AsyncMock(return_value=MagicMock())

    import bot.handlers.main_menu as main_menu

    monkeypatch.setattr(main_menu, "_render_menu_header", render_header)
    monkeypatch.setattr(main_menu, "_build_menu_markup", build_markup)

    state = AsyncMock()
    user = _user()
    callback = _callback("settings:back_menu")

    await settings.on_settings_menu(callback, state, MagicMock(), user)

    state.clear.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    assert user.weight_kg == 75.0


@pytest.mark.asyncio
async def test_weight_change_is_not_saved_before_confirmation(monkeypatch):
    calls = []

    class FakeUserService:
        def __init__(self, repo):
            self.repo = repo

        async def update_profile_field(self, user_id, field, value):
            calls.append((user_id, field, value))
            user = _user()
            user.weight_kg = value
            user.calorie_norm = 2520
            return user

    monkeypatch.setattr(profile, "UserService", FakeUserService)
    state = AsyncMock()
    state.get_data.return_value = {"pending_profile_field": "weight_kg"}
    message = _message()
    message.text = "76"
    user = _user()

    await profile.on_profile_value_input(message, state, user)

    assert calls == []
    state.update_data.assert_awaited_with(
        pending_profile_field="weight_kg",
        pending_profile_value=76.0,
    )
    state.set_state.assert_awaited_with(AppState.profile_confirm)

    callback = _callback("profile:save")
    state.get_data.return_value = {
        "pending_profile_field": "weight_kg",
        "pending_profile_value": 76.0,
    }
    await profile.on_profile_save(callback, state, MagicMock(), user)

    assert calls == [(1001, "weight_kg", 76.0)]


@pytest.mark.asyncio
async def test_name_change_is_saved_only_after_confirmation(monkeypatch):
    calls = []

    class FakeUserService:
        def __init__(self, repo):
            self.repo = repo

        async def update_profile_field(self, user_id, field, value):
            calls.append((user_id, field, value))
            user = _user()
            user.first_name = value
            return user

    monkeypatch.setattr(profile, "UserService", FakeUserService)
    state = AsyncMock()
    state.get_data.return_value = {"pending_profile_field": "first_name"}
    message = _message()
    message.text = "  Petr   Petrov  "
    user = _user()

    await profile.on_profile_value_input(message, state, user)

    assert calls == []
    state.update_data.assert_awaited_with(
        pending_profile_field="first_name",
        pending_profile_value="Petr Petrov",
    )

    callback = _callback("profile:save")
    state.get_data.return_value = {
        "pending_profile_field": "first_name",
        "pending_profile_value": "Petr Petrov",
    }
    await profile.on_profile_save(callback, state, MagicMock(), user)

    assert calls == [(1001, "first_name", "Petr Petrov")]


@pytest.mark.asyncio
async def test_cancel_name_change_does_not_mutate_user():
    state = AsyncMock()
    state.get_data.return_value = {
        "pending_profile_field": "first_name",
        "pending_profile_value": "Petr",
    }
    user = _user()

    await profile.on_profile_cancel(_callback("profile:cancel"), state, user)

    assert user.first_name == "Ivan"
    state.set_state.assert_awaited_with(AppState.viewing_profile)


@pytest.mark.asyncio
async def test_weight_change_recalculates_norms_in_user_service():
    user = _user()

    updated = await UserService(FakeRepo(user)).update_profile_field(user.id, "weight_kg", 80.0)

    assert updated.weight_kg == 80.0
    assert updated.calorie_norm != 2500
    assert updated.protein_norm == 144


@pytest.mark.asyncio
async def test_gender_change_recalculates_norms_in_user_service():
    user = _user()

    updated = await UserService(FakeRepo(user)).update_profile_field(user.id, "gender", "female")

    assert updated.gender == "female"
    assert updated.calorie_norm != 2500


@pytest.mark.asyncio
async def test_birth_year_change_recalculates_norms_in_user_service():
    user = _user()

    updated = await UserService(FakeRepo(user)).update_profile_field(user.id, "birth_year", 1985)

    assert updated.birth_year == 1985
    assert updated.calorie_norm != 2500


@pytest.mark.asyncio
async def test_invalid_birth_year_is_not_confirmed():
    state = AsyncMock()
    state.get_data.return_value = {"pending_profile_field": "birth_year"}
    message = _message()
    message.text = "1900"

    await profile.on_profile_value_input(message, state, _user())

    message.answer.assert_awaited_once()
    state.update_data.assert_not_awaited()
    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_name_is_not_confirmed():
    state = AsyncMock()
    state.get_data.return_value = {"pending_profile_field": "first_name"}
    message = _message()
    message.text = " " * 10

    await profile.on_profile_value_input(message, state, _user())

    message.answer.assert_awaited_once()
    state.update_data.assert_not_awaited()
    state.set_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_profile_menu_clears_only_fsm(monkeypatch):
    render_header = AsyncMock(return_value="menu")
    build_markup = AsyncMock(return_value=MagicMock())

    import bot.handlers.main_menu as main_menu

    monkeypatch.setattr(main_menu, "_render_menu_header", render_header)
    monkeypatch.setattr(main_menu, "_build_menu_markup", build_markup)

    state = AsyncMock()
    user = _user()
    callback = _callback("profile:menu")

    await profile.on_profile_menu(callback, state, MagicMock(), user)

    state.clear.assert_awaited_once()
    assert user.weight_kg == 75.0
    assert user.calorie_norm == 2500
