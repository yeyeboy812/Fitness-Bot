"""Subscription entitlements and feature access decisions."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timezone

from bot.models.user import SubscriptionTier, User


class Feature(str, enum.Enum):
    """Business features that can be gated by subscription tier."""

    stats_all_time = "stats_all_time"
    ai_text_meal = "ai_text_meal"
    ai_photo_meal = "ai_photo_meal"


@dataclass(frozen=True)
class EntitlementDecision:
    allowed: bool
    reason: str | None = None


class EntitlementService:
    """Resolve feature access for a user.

    Keep handlers thin: they ask this service whether a feature is available
    and decide how to render Telegram UI around that answer.
    """

    _PRO_FEATURES = {
        Feature.stats_all_time,
        Feature.ai_text_meal,
        Feature.ai_photo_meal,
    }

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime.now(timezone.utc).replace(tzinfo=None)

    def is_pro_active(self, user: User) -> bool:
        if user.subscription_tier != SubscriptionTier.pro:
            return False
        if user.subscription_expires_at is None:
            return False
        return user.subscription_expires_at > self.now

    def check(self, user: User, feature: Feature) -> EntitlementDecision:
        if feature not in self._PRO_FEATURES:
            return EntitlementDecision(allowed=True)
        if self.is_pro_active(user):
            return EntitlementDecision(allowed=True)
        return EntitlementDecision(
            allowed=False,
            reason="Эта функция доступна в Pro.",
        )
