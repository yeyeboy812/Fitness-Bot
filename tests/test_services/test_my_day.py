"""My-day header block — pure helpers for the main menu."""

from __future__ import annotations

import pytest

from bot.models.user import Gender
from bot.services.my_day import (
    _COACH_LINES,
    _tier_index,
    build_my_day_block,
    calculate_progress,
    format_calories_line,
    format_streak_line,
    format_workout_line,
    pick_coach_line,
    pick_rank,
    render_my_day_block,
)


# ---------------------------------------------------------------------------
# calculate_progress
# ---------------------------------------------------------------------------
class TestCalculateProgress:
    def test_nothing_logged_is_zero(self):
        assert calculate_progress(
            calories_today=0, calorie_goal=2000, workouts_today=0
        ) == 0

    def test_full_day_caps_at_hundred(self):
        """Calories at goal (40) + workout (40) + activity (20) = 100."""
        assert calculate_progress(
            calories_today=2000, calorie_goal=2000, workouts_today=1
        ) == 100

    def test_overshoot_still_caps_at_hundred(self):
        assert calculate_progress(
            calories_today=4000, calorie_goal=2000, workouts_today=3
        ) == 100

    def test_only_food_logged_without_workout(self):
        """Half-goal calories (20) + activity bonus (20) = 40."""
        assert calculate_progress(
            calories_today=1000, calorie_goal=2000, workouts_today=0
        ) == 40

    def test_only_workout_no_food(self):
        """Workout (40) + activity (20) = 60, calories part = 0."""
        assert calculate_progress(
            calories_today=0, calorie_goal=2000, workouts_today=1
        ) == 60

    def test_no_calorie_goal_still_scores_workout_and_activity(self):
        """Missing goal → calorie part 0, rest still counts."""
        assert calculate_progress(
            calories_today=1500, calorie_goal=None, workouts_today=1
        ) == 60

    def test_no_calorie_goal_no_workout_only_food(self):
        """No goal, no workout, food present → only activity bonus (20)."""
        assert calculate_progress(
            calories_today=800, calorie_goal=None, workouts_today=0
        ) == 20

    def test_zero_goal_behaves_like_missing(self):
        assert calculate_progress(
            calories_today=500, calorie_goal=0, workouts_today=0
        ) == 20

    def test_negative_inputs_clamped(self):
        assert calculate_progress(
            calories_today=-100, calorie_goal=2000, workouts_today=-5
        ) == 0

    def test_multiple_workouts_capped_at_workout_bucket(self):
        """More than one workout doesn't double-count the workout bucket."""
        assert calculate_progress(
            calories_today=0, calorie_goal=2000, workouts_today=5
        ) == 60


# ---------------------------------------------------------------------------
# pick_rank — boundary mapping
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "progress,expected",
    [
        (0, "Спящий режим"),
        (9, "Спящий режим"),
        (10, "Разогрев"),
        (29, "Разогрев"),
        (30, "Вход в ритм"),
        (49, "Вход в ритм"),
        (50, "Половина пути"),
        (69, "Половина пути"),
        (70, "Режим машины"),
        (89, "Режим машины"),
        (90, "Почти легенда"),
        (99, "Почти легенда"),
        (100, "Железная легенда"),
    ],
)
def test_pick_rank_buckets(progress, expected):
    assert pick_rank(progress) == expected


@pytest.mark.parametrize(
    "progress,expected_index",
    [(0, 0), (10, 1), (30, 2), (50, 3), (70, 4), (90, 5), (100, 6)],
)
def test_tier_index_boundaries(progress, expected_index):
    assert _tier_index(progress) == expected_index


# ---------------------------------------------------------------------------
# pick_coach_line — gender branching + fallback
# ---------------------------------------------------------------------------
class TestPickCoachLine:
    def test_male_female_neutral_all_return_strings(self):
        for gender in (Gender.male, Gender.female, None):
            for progress in (0, 50, 100):
                line = pick_coach_line(progress, gender)
                assert isinstance(line, str) and line

    def test_unknown_gender_falls_back_to_neutral(self):
        line = pick_coach_line(0, None)
        assert line == _COACH_LINES["neutral"][0]

    def test_tier_lines_within_a_gender_differ(self):
        """Each of the 7 tiers for a gender must pick a different line."""
        for gender in (Gender.male, Gender.female, None):
            lines = [
                pick_coach_line(p, gender) for p in (0, 10, 30, 50, 70, 90, 100)
            ]
            assert len(set(lines)) == 7, f"duplicate lines for gender={gender}"

    def test_all_three_tiers_have_seven_lines(self):
        for key, pool in _COACH_LINES.items():
            assert len(pool) == 7, f"{key} pool must have 7 tier lines"


