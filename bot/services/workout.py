"""Workout service — session management and logging."""

from datetime import date
from uuid import UUID

from bot.models.exercise import ExerciseType, MuscleGroup
from bot.models.workout import Workout, WorkoutExercise, WorkoutSet
from bot.repositories.exercise import ExerciseRepository
from bot.repositories.workout import WorkoutRepository


class WorkoutService:
    def __init__(
        self,
        workout_repo: WorkoutRepository,
        exercise_repo: ExerciseRepository,
    ) -> None:
        self.workout_repo = workout_repo
        self.exercise_repo = exercise_repo

    async def start_workout(
        self,
        user_id: int,
        workout_date: date,
        name: str | None = None,
    ) -> Workout:
        return await self.workout_repo.create_workout(
            user_id=user_id,
            workout_date=workout_date,
            name=name,
        )

    async def add_exercise_to_workout(
        self,
        workout_id: UUID,
        user_id: int,
        exercise_name: str,
        order: int,
    ) -> WorkoutExercise:
        exercise, _ = await self.exercise_repo.get_or_create_user_exercise(
            name=exercise_name,
            user_id=user_id,
            muscle_group=MuscleGroup.other,
            exercise_type=ExerciseType.weight_reps,
        )
        return await self.workout_repo.add_exercise(
            workout_id=workout_id,
            exercise_id=exercise.id,
            order=order,
        )

    async def log_set(
        self,
        workout_exercise_id: UUID,
        set_number: int,
        weight_kg: float | None = None,
        reps: int | None = None,
        duration_seconds: int | None = None,
        is_warmup: bool = False,
    ) -> WorkoutSet:
        return await self.workout_repo.add_set(
            workout_exercise_id=workout_exercise_id,
            set_number=set_number,
            weight_kg=weight_kg,
            reps=reps,
            duration_seconds=duration_seconds,
            is_warmup=is_warmup,
        )

    async def get_today_workouts(
        self, user_id: int, day: date
    ) -> list[Workout]:
        return await self.workout_repo.get_by_date(user_id, day)

    async def count_workouts(self, user_id: int) -> int:
        return await self.workout_repo.count_user_workouts(user_id)
