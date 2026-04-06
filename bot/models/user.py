"""User model."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Float, SmallInteger, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .meal import Meal
    from .product import Product
    from .recipe import Recipe
    from .workout import Workout


class Gender(enum.Enum):
    male = "male"
    female = "female"


class Goal(enum.Enum):
    lose = "lose"
    maintain = "maintain"
    gain = "gain"


class ActivityLevel(enum.Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"


class SubscriptionTier(enum.Enum):
    free = "free"
    pro = "pro"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    # Telegram user_id — NOT auto-increment
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)

    gender: Mapped[Gender | None] = mapped_column(
        SAEnum(Gender, name="gender_enum"), nullable=True
    )
    birth_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    goal: Mapped[Goal | None] = mapped_column(
        SAEnum(Goal, name="goal_enum"), nullable=True
    )
    activity_level: Mapped[ActivityLevel | None] = mapped_column(
        SAEnum(ActivityLevel, name="activity_level_enum"), nullable=True
    )

    calorie_norm: Mapped[int | None] = mapped_column(nullable=True)
    protein_norm: Mapped[int | None] = mapped_column(nullable=True)
    fat_norm: Mapped[int | None] = mapped_column(nullable=True)
    carb_norm: Mapped[int | None] = mapped_column(nullable=True)

    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, name="subscription_tier_enum"),
        default=SubscriptionTier.free,
        server_default="free",
    )
    referral_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(32), default="Europe/Moscow", server_default="Europe/Moscow"
    )

    # --- relationships ---
    meals: Mapped[list["Meal"]] = relationship(back_populates="user", lazy="selectin")
    products: Mapped[list["Product"]] = relationship(back_populates="user", lazy="selectin")
    recipes: Mapped[list["Recipe"]] = relationship(back_populates="user", lazy="selectin")
    workouts: Mapped[list["Workout"]] = relationship(back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
