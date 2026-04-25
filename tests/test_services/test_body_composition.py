"""Body composition estimation helpers."""

import pytest

from bot.services.body_composition import (
    BodyCompGender,
    BodyCompositionError,
    calculate_lean_mass,
    estimate_body_composition,
    select_macro_basis_weight,
)


def test_us_navy_formula_male_returns_plausible_body_fat_percent():
    result = estimate_body_composition(
        gender=BodyCompGender.male,
        height_cm=178,
        weight_kg=140,
        neck_cm=45,
        waist_cm=125,
    )

    assert result.body_fat_percent == pytest.approx(36.6, abs=0.2)
    assert 3 <= result.body_fat_percent <= 70


def test_us_navy_formula_female_returns_plausible_body_fat_percent():
    result = estimate_body_composition(
        gender=BodyCompGender.female,
        height_cm=165,
        weight_kg=90,
        neck_cm=35,
        waist_cm=95,
        hip_cm=110,
    )

    assert result.body_fat_percent == pytest.approx(42.5, abs=0.2)
    assert 3 <= result.body_fat_percent <= 70


def test_lean_mass_is_calculated_from_weight_and_body_fat_percent():
    assert calculate_lean_mass(140, 36.6) == pytest.approx(88.76)


def test_high_bmi_uses_lean_mass_as_macro_basis():
    basis = select_macro_basis_weight(
        weight_kg=140,
        height_cm=178,
        lean_mass_kg=88.7,
    )

    assert basis == 88.7


def test_lower_bmi_uses_total_weight_as_macro_basis():
    result = estimate_body_composition(
        gender=BodyCompGender.male,
        height_cm=178,
        weight_kg=75,
        neck_cm=39,
        waist_cm=84,
    )

    assert result.macro_basis_weight_kg == 75


def test_invalid_measurements_are_rejected():
    with pytest.raises(BodyCompositionError):
        estimate_body_composition(
            gender=BodyCompGender.male,
            height_cm=178,
            weight_kg=140,
            neck_cm=45,
            waist_cm=44,
        )
