"""Pure functions for calorie and macronutrient calculations.

Uses Mifflin-St Jeor equation — the most widely validated formula
for estimating Basal Metabolic Rate (BMR).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Gender(str, Enum):
    male = "male"
    female = "female"


class Goal(str, Enum):
    lose = "lose"
    maintain = "maintain"
    gain = "gain"


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


ACTIVITY_MULTIPLIERS: dict[ActivityLevel, float] = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.light: 1.375,
    ActivityLevel.moderate: 1.55,
    ActivityLevel.active: 1.725,
    ActivityLevel.very_active: 1.9,
}

GOAL_ADJUSTMENTS: dict[Goal, float] = {
    Goal.lose: -0.15,
    Goal.maintain: 0.0,
    Goal.gain: 0.15,
}


@dataclass(frozen=True)
class MacroSplit:
    calories: int
    protein_g: int
    fat_g: int
    carbs_g: int


def calculate_bmr(gender: Gender, weight_kg: float, height_cm: int, age: int) -> float:
    """Mifflin-St Jeor equation for BMR.

    Male:   10 * weight + 6.25 * height - 5 * age + 5
    Female: 10 * weight + 6.25 * height - 5 * age - 161
    """
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender == Gender.male:
        return base + 5
    return base - 161


def calculate_tdee(bmr: float, activity_level: ActivityLevel) -> float:
    """Total Daily Energy Expenditure = BMR * activity multiplier."""
    return bmr * ACTIVITY_MULTIPLIERS[activity_level]


def adjust_for_goal(tdee: float, goal: Goal) -> int:
    """Apply caloric deficit or surplus based on goal."""
    adjustment = GOAL_ADJUSTMENTS[goal]
    return round(tdee * (1 + adjustment))


def calculate_macros(calories: int, goal: Goal, weight_kg: float) -> MacroSplit:
    """Calculate macronutrient split.

    Protein: 1.6 g/kg (maintain) to 2.2 g/kg (lose) — higher protein
             during deficit preserves muscle mass.
    Fat:     25-30% of total calories.
    Carbs:   remainder.
    """
    protein_per_kg = {
        Goal.lose: 2.2,
        Goal.maintain: 1.8,
        Goal.gain: 2.0,
    }

    protein_g = round(weight_kg * protein_per_kg[goal])
    fat_g = round(calories * 0.27 / 9)  # 27% of cals, 9 cal/g
    carbs_g = round((calories - protein_g * 4 - fat_g * 9) / 4)

    # Safety: carbs should not be negative
    if carbs_g < 50:
        carbs_g = 50
        fat_g = round((calories - protein_g * 4 - carbs_g * 4) / 9)

    return MacroSplit(
        calories=calories,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
    )


def calculate_norms(
    gender: Gender,
    weight_kg: float,
    height_cm: int,
    age: int,
    activity_level: ActivityLevel,
    goal: Goal,
) -> MacroSplit:
    """Full pipeline: BMR → TDEE → goal adjustment → macro split."""
    bmr = calculate_bmr(gender, weight_kg, height_cm, age)
    tdee = calculate_tdee(bmr, activity_level)
    target_calories = adjust_for_goal(tdee, goal)
    return calculate_macros(target_calories, goal, weight_kg)
