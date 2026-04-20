"""Tests for MVP calorie-burn estimator."""

from bot.services.workout import (
    BASE_MET,
    DEFAULT_USER_WEIGHT_KG,
    HIGH_MET,
    estimate_calories_burned,
)


class TestBurnedEstimator:
    def test_base_met_light_session(self):
        # 60 min * 3.5 MET * 70 kg = 245 kcal
        cal = estimate_calories_burned(
            duration_minutes=60,
            user_weight_kg=70.0,
            total_sets=10,
            total_volume_kg=1000.0,
        )
        assert cal == round(BASE_MET * 70.0, 1)

    def test_high_met_by_sets(self):
        cal = estimate_calories_burned(
            duration_minutes=60,
            user_weight_kg=80.0,
            total_sets=20,
            total_volume_kg=500.0,
        )
        assert cal == round(HIGH_MET * 80.0, 1)

    def test_high_met_by_volume(self):
        cal = estimate_calories_burned(
            duration_minutes=60,
            user_weight_kg=80.0,
            total_sets=5,
            total_volume_kg=8000.0,
        )
        assert cal == round(HIGH_MET * 80.0, 1)

    def test_weight_fallback(self):
        cal = estimate_calories_burned(
            duration_minutes=60,
            user_weight_kg=None,
            total_sets=1,
            total_volume_kg=0.0,
        )
        assert cal == round(BASE_MET * DEFAULT_USER_WEIGHT_KG, 1)

    def test_zero_duration_clamped_to_one_minute(self):
        cal = estimate_calories_burned(
            duration_minutes=0,
            user_weight_kg=70.0,
            total_sets=0,
            total_volume_kg=0.0,
        )
        # 1 min / 60 * 3.5 * 70 = ~4.08
        assert cal > 0
        assert cal < 10

    def test_scales_linearly_with_duration(self):
        a = estimate_calories_burned(
            duration_minutes=30, user_weight_kg=70.0, total_sets=5, total_volume_kg=0.0
        )
        b = estimate_calories_burned(
            duration_minutes=60, user_weight_kg=70.0, total_sets=5, total_volume_kg=0.0
        )
        assert abs(b - 2 * a) < 0.2
