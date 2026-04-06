"""Product service — search, CRUD, hybrid system+user catalog."""

from uuid import UUID

from bot.models.product import Product, ProductSource
from bot.repositories.product import ProductRepository
from bot.schemas.product import NutritionPerAmount, ProductCreate


class ProductService:
    def __init__(self, repo: ProductRepository) -> None:
        self.repo = repo

    async def search(
        self, query: str, user_id: int, limit: int = 10
    ) -> list[Product]:
        return await self.repo.search(query, user_id=user_id, limit=limit)

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return await self.repo.get_by_id(product_id)

    async def create_user_product(
        self, user_id: int, data: ProductCreate
    ) -> Product:
        return await self.repo.create(
            user_id=user_id,
            name=data.name,
            brand=data.brand,
            calories_per_100g=data.calories_per_100g,
            protein_per_100g=data.protein_per_100g,
            fat_per_100g=data.fat_per_100g,
            carbs_per_100g=data.carbs_per_100g,
            source=ProductSource.user,
        )

    async def get_frequent(self, user_id: int, limit: int = 10) -> list[Product]:
        return await self.repo.get_frequent(user_id, limit=limit)

    async def increment_usage(self, product_id: UUID) -> None:
        await self.repo.increment_usage(product_id)

    @staticmethod
    def calc_nutrition(product: Product, amount_grams: float) -> NutritionPerAmount:
        ratio = amount_grams / 100.0
        return NutritionPerAmount(
            name=product.name,
            amount_grams=amount_grams,
            calories=round(product.calories_per_100g * ratio, 1),
            protein=round(product.protein_per_100g * ratio, 1),
            fat=round(product.fat_per_100g * ratio, 1),
            carbs=round(product.carbs_per_100g * ratio, 1),
        )
