"""My-day header block for the main menu.

Pure helpers: progress calculation, rank lookup, coach-line selection,
metric-string formatting, and the final text render. All data fetching
stays in the caller (the ``main_menu`` handler) so this module is
trivially unit-testable without a DB or Telegram context.
"""

from __future__ import annotations

from dataclasses import dataclass

from bot.models.user import Gender


@dataclass(frozen=True)
class MyDayBlock:
    progress: int
    rank: str
    coach_line: str
    calories_line: str
    workout_line: str
    streak_line: str


# ---------------------------------------------------------------------------
# Progress / rank
# ---------------------------------------------------------------------------
def calculate_progress(
    *,
    calories_today: float,
    calorie_goal: int | None,
    workouts_today: int,
) -> int:
    """Return an integer 0..100 describing today's momentum.

    Weights: calories 40, workout presence 40, any activity 20.

    When ``calorie_goal`` is missing/zero the calorie part contributes 0 —
    there is no reference point to measure proximity against. Users with
    no goal still get a meaningful 0..60 signal from workout + activity.
    """
    calories_today = max(float(calories_today), 0.0)
    workouts_today = max(int(workouts_today), 0)

    if calorie_goal and calorie_goal > 0:
        calories_part = min(calories_today / calorie_goal, 1.0) * 40.0
    else:
        calories_part = 0.0

    workout_part = 40 if workouts_today >= 1 else 0
    activity_part = 20 if (workouts_today >= 1 or calories_today > 0) else 0

    total = round(calories_part + workout_part + activity_part)
    return max(0, min(100, int(total)))


_RANKS: tuple[tuple[int, str], ...] = (
    (100, "Железная легенда"),
    (90, "Почти легенда"),
    (70, "Режим машины"),
    (50, "Половина пути"),
    (30, "Вход в ритм"),
    (10, "Разогрев"),
    (0, "Спящий режим"),
)


def pick_rank(progress: int) -> str:
    for threshold, label in _RANKS:
        if progress >= threshold:
            return label
    return _RANKS[-1][1]


# ---------------------------------------------------------------------------
# Coach line — per-gender tier tables
# ---------------------------------------------------------------------------
# Index 0..6 matches the tier returned by _tier_index.
_COACH_LINES: dict[str, tuple[str, ...]] = {
    "male": (
        "Система пока фиксирует только признаки жизни. Пора шевелиться.",
        "Разогрев пошёл. Не выключайся.",
        "Ритм держишь. День не слит.",
        "Половина пути позади — это уже база.",
        "Дисциплина сегодня явно не спит.",
        "Почти чемпион. Последний рывок.",
        "Сегодня внутренний тренер аплодирует стоя. Красавчик.",
    ),
    "female": (
        "Датчики ловят только тепло. Пора подкинуть действий.",
        "Разгон пошёл. Не тормози.",
        "Темп держишь, день идёт по плану.",
        "Половина пути пройдена — дальше только мощнее.",
        "Дисциплина сегодня явно под контролем.",
        "Почти чемпионка. Финишная прямая.",
        "Сегодня внутренний тренер аплодирует стоя. Красотка.",
    ),
    "neutral": (
        "Система пока видит только признаки жизни. Двигаемся.",
        "Разогрев пошёл. Продолжаем.",
        "Ритм поймали. Так держать.",
        "Половина пути — уже неплохо.",
        "Дисциплина сегодня явно не спит.",
        "Почти легенда. Ещё чуть-чуть.",
        "Железный день. Внутренний тренер аплодирует стоя.",
    ),
}


def _tier_index(progress: int) -> int:
    """Map 0..100 → 0..6 bucket (same cuts as the rank table)."""
    if progress >= 100:
        return 6
    if progress >= 90:
        return 5
    if progress >= 70:
        return 4
    if progress >= 50:
        return 3
    if progress >= 30:
        return 2
    if progress >= 10:
        return 1
    return 0


def pick_coach_line(progress: int, gender: Gender | None) -> str:
    if gender is Gender.male:
        pool = _COACH_LINES["male"]
    elif gender is Gender.female:
        pool = _COACH_LINES["female"]
    else:
        pool = _COACH_LINES["neutral"]
    return pool[_tier_index(progress)]


# ---------------------------------------------------------------------------
# Metric lines
# ---------------------------------------------------------------------------
def format_calories_line(calories_today: float, calorie_goal: int | None) -> str:
    current = max(int(round(float(calories_today))), 0)
    if calorie_goal and calorie_goal > 0:
        return f"{current} / {calorie_goal} ккал"
    return f"{current} ккал"


def _format_progress_value(value: float | int | None) -> int:
    return max(int(round(float(value or 0))), 0)


def _has_progress_target(value: float | int | None) -> bool:
    return value is not None and value > 0


def format_today_nutrition_progress(
    *,
    current_calories: float,
    target_calories: int | None,
    current_protein: float,
    target_protein: int | None,
    current_fat: float,
    target_fat: int | None,
    current_carbs: float,
    target_carbs: int | None,
) -> str:
    targets = (target_calories, target_protein, target_fat, target_carbs)
    if not all(_has_progress_target(target) for target in targets):
        return "Сегодня пока нет данных по БЖУ."

    return (
        "Сегодня:\n"
        f"🔥 {_format_progress_value(current_calories)} / {_format_progress_value(target_calories)} ккал\n"
        f"🥩 Б: {_format_progress_value(current_protein)} / {_format_progress_value(target_protein)} г\n"
        f"🥑 Ж: {_format_progress_value(current_fat)} / {_format_progress_value(target_fat)} г\n"
        f"🍚 У: {_format_progress_value(current_carbs)} / {_format_progress_value(target_carbs)} г"
    )


def format_workout_line(workouts_today: int) -> str:
    n = max(int(workouts_today), 0)
    if n == 0:
        return "пока нет"
    if n == 1:
        return "есть сегодня"
    return f"{n} сегодня"


def _plural_days(n: int) -> str:
    n_abs = abs(n) % 100
    if 11 <= n_abs <= 14:
        return "дней"
    last = n_abs % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дня"
    return "дней"


def format_streak_line(current_streak: int) -> str:
    n = max(int(current_streak), 0)
    return f"{n} {_plural_days(n)}"


# ---------------------------------------------------------------------------
# Final block build + render
# ---------------------------------------------------------------------------
def build_my_day_block(
    *,
    calories_today: float,
    calorie_goal: int | None,
    workouts_today: int,
    current_streak: int,
    gender: Gender | None,
) -> MyDayBlock:
    progress = calculate_progress(
        calories_today=calories_today,
        calorie_goal=calorie_goal,
        workouts_today=workouts_today,
    )
    return MyDayBlock(
        progress=progress,
        rank=pick_rank(progress),
        coach_line=pick_coach_line(progress, gender),
        calories_line=format_calories_line(calories_today, calorie_goal),
        workout_line=format_workout_line(workouts_today),
        streak_line=format_streak_line(current_streak),
    )


def render_my_day_block(block: MyDayBlock) -> str:
    return (
        f"🎯 Прогресс за день — {block.progress}%\n"
        f"\n"
        f"🏅 {block.rank}\n"
        f"🤖 {block.coach_line}\n"
        f"\n"
        f"🍽️ {block.calories_line}\n"
        f"🏋️ {block.workout_line}\n"
        f"🔥 Серия: {block.streak_line}"
    )
