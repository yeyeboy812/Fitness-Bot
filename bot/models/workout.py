"""Workout, WorkoutExercise, and WorkoutSet models."""

import uuid
from datetime import date as date_type
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, SmallInteger, String, Uuid
from sqlalchemy import ForeignKey

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class Workout(TimestampMixin, Base):
    __tablename__ = "workouts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    workout_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_calories_burned: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # --- relationships ---
    user: Mapped["User"] = relationship(back_populates="workouts")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan",
        order_by="WorkoutExercise.order",
    )

    def __repr__(self) -> str:
        return f"<Workout {self.name!r} {self.workout_date}>"


class WorkoutExercise(TimestampMixin, Base):
    __tablename__ = "workout_exercises"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    workout_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercises.id"), nullable=False
    )
    order: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # --- relationships ---
    workout: Mapped["Workout"] = relationship(back_populates="exercises")
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout_exercise", cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )


class WorkoutSet(TimestampMixin, Base):
    __tablename__ = "workout_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    workout_exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False
    )
    set_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_warmup: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    # --- v2 load-tracking fields --------------------------------------------
    # Capture the load model so analytics can tell "90kg bench press" from
    # "90kg effective on pullups (75kg user + 15kg belt)".
    load_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_body_weight_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- relationships ---
    workout_exercise: Mapped["WorkoutExercise"] = relationship(back_populates="sets")
