"""Body composition estimation (US Navy method).

Pure functions only — no DB or Telegram dependencies. The handler layer
collects raw measurements, calls these functions for validation/estimation
and persists the resulting numbers via the user repository.

US Navy body fat formula (metric):

    male:    BFP = 495 / (1.0324 - 0.19077 * log10(waist - neck)
                          + 0.15456 * log10(height)) - 450
    female:  BFP = 495 / (1.29579 - 0.35004 * log10(waist + hip - neck)
                          + 0.22100 * log10(height)) - 450

The macro-basis weight switches to lean mass once BMI ≥ 30 so that protein
and fat targets stop scaling linearly with total weight for users where a
substantial fraction of body weight is fat tissue. Below that threshold
total body weight remains the basis (consistent with the original norms).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

# --- Validation bounds ---------------------------------------------------
NECK_CM_MIN = 20.0
NECK_CM_MAX = 80.0
WAIST_CM_MIN = 40.0
WAIST_CM_MAX = 200.0
HIP_CM_MIN = 40.0
HIP_CM_MAX = 200.0

# Body fat percent is reported back inside this range. Values outside it
# almost always indicate bad measurements and are rejected up front.
BODY_FAT_MIN_PERCENT = 3.0
BODY_FAT_MAX_PERCENT = 70.0

# BMI threshold above which we switch the macro basis from total body
# weight to estimated lean mass.
HIGH_BMI_THRESHOLD = 30.0


class BodyCompGender(str, Enum):
    male = "male"
    female = "female"


@dataclass(frozen=True)
class BodyCompositionResult:
    body_fat_percent: float
    fat_mass_kg: float
    lean_mass_kg: float
    macro_basis_weight_kg: float
    method: str = "us_navy"


class BodyCompositionError(ValueError):
    """Raised when the supplied measurements cannot produce a usable estimate."""


def calculate_bmi(weight_kg: float, height_cm: float | int) -> float:
    if weight_kg <= 0 or height_cm <= 0:
        raise BodyCompositionError("Вес и рост должны быть положительными.")
    height_m = height_cm / 100.0
    return weight_kg / (height_m * height_m)


def calculate_us_navy_body_fat(
    *,
    gender: BodyCompGender,
    height_cm: float | int,
    neck_cm: float,
    waist_cm: float,
    hip_cm: float | None = None,
) -> float:
    """Return estimated body-fat percent (0..100). Raises ``BodyCompositionError``."""
    if height_cm <= 0:
        raise BodyCompositionError("Рост должен быть больше нуля.")
    if not NECK_CM_MIN <= neck_cm <= NECK_CM_MAX:
        raise BodyCompositionError(
            f"Обхват шеи должен быть в пределах {NECK_CM_MIN:.0f}–{NECK_CM_MAX:.0f} см."
        )
    if not WAIST_CM_MIN <= waist_cm <= WAIST_CM_MAX:
        raise BodyCompositionError(
            f"Обхват талии должен быть в пределах {WAIST_CM_MIN:.0f}–{WAIST_CM_MAX:.0f} см."
        )

    if gender == BodyCompGender.male:
        if waist_cm <= neck_cm:
            raise BodyCompositionError(
                "Обхват талии должен быть больше обхвата шеи."
            )
        denom = (
            1.0324
            - 0.19077 * math.log10(waist_cm - neck_cm)
            + 0.15456 * math.log10(height_cm)
        )
    else:
        if hip_cm is None:
            raise BodyCompositionError("Для женщин нужен обхват бёдер.")
        if not HIP_CM_MIN <= hip_cm <= HIP_CM_MAX:
            raise BodyCompositionError(
                f"Обхват бёдер должен быть в пределах {HIP_CM_MIN:.0f}–{HIP_CM_MAX:.0f} см."
            )
        if waist_cm + hip_cm <= neck_cm:
            raise BodyCompositionError(
                "Сумма обхватов талии и бёдер должна превышать обхват шеи."
            )
        denom = (
            1.29579
            - 0.35004 * math.log10(waist_cm + hip_cm - neck_cm)
            + 0.22100 * math.log10(height_cm)
        )

    if denom <= 0:
        raise BodyCompositionError(
            "Не удалось рассчитать процент жира — проверь обмеры."
        )
    body_fat_percent = 495.0 / denom - 450.0

    if not BODY_FAT_MIN_PERCENT <= body_fat_percent <= BODY_FAT_MAX_PERCENT:
        raise BodyCompositionError(
            "Расчётный процент жира получился вне разумного диапазона. "
            "Проверь обмеры и повтори."
        )
    return body_fat_percent


def calculate_lean_mass(weight_kg: float, body_fat_percent: float) -> float:
    if weight_kg <= 0:
        raise BodyCompositionError("Вес должен быть больше нуля.")
    if not BODY_FAT_MIN_PERCENT <= body_fat_percent <= BODY_FAT_MAX_PERCENT:
        raise BodyCompositionError("Процент жира вне разумного диапазона.")
    fat_mass_kg = weight_kg * body_fat_percent / 100.0
    return weight_kg - fat_mass_kg


def select_macro_basis_weight(
    *,
    weight_kg: float,
    height_cm: float | int,
    lean_mass_kg: float | None,
) -> float:
    """Pick the weight used for protein/fat targets.

    Returns ``lean_mass_kg`` when BMI ≥ 30 and a lean-mass estimate is
    available; otherwise ``weight_kg``. This keeps macro recommendations
    realistic for users whose total body weight contains a large fat
    component without changing behaviour for everyone else.
    """
    if lean_mass_kg is not None and lean_mass_kg > 0:
        bmi = calculate_bmi(weight_kg, height_cm)
        if bmi >= HIGH_BMI_THRESHOLD:
            return lean_mass_kg
    return weight_kg


def estimate_body_composition(
    *,
    gender: BodyCompGender,
    height_cm: float | int,
    weight_kg: float,
    neck_cm: float,
    waist_cm: float,
    hip_cm: float | None = None,
) -> BodyCompositionResult:
    """End-to-end estimate: BFP → fat mass → lean mass → macro basis."""
    if weight_kg <= 0:
        raise BodyCompositionError("Вес должен быть больше нуля.")
    body_fat_percent = calculate_us_navy_body_fat(
        gender=gender,
        height_cm=height_cm,
        neck_cm=neck_cm,
        waist_cm=waist_cm,
        hip_cm=hip_cm,
    )
    fat_mass_kg = weight_kg * body_fat_percent / 100.0
    lean_mass_kg = weight_kg - fat_mass_kg
    macro_basis = select_macro_basis_weight(
        weight_kg=weight_kg,
        height_cm=height_cm,
        lean_mass_kg=lean_mass_kg,
    )
    return BodyCompositionResult(
        body_fat_percent=round(body_fat_percent, 1),
        fat_mass_kg=round(fat_mass_kg, 1),
        lean_mass_kg=round(lean_mass_kg, 1),
        macro_basis_weight_kg=round(macro_basis, 1),
    )
