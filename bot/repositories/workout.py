"""Workout repository."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.models.workout import Workout, WorkoutExercise, WorkoutSet

from .base import BaseRepository


class WorkoutRepository(BaseRepository[Workout]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workout)

    async def get_by_date(self, user_id: int, day: date) -> list[Workout]:
        stmt = (
            select(Workout)
            .where(Workout.user_id == user_id, Workout.workout_date == day)
            .options(
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets)
            )
            .order_by(Workout.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_workout(self, user_id: int, **kwargs) -> Workout:
        return await self.create(user_id=user_id, **kwargs)

    async def add_exercise(
        self,
        workout_id: UUID,
        exercise_id: UUID,
        order: int,
    ) -> WorkoutExercise:
        we = WorkoutExercise(
            workout_id=workout_id,
            exercise_id=exercise_id,
            order=order,
        )
        self.session.add(we)
        await self.session.flush()
        return we

    async def add_set(
        self,
        workout_exercise_id: UUID,
        set_number: int,
        **kwargs,
    ) -> WorkoutSet:
        ws = WorkoutSet(
            workout_exercise_id=workout_exercise_id,
            set_number=set_number,
            **kwargs,
        )
        self.session.add(ws)
        await self.session.flush()
        return ws

    async def count_user_workouts(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(Workout).where(Workout.user_id == user_id)
        return await self.session.scalar(stmt) or 0

    async def get_recent(
        self, user_id: int, limit: int = 5
    ) -> list[Workout]:
        stmt = (
            select(Workout)
            .where(Workout.user_id == user_id)
            .options(
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets)
            )
            .order_by(Workout.workout_date.desc(), Workout.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
