"""Product schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    name: str
    brand: str | None = None
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    brand: str | None = None
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    is_verified: bool
    usage_count: int


class NutritionPerAmount(BaseModel):
    """Calculated nutrition for a specific amount of a product."""
    name: str
    amount_grams: float
    calories: float
    protein: float
    fat: float
    carbs: float
