"""Seed system products from CSV into the database."""

import asyncio
import csv
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import settings
from bot.models.base import create_db_engine, create_session_factory
from bot.models.product import Product, ProductAlias, ProductSource


CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "products_ru.csv"
ALIASES_CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "product_aliases.csv"


async def seed() -> None:
    engine = create_db_engine(settings.database_url)

    # Ensure tables exist (for SQLite dev mode)
    if "sqlite" in settings.database_url:
        from bot.models import Base  # noqa: F401
        from bot.models.base import create_tables
        await create_tables(engine)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        # Check if products already seeded
        from sqlalchemy import select, func
        count = await session.scalar(
            select(func.count()).where(Product.source == ProductSource.system)
        )
        if count and count > 0:
            print(f"System products already seeded ({count} found). Skipping.")
            await engine.dispose()
            return

        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            products = []
            for row in reader:
                product = Product(
                    name=row["name"],
                    calories_per_100g=float(row["calories_per_100g"]),
                    protein_per_100g=float(row["protein_per_100g"]),
                    fat_per_100g=float(row["fat_per_100g"]),
                    carbs_per_100g=float(row["carbs_per_100g"]),
                    source=ProductSource.system,
                    is_verified=True,
                    user_id=None,
                )
                products.append(product)

            session.add_all(products)
            await session.commit()
            print(f"Seeded {len(products)} system products.")

    await engine.dispose()


async def seed_aliases() -> None:
    if not ALIASES_CSV_PATH.exists():
        print("Aliases CSV not found, skipping.")
        return

    engine = create_db_engine(settings.database_url)

    if "sqlite" in settings.database_url:
        from bot.models import Base  # noqa: F401
        from bot.models.base import create_tables
        await create_tables(engine)

    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        from sqlalchemy import select, func
        count = await session.scalar(
            select(func.count()).select_from(ProductAlias)
        )
        if count and count > 0:
            print(f"Product aliases already seeded ({count} found). Skipping.")
            await engine.dispose()
            return

        with open(ALIASES_CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            aliases = []
            skipped = 0
            for row in reader:
                product = await session.scalar(
                    select(Product).where(
                        Product.name == row["product_name"],
                        Product.source == ProductSource.system,
                    )
                )
                if not product:
                    skipped += 1
                    continue
                aliases.append(
                    ProductAlias(product_id=product.id, alias=row["alias"])
                )

            session.add_all(aliases)
            await session.commit()
            print(f"Seeded {len(aliases)} product aliases (skipped {skipped}).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
    asyncio.run(seed_aliases())
