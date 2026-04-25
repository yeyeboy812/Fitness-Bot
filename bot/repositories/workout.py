"""Workout repository."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
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
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
                selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
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

    async def delete_set(
        self,
        workout_exercise_id: UUID,
        workout_set_id: UUID,
    ) -> None:
        stmt = delete(WorkoutSet).where(
            WorkoutSet.id == workout_set_id,
            WorkoutSet.workout_exercise_id == workout_exercise_id,
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def finish_workout(
        self,
        workout_id: UUID,
        *,
        finished_at: datetime,
        estimated_calories_burned: float,
    ) -> Workout | None:
        workout = await self.get_by_id(workout_id)
        if workout is None:
            return None
        workout.finished_at = finished_at
        workout.estimated_calories_burned = estimated_calories_burned
        await self.session.flush()
        return workout

    async def get_daily_activity(
        self, user_id: int, day: date
    ) -> dict[str, Any]:
        """Aggregate today's workout stats for the daily summary screen.

        Relies on ``get_by_date`` which already eagerly loads exercises + sets.
        Returns zeros when no workouts exist for the day.
        """
        workouts = await self.get_by_date(user_id, day)
        return self._aggregate_workouts(workouts, include_items=True)

    async def get_range_activity(
        self, user_id: int, start: date, end: date
    ) -> dict[str, Any]:
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
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
                selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
            )
        )
        result = await self.session.execute(stmt)
        workouts = list(result.scalars().all())
        return self._aggregate_workouts(workouts, include_items=False)

    def _aggregate_workouts(
        self,
        workouts: list[Workout],
        *,
        include_items: bool,
    ) -> dict[str, Any]:
        burned = 0.0
        workouts_count = 0
        exercise_ids: set[UUID] = set()
        sets_count = 0
        reps_count = 0
        duration_seconds = 0
        volume = 0.0
        minutes = 0
        items_by_exercise: dict[UUID, dict[str, Any]] = {}

        for w in workouts:
            workout_has_sets = False
            if w.started_at and w.finished_at:
                delta = (w.finished_at - w.started_at).total_seconds() / 60.0
                if delta > 0:
                    minutes += int(round(delta))
            for we in w.exercises:
                if not we.sets:
                    continue
                workout_has_sets = True
                exercise_ids.add(we.exercise_id)
                if include_items:
                    exercise = we.exercise
                    item = items_by_exercise.setdefault(
                        we.exercise_id,
                        {
                            "exercise_name": exercise.name if exercise else "Упражнение",
                            "sets_count": 0,
                            "reps_total": 0,
                            "reps_per_set": None,
                            "duration_seconds": 0,
                            "total_volume_kg": 0.0,
                            "weight_kg": None,
                            "load_mode": None,
                            "log_mode": exercise.log_mode if exercise else None,
                            "_weights": [],
                            "_reps": [],
                            "_load_modes": set(),
                        },
                    )
                for s in we.sets:
                    sets_count += 1
                    weight = (
                        s.effective_weight_kg
                        if s.effective_weight_kg is not None
                        else s.weight_kg
                    )
                    if s.reps:
                        reps = int(s.reps)
                        reps_count += reps
                        if include_items:
                            item["reps_total"] += reps
                            item["_reps"].append(reps)
                    if s.duration_seconds:
                        seconds = int(s.duration_seconds)
                        duration_seconds += seconds
                        if include_items:
                            item["duration_seconds"] += seconds
                    if weight is not None and s.reps:
                        set_volume = float(weight) * int(s.reps)
                        volume += set_volume
                        if include_items:
                            item["total_volume_kg"] += set_volume
                            item["_weights"].append(round(float(weight), 3))
                    if include_items:
                        item["sets_count"] += 1
                        if s.load_mode:
                            item["_load_modes"].add(s.load_mode)
            if workout_has_sets:
                workouts_count += 1
                burned += w.estimated_calories_burned or 0.0

        items: list[dict[str, Any]] = []
        if include_items:
            for item in items_by_exercise.values():
                weights = item.pop("_weights")
                reps = item.pop("_reps")
                load_modes = item.pop("_load_modes")
                if weights and all(weight == weights[0] for weight in weights):
                    item["weight_kg"] = weights[0]
                if (
                    reps
                    and len(reps) == item["sets_count"]
                    and all(rep == reps[0] for rep in reps)
                ):
                    item["reps_per_set"] = reps[0]
                if len(load_modes) == 1:
                    item["load_mode"] = next(iter(load_modes))
                item["total_volume_kg"] = round(float(item["total_volume_kg"]), 1)
                items.append(item)

        return {
            "burned_calories": round(burned, 1),
            "workouts_count": workouts_count,
            "exercises_count": len(exercise_ids),
            "sets_count": sets_count,
            "reps_count": reps_count,
            "duration_seconds": duration_seconds,
            "total_volume_kg": round(volume, 1),
            "training_minutes": minutes,
            "items": items,
        }

    async def get_first_workout_date(self, user_id: int) -> date | None:
        stmt = (
            select(func.min(Workout.workout_date))
            .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(Workout.user_id == user_id)
        )
        return await self.session.scalar(stmt)

    async def get_active_dates(self, user_id: int) -> set[date]:
        """Distinct dates on which the user logged at least one workout."""
        stmt = (
            select(Workout.workout_date)
            .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(Workout.user_id == user_id)
            .distinct()
        )
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

    async def count_user_workouts(self, user_id: int) -> int:
        stmt = (
            select(func.count(func.distinct(Workout.id)))
            .select_from(Workout)
            .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(Workout.user_id == user_id)
        )
        return await self.session.scalar(stmt) or 0

    async def get_recent(
        self, user_id: int, limit: int = 5
    ) -> list[Workout]:
        stmt = (
            select(Workout)
            .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(Workout.user_id == user_id)
            .options(
                selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
                selectinload(Workout.exercises).selectinload(WorkoutExercise.exercise),
            )
            .distinct()
            .order_by(Workout.workout_date.desc(), Workout.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
