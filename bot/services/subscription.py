"""Subscription tariffs and extension logic (Telegram Stars)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bot.models.user import SubscriptionTier, User


@dataclass(frozen=True)
class Tariff:
    key: str
    title: str
    description: str
    stars: int
    days: int


TARIFFS: dict[str, Tariff] = {
    "month": Tariff(
        key="month",
        title="Подписка на месяц",
        description="Pro-доступ на 30 дней",
        stars=2,
        days=30,
    ),
    "half_year": Tariff(
        key="half_year",
        title="Подписка на полгода",
        description="Pro-доступ на 180 дней",
        stars=10,
        days=180,
    ),
    "year": Tariff(
        key="year",
        title="Подписка на год",
        description="Pro-доступ на 365 дней",
        stars=16,
        days=365,
    ),
}


def get_tariff(key: str) -> Tariff | None:
    return TARIFFS.get(key)


def is_pro_active(user: User, now: datetime | None = None) -> bool:
    """User has active Pro tier."""
    if user.subscription_tier != SubscriptionTier.pro:
        return False
    if user.subscription_expires_at is None:
        return False
    current = now or datetime.now(timezone.utc).replace(tzinfo=None)
    return user.subscription_expires_at > current


def extend_from(user: User, tariff: Tariff, now: datetime | None = None) -> datetime:
    """Compute new expiry date after applying *tariff*.

    Stacks on top of the existing expiry if the user is still Pro.
    """
    current = now or datetime.now(timezone.utc).replace(tzinfo=None)
    base = (
        user.subscription_expires_at
        if is_pro_active(user, current)
        else current
    )
    return base + timedelta(days=tariff.days)
