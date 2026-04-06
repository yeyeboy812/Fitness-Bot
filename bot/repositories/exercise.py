"""Exercise repository."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.exercise import Exercise, ExerciseType, MuscleGroup

from .base import BaseRepository


class ExerciseRepository(BaseRepository[Exercise]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Exercise)

    async def search(
        self,
        query: str,
        user_id: int | None = None,
        limit: int = 10,
    ) -> list[Exercise]:
        pattern = f"%{query}%"
        stmt = (
            select(Exercise)
            .where(
                Exercise.name.ilike(pattern),
                or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_user_exercise(
        self,
        name: str,
        user_id: int,
        muscle_group: MuscleGroup = MuscleGroup.other,
        exercise_type: ExerciseType = ExerciseType.weight_reps,
    ) -> tuple[Exercise, bool]:
        """Get existing or create a new user exercise."""
        stmt = select(Exercise).where(
            Exercise.name.ilike(name),
            or_(Exercise.user_id.is_(None), Exercise.user_id == user_id),
        )
        result = await self.session.execute(stmt)
        exercise = result.scalar_one_or_none()
        if exercise:
            return exercise, False

        exercise = await self.create(
            name=name,
            user_id=user_id,
            muscle_group=muscle_group,
            exercise_type=exercise_type,
        )
        return exercise, True
