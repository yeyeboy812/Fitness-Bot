"""Agent bridge repository tests."""

from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import bot.handlers  # noqa: F401
from bot.keyboards.inline import main_menu_kb
from bot.models import Base
from bot.models.agent import ShortcutActionType
from bot.models.user import User
from bot.repositories.agent import UserShortcutRepository


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
    user = User(id=tg_id, first_name=f"user{tg_id}")
    session.add(user)
    await session.flush()
    return user


def _layout(markup) -> list[list[tuple[str, str]]]:
    return [[(button.text, button.callback_data) for button in row] for row in markup.inline_keyboard]


@pytest.mark.asyncio
async def test_shortcuts_list_personal_before_global(session: AsyncSession):
    user = await _make_user(session, 1001)
    repo = UserShortcutRepository(session)

    await repo.create_shortcut(
        user_id=None,
        label="Глобальная",
        action_type=ShortcutActionType.menu_action,
        payload={"action": "stats"},
        position=2,
    )
    personal = await repo.create_shortcut(
        user_id=user.id,
        label="Моя",
        action_type=ShortcutActionType.menu_action,
        payload={"action": "my_day"},
        position=10,
    )

    shortcuts = await repo.list_active_for_user(user.id)

    assert [item.label for item in shortcuts] == ["Моя", "Глобальная"]
    assert shortcuts[0].id == personal.id


def test_main_menu_appends_shortcut_rows_before_pro():
    shortcuts = [
        SimpleNamespace(id="aaa", label="Быстрый завтрак"),
        SimpleNamespace(id="bbb", label="Мой день"),
        SimpleNamespace(id="ccc", label="Статистика"),
    ]

    markup = main_menu_kb(user_id=123456789, shortcuts=shortcuts)
    layout = _layout(markup)

    assert layout[3] == [
        ("Быстрый завтрак", "shortcut:aaa"),
        ("Мой день", "shortcut:bbb"),
    ]
    assert layout[4] == [("Статистика", "shortcut:ccc")]
    assert layout[5] == [("⚙️ Настройки", "menu:settings")]
    assert layout[6] == [("⭐ Pro", "menu:pro")]
