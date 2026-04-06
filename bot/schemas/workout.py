"""Workout schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SetData(BaseModel):
    weight_kg: float | None = None
    reps: int | None = None
    duration_seconds: int | None = None
    is_warmup: bool = False


class ExerciseLogCreate(BaseModel):
    exercise_name: str
    sets: list[SetData]


class WorkoutCreate(BaseModel):
    name: str | None = None
    workout_date: date
    exercises: list[ExerciseLogCreate]


class WorkoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    workout_date: date


class WorkoutSummary(BaseModel):
    total_workouts: int = 0
    total_sets: int = 0
    total_volume_kg: float = 0.0
