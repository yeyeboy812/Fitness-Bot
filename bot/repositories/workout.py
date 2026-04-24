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

    async def get_daily_activity(
        self, user_id: int, day: date
    ) -> dict[str, float | int]:
        """Aggregate today's workout stats for the daily summary screen.

        Relies on ``get_by_date`` which already eagerly loads exercises + sets.
        Returns zeros when no workouts exist for the day.
        """
        workouts = await self.get_by_date(user_id, day)

        burned = 0.0
        workouts_count = len(workouts)
        exercises_count = 0
        sets_count = 0
        volume = 0.0
        minutes = 0

        for w in workouts:
            burned += w.estimated_calories_burned or 0.0
            if w.started_at and w.finished_at:
                delta = (w.finished_at - w.started_at).total_seconds() / 60.0
                if delta > 0:
                    minutes += int(round(delta))
            exercises_count += len(w.exercises)
            for we in w.exercises:
                for s in we.sets:
                    sets_count += 1
                    volume += (s.weight_kg or 0.0) * (s.reps or 0)

        return {
            "burned_calories": round(burned, 1),
            "workouts_count": workouts_count,
            "exercises_count": exercises_count,
            "sets_count": sets_count,
            "total_volume_kg": round(volume, 1),
            "training_minutes": minutes,
        }

    async def get_range_activity(
        self, user_id: int, start: date, end: date
    ) -> dict[str, float | int]:
        """Aggregate workouts across an inclusive date range.

        Relies on eager-loaded exercises + sets; OK for the stats period
        sizes we care about (a month of workouts is small in practice).
        Safe with NULL estimated_calories_burned / NULL weights / NULL reps.
        """
        stmt = (
            select(Workout)
            .where(
                Workout.user_id == user_id,
                Workout.workout_date >= start,
                Workout.workout_date <= end,
            )
            .options(
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets)
            )
        )
        result = await self.session.execute(stmt)
        workouts = list(result.scalars().all())

        burned = 0.0
        workouts_count = len(workouts)
        exercises_count = 0
        sets_count = 0
        volume = 0.0
        minutes = 0

        for w in workouts:
            burned += w.estimated_calories_burned or 0.0
            if w.started_at and w.finished_at:
                delta = (w.finished_at - w.started_at).total_seconds() / 60.0
                if delta > 0:
                    minutes += int(round(delta))
            exercises_count += len(w.exercises)
            for we in w.exercises:
                for s in we.sets:
                    sets_count += 1
                    volume += (s.weight_kg or 0.0) * (s.reps or 0)

        return {
            "burned_calories": round(burned, 1),
            "workouts_count": workouts_count,
            "exercises_count": exercises_count,
            "sets_count": sets_count,
            "total_volume_kg": round(volume, 1),
            "training_minutes": minutes,
        }

    async def get_first_workout_date(self, user_id: int) -> date | None:
        stmt = (
            select(func.min(Workout.workout_date))
            .where(Workout.user_id == user_id)
        )
        return await self.session.scalar(stmt)

    async def get_active_dates(self, user_id: int) -> set[date]:
        """Distinct dates on which the user logged at least one workout."""
        stmt = (
            select(Workout.workout_date)
            .where(Workout.user_id == user_id)
            .distinct()
        )
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

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
