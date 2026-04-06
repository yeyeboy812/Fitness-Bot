"""Tests for calorie calculation pure functions."""

from bot.services.calorie_calc import (
    ActivityLevel,
    Gender,
    Goal,
    calculate_bmr,
    calculate_macros,
    calculate_norms,
    calculate_tdee,
    adjust_for_goal,
)


class TestBMR:
    def test_male_bmr(self):
        # 10*80 + 6.25*180 - 5*25 + 5 = 800 + 1125 - 125 + 5 = 1805
        result = calculate_bmr(Gender.male, 80.0, 180, 25)
        assert result == 1805.0

    def test_female_bmr(self):
        # 10*60 + 6.25*165 - 5*30 - 161 = 600 + 1031.25 - 150 - 161 = 1320.25
        result = calculate_bmr(Gender.female, 60.0, 165, 30)
        assert result == 1320.25


class TestTDEE:
    def test_sedentary(self):
        tdee = calculate_tdee(1800.0, ActivityLevel.sedentary)
        assert tdee == 1800.0 * 1.2

    def test_moderate(self):
        tdee = calculate_tdee(1800.0, ActivityLevel.moderate)
        assert tdee == 1800.0 * 1.55


class TestGoalAdjustment:
    def test_lose(self):
        result = adjust_for_goal(2500.0, Goal.lose)
        assert result == round(2500 * 0.85)

    def test_maintain(self):
        result = adjust_for_goal(2500.0, Goal.maintain)
        assert result == 2500

    def test_gain(self):
        result = adjust_for_goal(2500.0, Goal.gain)
        assert result == round(2500 * 1.15)


class TestMacros:
    def test_lose_macros(self):
        macros = calculate_macros(2000, Goal.lose, 80.0)
        assert macros.calories == 2000
        assert macros.protein_g == round(80.0 * 2.2)  # 176
        assert macros.fat_g > 0
        assert macros.carbs_g > 0
        # Total calories should roughly match
        total = macros.protein_g * 4 + macros.fat_g * 9 + macros.carbs_g * 4
        assert abs(total - 2000) < 10  # small rounding tolerance

    def test_maintain_macros(self):
        macros = calculate_macros(2500, Goal.maintain, 75.0)
        assert macros.protein_g == round(75.0 * 1.8)


class TestFullPipeline:
    def test_calculate_norms(self):
        norms = calculate_norms(
            gender=Gender.male,
            weight_kg=85.0,
            height_cm=180,
            age=28,
            activity_level=ActivityLevel.moderate,
            goal=Goal.lose,
        )
        # Should produce reasonable results
        assert 1800 < norms.calories < 2800
        assert norms.protein_g > 100
        assert norms.fat_g > 40
        assert norms.carbs_g > 100
