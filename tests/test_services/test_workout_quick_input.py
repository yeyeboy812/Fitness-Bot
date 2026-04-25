"""Fast workout set input parser."""

import math

import pytest

from bot.services.workout import LB_TO_KG, parse_weight_reps_input


@pytest.mark.parametrize(
    ("raw", "weight", "reps"),
    [
        ("93x15", 93.0, 15),
        ("93х15", 93.0, 15),
        ("93 x 15", 93.0, 15),
        ("93 х 15", 93.0, 15),
        ("93кг x 15", 93.0, 15),
        ("93 кг х 15", 93.0, 15),
        ("93kg x 15", 93.0, 15),
        ("93 kg x 15", 93.0, 15),
        ("12.5x10", 12.5, 10),
        ("12,5х10", 12.5, 10),
        ("12,5kg x 10", 12.5, 10),
    ],
)
def test_parse_kg_input(raw, weight, reps):
    parsed = parse_weight_reps_input(raw)

    assert parsed is not None
    assert parsed.weight_kg == weight
    assert parsed.reps == reps
    assert parsed.original_weight_unit == "kg"
    assert parsed.original_weight_value == weight


@pytest.mark.parametrize(
    "raw",
    [
        "200lb x 10",
        "200 lbs x 10",
        "200lb x 10",
        "200 lb x 10",
        "200lbsx10",
        "200 lbx10",
        "200 фунтов x 10",
        "200 фунта х 10",
        "200 ф x 10",
        "200ф x 10",
    ],
)
def test_parse_lb_input(raw):
    parsed = parse_weight_reps_input(raw)

    assert parsed is not None
    assert parsed.original_weight_unit == "lb"
    assert parsed.original_weight_value == 200.0
    assert parsed.reps == 10
    # 200 lb -> 90.718474 kg
    assert math.isclose(parsed.weight_kg, 200 * LB_TO_KG)
    assert round(parsed.weight_kg, 1) == 90.7


@pytest.mark.parametrize(
    "raw",
    [
        "0x10",
        "93x0",
        "0lb x 10",
        "200lb x 0",
        "abc",
        "93",
        "",
        "x10",
        "-5x10",
    ],
)
def test_parse_invalid_input(raw):
    assert parse_weight_reps_input(raw) is None
