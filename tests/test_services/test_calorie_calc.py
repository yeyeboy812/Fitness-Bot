"""Tests for calorie calculation pure functions."""

from bot.services.calorie_calc import (
    ActivityLevel,
    FAT_G_PER_KG_MAX,
    FAT_G_PER_KG_STANDARD,
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
    def test_all_macros_rounded_to_10(self):
        macros = calculate_macros(2000, Goal.lose, 80.0)
        assert macros.protein_g % 10 == 0
        assert macros.fat_g % 10 == 0
        assert macros.carbs_g % 10 == 0

    def test_fat_is_per_kg_not_share_of_calories(self):
        # 80kg @ 0.9 g/kg = 72g raw → rounded to 70g.
        # Old algorithm gave 27% of 2000 / 9 = 60g, so make sure we are not
        # accidentally back to the share-of-calories formula on big calories:
        # 80kg @ 0.9 g/kg = 72g raw → 70g rounded, regardless of total.
        macros_low = calculate_macros(1800, Goal.maintain, 80.0)
        macros_high = calculate_macros(3000, Goal.maintain, 80.0)
        assert macros_low.fat_g == macros_high.fat_g == 70

    def test_fat_capped_at_one_per_kg(self):
        macros = calculate_macros(3500, Goal.gain, 80.0)
        # Hard cap: never above weight * 1.0 g/kg.
        assert macros.fat_g <= 80
        assert macros.fat_g <= round(80.0 * FAT_G_PER_KG_MAX / 10) * 10

    def test_lose_macros_balance(self):
        macros = calculate_macros(2000, Goal.lose, 80.0)
        assert macros.calories == 2000
        # 80kg lose: 2.2 g/kg → 176 → 180g protein.
        assert macros.protein_g == 180
        # 80kg @ 0.9 g/kg → 72g → 70g fat.
        assert macros.fat_g == 70
        assert macros.carbs_g >= 0
        # Total calories should be close to target (rounding to 10 introduces
        # up to ~50 kcal drift).
        total = macros.protein_g * 4 + macros.fat_g * 9 + macros.carbs_g * 4
        assert abs(total - 2000) <= 50

    def test_maintain_macros_protein_rounded(self):
        # 75kg maintain: 1.8 g/kg → 135 → rounded to 140.
        macros = calculate_macros(2500, Goal.maintain, 75.0)
        assert macros.protein_g == 140

    def test_carbs_never_negative_on_aggressive_deficit(self):
        # 100kg with absurdly low calories: protein 220, fat 90 →
        # 220*4 + 90*9 = 1690 cal of P+F alone, which exceeds 1000.
        macros = calculate_macros(1000, Goal.lose, 100.0)
        assert macros.carbs_g >= 0
        # Protein and fat still locked to body weight.
        assert macros.protein_g == 220
        assert macros.fat_g == 90

    def test_fat_standard_constant(self):
        # Sanity-check the constant used as MVP default.
        assert FAT_G_PER_KG_STANDARD == 0.9

    def test_macro_basis_weight_overrides_protein_and_fat_basis(self):
        macros = calculate_macros(
            3000,
            Goal.maintain,
            weight_kg=140.0,
            macro_basis_weight_kg=88.7,
        )

        assert macros.protein_g == 160
        assert macros.fat_g == 80


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
        assert 1800 < norms.calories < 2800
        # 85kg @ 0.9 g/kg = 76.5g → 80g rounded.
        assert norms.fat_g == 80
        # All macros multiples of 10.
        assert norms.protein_g % 10 == 0
        assert norms.fat_g % 10 == 0
        assert norms.carbs_g % 10 == 0
        # Profile has enough calories for non-zero carbs at this weight.
        assert norms.carbs_g > 0

    def test_calculate_norms_uses_macro_basis_weight_for_macros(self):
        norms = calculate_norms(
            gender=Gender.male,
            weight_kg=140.0,
            height_cm=178,
            age=35,
            activity_level=ActivityLevel.light,
            goal=Goal.maintain,
            macro_basis_weight_kg=88.7,
        )

        assert norms.protein_g == 160
        assert norms.fat_g == 80
        assert norms.fat_g < 130

    def test_recalc_uses_new_logic_after_weight_change(self):
        # Models the UserService.recalculate_norms code path (same call site).
        original = calculate_norms(
            gender=Gender.male,
            weight_kg=70.0,
            height_cm=178,
            age=30,
            activity_level=ActivityLevel.moderate,
            goal=Goal.maintain,
        )
        heavier = calculate_norms(
            gender=Gender.male,
            weight_kg=90.0,
            height_cm=178,
            age=30,
            activity_level=ActivityLevel.moderate,
            goal=Goal.maintain,
        )
        # Fat scales with body weight, not calories.
        assert original.fat_g == 60   # 70 * 0.9 = 63 → 60
        assert heavier.fat_g == 80    # 90 * 0.9 = 81 → 80
