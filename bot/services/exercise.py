"""Exercise service — search and management."""

from bot.models.exercise import Exercise
from bot.repositories.exercise import ExerciseRepository


class ExerciseService:
    def __init__(self, repo: ExerciseRepository) -> None:
        self.repo = repo

    async def search(
        self, query: str, user_id: int, limit: int = 10
    ) -> list[Exercise]:
        return await self.repo.search(query, user_id=user_id, limit=limit)

    async def get_all_system(self, limit: int = 50) -> list[Exercise]:
        from sqlalchemy import select
        from bot.models.exercise import Exercise as ExModel

        stmt = (
            select(ExModel)
            .where(ExModel.is_system.is_(True))
            .order_by(ExModel.name)
            .limit(limit)
        )
        result = await self.repo.session.execute(stmt)
        return list(result.scalars().all())
