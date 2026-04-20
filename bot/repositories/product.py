"""Product repository."""

from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.product import Product, ProductAlias

from .base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Product)

    async def search(
        self,
        query: str,
        user_id: int | None = None,
        limit: int = 10,
    ) -> list[Product]:
        """Search products by name or alias (ILIKE). Returns system + user's own."""
        pattern = f"%{query}%"
        stmt = (
            select(Product)
            .outerjoin(ProductAlias, Product.id == ProductAlias.product_id)
            .where(
                or_(Product.name.ilike(pattern), ProductAlias.alias.ilike(pattern)),
                or_(Product.user_id.is_(None), Product.user_id == user_id),
            )
            .group_by(Product.id)
            .order_by(Product.usage_count.desc(), Product.name)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_frequent(
        self, user_id: int, limit: int = 10
    ) -> list[Product]:
        """Most frequently used products (system + user's)."""
        stmt = (
            select(Product)
            .where(
                or_(Product.user_id.is_(None), Product.user_id == user_id),
                Product.usage_count > 0,
            )
            .order_by(Product.usage_count.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_usage(self, product_id: UUID) -> None:
        stmt = (
            update(Product)
            .where(Product.id == product_id)
            .values(usage_count=Product.usage_count + 1)
        )
        await self.session.execute(stmt)
