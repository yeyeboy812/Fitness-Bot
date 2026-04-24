"""Monitoring commands for the context bot."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.access import is_admin
from bot.models.user import User
from bot.repositories.agent import AgentCommandRepository, AgentEventRepository, UserShortcutRepository

router = Router(name="context_monitoring")


@router.message(Command("status"))
async def cmd_status(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    if not is_admin(user.id):
        await message.answer("Этот бот доступен только администратору.")
        return

    command_repo = AgentCommandRepository(session)
    event_repo = AgentEventRepository(session)
    shortcut_repo = UserShortcutRepository(session)

    pending_commands = await command_repo.list_pending(limit=10)
    recent_events = await event_repo.list_recent(limit=5)
    shortcuts = await shortcut_repo.list_active_for_user(user.id)

    lines = [
        "<b>Bridge status</b>",
        "",
        f"Pending commands: <b>{len(pending_commands)}</b>",
        f"Active shortcuts for you: <b>{len(shortcuts)}</b>",
        "",
        "Recent events:",
    ]

    if recent_events:
        for event in recent_events:
            lines.append(
                f"- {event.event_type.value} | user={event.user_id} | source={event.source_bot}"
            )
    else:
        lines.append("- no events yet")

    await message.answer("\n".join(lines))
