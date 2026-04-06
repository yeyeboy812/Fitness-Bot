"""Exercise model."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class MuscleGroup(enum.Enum):
    chest = "chest"
    back = "back"
    shoulders = "shoulders"
    biceps = "biceps"
    triceps = "triceps"
    legs = "legs"
    abs = "abs"
    cardio = "cardio"
    other = "other"


class ExerciseType(enum.Enum):
    weight_reps = "weight_reps"
    bodyweight_reps = "bodyweight_reps"
    timed = "timed"
    distance = "distance"
    cardio_machine = "cardio_machine"


class Exercise(TimestampMixin, Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    muscle_group: Mapped[MuscleGroup] = mapped_column(
        SAEnum(MuscleGroup, name="muscle_group_enum"), nullable=False
    )
    exercise_type: Mapped[ExerciseType] = mapped_column(
        SAEnum(ExerciseType, name="exercise_type_enum"), nullable=False
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    def __repr__(self) -> str:
        return f"<Exercise {self.name!r} ({self.muscle_group.value})>"
