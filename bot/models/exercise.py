"""Exercise model."""

import enum
import uuid

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class MuscleGroup(enum.Enum):
    chest = "chest"
    back = "back"
    shoulders = "shoulders"
    arms = "arms"
    biceps = "biceps"
    triceps = "triceps"
    legs = "legs"
    abs = "abs"
    full_body = "full_body"
    cardio = "cardio"
    other = "other"


class ExerciseType(enum.Enum):
    weight_reps = "weight_reps"
    bodyweight_reps = "bodyweight_reps"
    timed = "timed"
    distance = "distance"
    cardio_machine = "cardio_machine"


# --- Workout section ("where it belongs in the top picker") -----------------
SECTION_GYM = "gym"
SECTION_HOME = "home"
SECTION_WARMUP = "warmup"
SECTION_COOLDOWN = "cooldown"

# --- Logging mode ----------------------------------------------------------
LOG_MODE_REPS = "reps"
LOG_MODE_TIME = "time"

# --- Load mode -------------------------------------------------------------
LOAD_EXTERNAL = "external_weight"              # barbell/dumbbell/machine — enter weight
LOAD_BW_OPT_EXTRA = "bodyweight_optional_extra"  # pullups/dips — bw, optional +weight
LOAD_NO_WEIGHT = "no_weight"                   # crunches, jumping jacks — bw, no prompt
LOAD_TIME_ONLY = "time_only"                   # plank, stretches — duration only


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

    # --- v2 catalog fields ---------------------------------------------------
    # Primary section this exercise belongs to ("gym" / "home" / "warmup" / "cooldown").
    # Gym exercises are still navigated by muscle_group; home/warmup/cooldown are
    # rendered as flat curated lists keyed on this column.
    section: Mapped[str] = mapped_column(
        String(16), nullable=False, default=SECTION_GYM, server_default=SECTION_GYM
    )
    # Whether logging flow collects reps or duration.
    log_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, default=LOG_MODE_REPS, server_default=LOG_MODE_REPS
    )
    # How load is sourced (see LOAD_* constants above).
    load_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default=LOAD_EXTERNAL, server_default=LOAD_EXTERNAL
    )

    def __repr__(self) -> str:
        return f"<Exercise {self.name!r} ({self.muscle_group.value})>"