# ---------------------------------------------------------------------------
# Metric formatters
# ---------------------------------------------------------------------------
class TestCaloriesLine:
    def test_with_goal(self):
        assert format_calories_line(1234.4, 2000) == "1234 / 2000 ккал"

    def test_without_goal(self):
        assert format_calories_line(1234.7, None) == "1235 ккал"

    def test_zero_goal_treated_as_missing(self):
        assert format_calories_line(500, 0) == "500 ккал"

    def test_negative_calories_clamped(self):
        assert format_calories_line(-50, 2000) == "0 / 2000 ккал"


class TestWorkoutLine:
    @pytest.mark.parametrize(
        "count,expected",
        [
            (0, "пока нет"),
            (1, "есть сегодня"),
            (2, "2 сегодня"),
            (5, "5 сегодня"),
            (-3, "пока нет"),
        ],
    )
    def test_counts(self, count, expected):
        assert format_workout_line(count) == expected


class TestStreakLine:
    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, "0 дней"),
            (1, "1 день"),
            (2, "2 дня"),
            (4, "4 дня"),
            (5, "5 дней"),
            (11, "11 дней"),
            (14, "14 дней"),
            (21, "21 день"),
            (22, "22 дня"),
            (25, "25 дней"),
            (-5, "0 дней"),
        ],
    )
    def test_russian_plurals(self, n, expected):
        assert format_streak_line(n) == expected


# ---------------------------------------------------------------------------
# build + render
# ---------------------------------------------------------------------------
class TestBuildAndRender:
    def test_empty_user_produces_zero_progress_block(self):
        """Fresh user with no data must not blow up and yields progress=0."""
        block = build_my_day_block(
            calories_today=0,
            calorie_goal=None,
            workouts_today=0,
            current_streak=0,
            gender=None,
        )
        assert block.progress == 0
        assert block.rank == "Спящий режим"
        rendered = render_my_day_block(block)
        assert "🎯 Прогресс за день — 0%" in rendered
        assert "🔥 Серия: 0 дней" in rendered
        assert "🍽️ 0 ккал" in rendered
        assert "🏋️ пока нет" in rendered

    def test_render_contains_expected_skeleton(self):
        block = build_my_day_block(
            calories_today=1500,
            calorie_goal=2000,
            workouts_today=1,
            current_streak=3,
            gender=Gender.female,
        )
        rendered = render_my_day_block(block)
        # Header with progress
        assert rendered.startswith("🎯 Прогресс за день — ")
        assert f"{block.progress}%" in rendered.splitlines()[0]
        # All four metric/coach markers present
        for marker in ("🏅", "🤖", "🍽️", "🏋️", "🔥 Серия:"):
            assert marker in rendered

    def test_render_does_not_contain_legacy_greeting_phrases(self):
        """The old header phrases must not leak into the new block."""
        block = build_my_day_block(
            calories_today=1900,
            calorie_goal=2000,
            workouts_today=1,
            current_streak=7,
            gender=Gender.male,
        )
        rendered = render_my_day_block(block)
        legacy_markers = [
            "Выбери раздел",
            "Остановись-ка",
            "пора становиться сильным",
            "Молодец, ты можешь ещё больше",
            "Питание и дневник",
            "Тренировки и прогресс",
            "Свои продукты и рецепты",
        ]
        for marker in legacy_markers:
            assert marker not in rendered, f"legacy text leaked: {marker!r}"

    def test_male_and_female_full_day_lines_differ(self):
        male = build_my_day_block(
            calories_today=2000, calorie_goal=2000,
            workouts_today=1, current_streak=0, gender=Gender.male,
        )
        female = build_my_day_block(
            calories_today=2000, calorie_goal=2000,
            workouts_today=1, current_streak=0, gender=Gender.female,
        )
        assert male.progress == female.progress == 100
        assert male.coach_line != female.coach_line
