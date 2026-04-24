"""Agent command execution tests."""

from __future__ import annotations

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models import Base
from bot.models.agent import AgentCommandStatus, AgentCommandType, AgentEventType, ShortcutActionType
from bot.models.user import User
from bot.repositories.agent import AgentCommandRepository, AgentEventRepository, UserShortcutRepository
from bot.repositories.product import ProductRepository
from bot.services.agent_commands import AgentCommandExecutor


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


@pytest.mark.asyncio
async def test_execute_create_product_command(session: AsyncSession):
    user = await _make_user(session, 3001)
    repo = AgentCommandRepository(session)
    command = await repo.enqueue(
        AgentCommandType.create_product,
        user_id=user.id,
        payload={
            "name": "Творог 5%",
            "calories_per_100g": 121,
            "protein_per_100g": 17,
            "fat_per_100g": 5,
            "carbs_per_100g": 3,
        },
    )

    completed = await AgentCommandExecutor(session, command_repo=repo).execute(command)

    product = await ProductRepository(session).get_by_id(UUID(completed.result_payload["id"]))
    events = await AgentEventRepository(session).list_recent(
        user_id=user.id,
        event_type=AgentEventType.command_executed,
        limit=10,
    )

    assert completed.status == AgentCommandStatus.completed
    assert product is not None
    assert product.name == "Творог 5%"
    assert len(events) == 1


@pytest.mark.asyncio
async def test_execute_create_shortcut_command(session: AsyncSession):
    user = await _make_user(session, 3002)
    repo = AgentCommandRepository(session)
    command = await repo.enqueue(
        AgentCommandType.create_shortcut,
        user_id=user.id,
        payload={
            "label": "Мой день",
            "action_type": ShortcutActionType.menu_action.value,
            "payload": {"action": "my_day"},
            "position": 1,
        },
    )

    completed = await AgentCommandExecutor(session, command_repo=repo).execute(command)
    shortcuts = await UserShortcutRepository(session).list_active_for_user(user.id)

    assert completed.status == AgentCommandStatus.completed
    assert [item.label for item in shortcuts] == ["Мой день"]
    assert shortcuts[0].payload == {"action": "my_day"}
