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

# Fat g/kg of body weight. Standard is the MVP default; min/max bound the
# safe range so the recommendation never drifts outside healthy ratios when
# carbs become tight at low total calories.
FAT_G_PER_KG_MIN = 0.8
FAT_G_PER_KG_STANDARD = 0.9
FAT_G_PER_KG_MAX = 1.0


def _round_to_nearest_10(value: float) -> int:
    """Round to the nearest 10 g; never return a negative number."""
    return max(0, int(round(value / 10.0)) * 10)


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

    Protein: 1.8–2.2 g/kg depending on goal (higher during deficit to
             preserve muscle mass).
    Fat:     0.9 g/kg of body weight (MVP default), hard-capped at
             1.0 g/kg so the recommendation never gets disproportionately
             high. Independent of total calories.
    Carbs:   remaining calories / 4 (after protein and fat). Floored at 0
             when the deficit is too aggressive — never negative.

    All macro grams are rounded to the nearest 10 g to avoid pseudo-precision.
    """
    protein_per_kg = {
        Goal.lose: 2.2,
        Goal.maintain: 1.8,
        Goal.gain: 2.0,
    }

    protein_raw = weight_kg * protein_per_kg[goal]
    fat_raw = min(weight_kg * FAT_G_PER_KG_STANDARD, weight_kg * FAT_G_PER_KG_MAX)

    protein_g = _round_to_nearest_10(protein_raw)
    fat_g = _round_to_nearest_10(fat_raw)

    remaining = calories - protein_g * 4 - fat_g * 9
    carbs_g = _round_to_nearest_10(remaining / 4) if remaining > 0 else 0

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
