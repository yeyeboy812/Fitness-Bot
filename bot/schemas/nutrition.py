"""Nutrition / meal schemas."""

from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealItemSource(str, Enum):
    search = "search"
    manual = "manual"
    text_parse = "text_parse"
    photo = "photo"
    recipe = "recipe"


class MealItemCreate(BaseModel):
    product_id: UUID | None = None
    recipe_id: UUID | None = None
    name_snapshot: str
    amount_grams: float
    calories: float
    protein: float
    fat: float
    carbs: float
    source: MealItemSource = MealItemSource.manual


class MealCreate(BaseModel):
    meal_type: MealType | None = None
    meal_date: date
    items: list[MealItemCreate]
    note: str | None = None


class WorkoutActivityItem(BaseModel):
    exercise_name: str
    sets_count: int = 0
    reps_total: int = 0
    reps_per_set: int | None = None
    duration_seconds: int = 0
    total_volume_kg: float = 0.0
    weight_kg: float | None = None
    load_mode: str | None = None
    log_mode: str | None = None


class DailySummary(BaseModel):
    date: date
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_fat: float = 0.0
    total_carbs: float = 0.0
    calorie_norm: int | None = None
    protein_norm: int | None = None
    fat_norm: int | None = None
    carb_norm: int | None = None
    # Activity (today)
    burned_calories: float = 0.0
    net_calories: float = 0.0
    workouts_count: int = 0
    exercises_count: int = 0
    sets_count: int = 0
    reps_count: int = 0
    duration_seconds: int = 0
    total_volume_kg: float = 0.0
    training_minutes: int = 0
    workout_items: list[WorkoutActivityItem] = Field(default_factory=list)
