"""Nutrition / meal schemas."""

from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


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
