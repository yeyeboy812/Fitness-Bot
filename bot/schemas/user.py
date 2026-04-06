"""User-related Pydantic schemas."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


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


class UserNorms(BaseModel):
    calorie_norm: int
    protein_norm: int
    fat_norm: int
    carb_norm: int


class OnboardingData(BaseModel):
    first_name: str
    gender: Gender
    birth_year: int
    height_cm: int
    weight_kg: float
    goal: Goal
    activity_level: ActivityLevel
    daily_water_ml: int | None = None
    referral_source: str | None = None


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    gender: Gender | None = None
    birth_year: int | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    goal: Goal | None = None
    activity_level: ActivityLevel | None = None
    calorie_norm: int | None = None
    protein_norm: int | None = None
    fat_norm: int | None = None
    carb_norm: int | None = None
    onboarding_completed: bool = False
