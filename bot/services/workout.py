"""Workout service — session management and logging."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from bot.models.exercise import ExerciseType, MuscleGroup
from bot.models.workout import Workout, WorkoutExercise, WorkoutSet
from bot.repositories.exercise import ExerciseRepository
from bot.repositories.workout import WorkoutRepository


DEFAULT_USER_WEIGHT_KG = 70.0
BASE_MET = 3.5
HIGH_MET = 5.0
HIGH_SETS_THRESHOLD = 20
HIGH_VOLUME_KG_THRESHOLD = 8000.0
LB_TO_KG = 0.45359237

# Quick-set input grammar:
#   <weight> [unit] x|х <reps>
# Unit is optional (no unit = kg). lbs/lb/фунт*/ф map to pounds; everything
# else (including missing) maps to kg. Decimals accept both '.' and ','.
_WEIGHT_REPS_PATTERN = re.compile(
    r"^\s*(?P<weight>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>kg|кг|lbs|lb|фунт\w*|ф)?\s*"
    r"[xх]\s*(?P<reps>\d+)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WeightRepsInput:
    weight_kg: float
    reps: int
    original_weight_value: float
    original_weight_unit: str  # "kg" | "lb"


def _classify_unit(raw_unit: str) -> str:
    """Map a parsed unit token to canonical 'kg' | 'lb'. Empty → 'kg'."""
    token = (raw_unit or "").lower()
    if token in ("lb", "lbs"):
        return "lb"
    if token == "ф" or token.startswith("фунт"):
        return "lb"
    return "kg"


def parse_weight_reps_input(text: str) -> WeightRepsInput | None:
    """Parse '<weight>[unit] x <reps>' into kg-canonical WeightRepsInput.

    Returns None for unrecognized input or non-positive weight/reps. When the
    user types lb/фунт, ``weight_kg`` is converted; ``original_weight_value``
    and ``original_weight_unit`` preserve the typed form for confirmation UX.
    """
    match = _WEIGHT_REPS_PATTERN.fullmatch(text or "")
    if match is None:
        return None

    weight_value = float(match.group("weight").replace(",", "."))
    reps = int(match.group("reps"))
    if weight_value <= 0 or reps <= 0:
        return None

    unit = _classify_unit(match.group("unit") or "")
    weight_kg = weight_value * LB_TO_KG if unit == "lb" else weight_value
    return WeightRepsInput(
        weight_kg=weight_kg,
        reps=reps,
        original_weight_value=weight_value,
        original_weight_unit=unit,
    )


def estimate_calories_burned(
    *,
    duration_minutes: int,
    user_weight_kg: float | None,
    total_sets: int,
    total_volume_kg: float,
) -> float:
    """MVP MET-based estimate for strength training.

    calories = MET * weight_kg * hours.
    High-intensity MET kicks in when session volume or set count crosses
    a threshold. Returns a non-negative float rounded to 1 decimal.
    """
    duration_minutes = max(1, int(duration_minutes))
    weight = user_weight_kg if user_weight_kg and user_weight_kg > 0 else DEFAULT_USER_WEIGHT_KG
    met = (
        HIGH_MET
        if total_sets >= HIGH_SETS_THRESHOLD or total_volume_kg >= HIGH_VOLUME_KG_THRESHOLD
        else BASE_MET
    )
    calories = met * weight * (duration_minutes / 60.0)
    return round(max(0.0, calories), 1)


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
        **kwargs,
    ) -> Workout:
        return await self.workout_repo.create_workout(
            user_id=user_id,
            workout_date=workout_date,
            name=name,
            **kwargs,
        )

    async def attach_exercise(
        self,
        workout_id: UUID,
        exercise_id: UUID,
        order: int,
    ) -> WorkoutExercise:
        """Attach an already-resolved Exercise row to a workout."""
        return await self.workout_repo.add_exercise(
            workout_id=workout_id,
            exercise_id=exercise_id,
            order=order,
        )

    async def add_exercise_to_workout(
        self,
        workout_id: UUID,
        user_id: int,
        exercise_name: str,
        order: int,
    ) -> WorkoutExercise:
        """Legacy by-name attach (kept for backwards-compat)."""
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
        *,
        load_mode: str | None = None,
        user_body_weight_snapshot: float | None = None,
        extra_weight_kg: float | None = None,
        effective_weight_kg: float | None = None,
    ) -> WorkoutSet:
        return await self.workout_repo.add_set(
            workout_exercise_id=workout_exercise_id,
            set_number=set_number,
            weight_kg=weight_kg,
            reps=reps,
            duration_seconds=duration_seconds,
            is_warmup=is_warmup,
            load_mode=load_mode,
            user_body_weight_snapshot=user_body_weight_snapshot,
            extra_weight_kg=extra_weight_kg,
            effective_weight_kg=effective_weight_kg,
        )

    async def delete_set(self, workout_exercise_id: UUID, workout_set_id: UUID) -> None:
        await self.workout_repo.delete_set(workout_exercise_id, workout_set_id)

    async def finish_workout(
        self,
        workout_id: UUID,
        *,
        finished_at: datetime,
        estimated_calories_burned: float,
    ) -> Workout | None:
        return await self.workout_repo.finish_workout(
            workout_id,
            finished_at=finished_at,
            estimated_calories_burned=estimated_calories_burned,
        )

    async def get_today_workouts(
        self, user_id: int, day: date
    ) -> list[Workout]:
        return await self.workout_repo.get_by_date(user_id, day)

    async def count_workouts(self, user_id: int) -> int:
        return await self.workout_repo.count_user_workouts(user_id)
