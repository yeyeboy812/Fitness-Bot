"""Meal and MealItem models."""

import enum
import uuid
from datetime import date as date_type
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, Index, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class MealType(enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealItemSource(enum.Enum):
    search = "search"
    manual = "manual"
    text_parse = "text_parse"
    photo = "photo"
    recipe = "recipe"


class Meal(TimestampMixin, Base):
    __tablename__ = "meals"
    __table_args__ = (
        Index("ix_meals_user_date", "user_id", "meal_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    meal_type: Mapped[MealType | None] = mapped_column(
        SAEnum(MealType, name="meal_type_enum"), nullable=True
    )
    meal_date: Mapped[date_type] = mapped_column(
        Date, nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # --- relationships ---
    user: Mapped["User"] = relationship(back_populates="meals")
    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Meal {self.meal_type} {self.meal_date}>"


class MealItem(TimestampMixin, Base):
    __tablename__ = "meal_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    meal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id"), nullable=True
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recipes.id"), nullable=True
    )

    name_snapshot: Mapped[str] = mapped_column(String(256), nullable=False)
    amount_grams: Mapped[float] = mapped_column(Float, nullable=False)

    # Denormalized КБЖУ — calculated at entry time
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)

    source: Mapped[MealItemSource] = mapped_column(
        SAEnum(MealItemSource, name="meal_item_source_enum"),
        default=MealItemSource.manual,
    )

    # --- relationships ---
    meal: Mapped["Meal"] = relationship(back_populates="items")
