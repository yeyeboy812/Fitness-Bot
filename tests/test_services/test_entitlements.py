"""Entitlement service tests."""

from datetime import datetime, timedelta

from bot.models.user import SubscriptionTier, User
from bot.services.entitlements import EntitlementService, Feature


NOW = datetime(2026, 4, 24, 12, 0, 0)


def _user(
    *,
    tier: SubscriptionTier = SubscriptionTier.free,
    expires_delta: timedelta | None = None,
) -> User:
    return User(
        id=1001,
        first_name="igor",
        subscription_tier=tier,
        subscription_expires_at=NOW + expires_delta if expires_delta else None,
    )


def test_free_user_cannot_use_pro_feature():
    decision = EntitlementService(now=NOW).check(
        _user(),
        Feature.stats_all_time,
    )

    assert decision.allowed is False
    assert decision.reason


def test_active_pro_user_can_use_pro_feature():
    decision = EntitlementService(now=NOW).check(
        _user(tier=SubscriptionTier.pro, expires_delta=timedelta(days=1)),
        Feature.stats_all_time,
    )

    assert decision.allowed is True


def test_expired_pro_user_is_treated_as_free():
    decision = EntitlementService(now=NOW).check(
        _user(tier=SubscriptionTier.pro, expires_delta=timedelta(seconds=-1)),
        Feature.stats_all_time,
    )

    assert decision.allowed is False
