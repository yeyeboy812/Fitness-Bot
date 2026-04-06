"""Recipe schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecipeIngredientCreate(BaseModel):
    product_id: UUID
    product_name: str
    amount_grams: float
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float


class RecipeCreate(BaseModel):
    name: str
    servings: int = 1
    ingredients: list[RecipeIngredientCreate]


class RecipeIngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    amount_grams: float


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    total_weight_grams: float
    servings: int
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    usage_count: int
