from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.filters.menu import MainMenuFilter
from bot.handlers import common
from bot.models.user import ActivityLevel, Gender, Goal, User
from bot.services.user import is_profile_complete
from bot.states.app import MAIN_MENU_LABEL
from bot.states.onboarding import OnboardingSG


def _user(*, completed: bool = False, filled: bool = False) -> User:
    user = User(id=1001, first_name="Ivan")
    user.onboarding_completed = completed
    if filled:
        user.gender = Gender.male
        user.birth_year = 1995
        user.height_cm = 180
        user.weight_kg = 75.0
        user.goal = Goal.maintain
        user.activity_level = ActivityLevel.moderate
        user.calorie_norm = 2400
        user.protein_norm = 140
        user.fat_norm = 80
        user.carb_norm = 260
    return user


def _message() -> MagicMock:
    message = MagicMock()
    message.answer = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_start_launches_onboarding_for_new_incomplete_user(monkeypatch):
    show_main_menu = AsyncMock()
    monkeypatch.setattr(common, "_show_main_menu", show_main_menu)
    state = AsyncMock()
    message = _message()

    await common.cmd_start(message, _user(), state, MagicMock())

    state.clear.assert_awaited_once()
    state.set_state.assert_awaited_once_with(OnboardingSG.name)
    show_main_menu.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_shows_menu_for_completed_user(monkeypatch):
    show_main_menu = AsyncMock()
    monkeypatch.setattr(common, "_show_main_menu", show_main_menu)
    state = AsyncMock()
    message = _message()
    session = MagicMock()
    user = _user(completed=True)

    await common.cmd_start(message, user, state, session)

    state.clear.assert_awaited_once()
    state.set_state.assert_not_awaited()
    show_main_menu.assert_awaited_once_with(message, session, user)


@pytest.mark.asyncio
async def test_start_shows_menu_for_filled_legacy_profile_without_flag(monkeypatch):
    show_main_menu = AsyncMock()
    monkeypatch.setattr(common, "_show_main_menu", show_main_menu)
    state = AsyncMock()
    message = _message()
    session = MagicMock()
    user = _user(completed=False, filled=True)

    await common.cmd_start(message, user, state, session)

    state.clear.assert_awaited_once()
    state.set_state.assert_not_awaited()
    show_main_menu.assert_awaited_once_with(message, session, user)


@pytest.mark.asyncio
async def test_main_menu_filter_allows_filled_legacy_profile_without_flag():
    message = MagicMock()
    message.text = MAIN_MENU_LABEL

    assert await MainMenuFilter()(message, _user(completed=False, filled=True)) is True


def test_profile_complete_accepts_completed_flag_without_touching_profile_fields():
    user = _user(completed=True, filled=False)

    assert is_profile_complete(user) is True
