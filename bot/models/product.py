"""Product and ProductAlias models."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, Index, Integer, String, Uuid
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User


class ProductSource(enum.Enum):
    system = "system"
    user = "user"
    ai = "ai"
    api = "api"


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_user_name", "user_id", "name"),
        # NOTE: for fuzzy search, run once in DB:
        #   CREATE EXTENSION IF NOT EXISTS pg_trgm;
        #   CREATE INDEX ix_products_name_trgm ON products USING gin (name gin_trgm_ops);
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)

    calories_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    protein_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_per_100g: Mapped[float] = mapped_column(Float, nullable=False)

    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    source: Mapped[ProductSource] = mapped_column(
        SAEnum(ProductSource, name="product_source_enum"),
        default=ProductSource.user,
        server_default="user",
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )

    # --- relationships ---
    user: Mapped["User | None"] = relationship(back_populates="products")
    aliases: Mapped[list["ProductAlias"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product {self.name!r} ({self.calories_per_100g} kcal/100g)>"


class ProductAlias(TimestampMixin, Base):
    __tablename__ = "product_aliases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(String(256), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="aliases")
