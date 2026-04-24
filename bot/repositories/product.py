"""Product repository."""

from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.product import Product

from .base import BaseRepository


def normalize_product_text(text: str) -> str:
    """Canonical form for name/brand/alias matching.

    Lowercase, ё→е, whitespace squashed. Used for SQLite-safe case-insensitive
    compare (SQLite LOWER() is ASCII-only and breaks Cyrillic).
    """
    return " ".join(text.strip().lower().replace("ё", "е").split())


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Product)

    async def search(
        self,
        query: str,
        user_id: int | None = None,
        limit: int = 10,
    ) -> list[Product]:
        """Search visible products by name / brand / alias.

        Python-side substring match on normalized text — works with Cyrillic
        on SQLite where LOWER() / ILIKE fail. Ranks verified system rows
        first, then by usage_count.
        """
        norm_query = normalize_product_text(query)
        if not norm_query:
            return []

        stmt = (
            select(Product)
            .options(selectinload(Product.aliases))
            .where(or_(Product.user_id.is_(None), Product.user_id == user_id))
        )
        result = await self.session.execute(stmt)
        candidates = list(result.scalars().unique().all())

        matches: list[tuple[int, Product]] = []
        for p in candidates:
            hit = _match_score(p, norm_query)
            if hit is not None:
                matches.append((hit, p))

        # Lower score = better. Tiebreak: verified desc, usage_count desc, name.
        matches.sort(
            key=lambda t: (
                t[0],
                0 if t[1].is_verified else 1,
                -t[1].usage_count,
                t[1].name.lower(),
            )
        )
        return [p for _, p in matches[:limit]]

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


def _match_score(product: Product, norm_query: str) -> int | None:
    """Return a rank (lower = stronger match) or None if no hit.

    Scoring (ascending priority):
      0 — exact name / brand / alias
      1 — prefix match on name / brand / alias
      2 — substring in name
      3 — substring in brand or alias
    """
    name_n = normalize_product_text(product.name)
    brand_n = normalize_product_text(product.brand or "")
    alias_norms = [
        a.normalized_alias or normalize_product_text(a.alias)
        for a in product.aliases
    ]

    exact_fields = [name_n, brand_n, *alias_norms]
    if any(f == norm_query for f in exact_fields if f):
        return 0

    prefix_fields = [name_n, brand_n, *alias_norms]
    if any(f.startswith(norm_query) for f in prefix_fields if f):
        return 1

    if norm_query in name_n:
        return 2

    if (brand_n and norm_query in brand_n) or any(
        norm_query in a for a in alias_norms
    ):
        return 3

    return None
