"""User repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User

from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_or_create(
        self,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
    ) -> tuple[User, bool]:
        """Return (user, created). created=True if new user was inserted."""
        user = await self.get_by_id(telegram_id)
        if user:
            return user, False
        user = await self.create(
            id=telegram_id,
            first_name=first_name,
            username=username,
        )
        return user, True

    async def update_profile(self, user_id: int, **kwargs) -> User:
        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        for key, value in kwargs.items():
            setattr(user, key, value)
        await self.session.flush()
        return user
