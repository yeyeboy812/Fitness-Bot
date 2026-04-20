"""Text formatting helpers for bot messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot.models.meal import Meal
    from bot.schemas.nutrition import DailySummary


def format_nutrition_line(cal: float, protein: float, fat: float, carbs: float) -> str:
    """One-line КБЖУ string."""
    return f"{cal:.0f} ккал | Б: {protein:.1f}г | Ж: {fat:.1f}г | У: {carbs:.1f}г"


def _progress_bar(current: float, target: float | None, width: int = 10) -> str:
    """Emoji-square progress bar. Renders identically across Telegram clients.

    Uses 🟩 for filled cells and ⬜ for empty. Fill caps at ``width`` even when
    ``current`` overshoots the target — the numeric percentage still reflects
    the real ratio so overshoots stay visible.
    """
    if not target or target <= 0:
        return ""
    ratio = current / target
    filled = min(round(ratio * width), width)
    bar = "🟩" * filled + "⬜" * (width - filled)
    return f"{bar} {int(ratio * 100)}%"


_DIVIDER = "━━━━━━━━━━━━━━━━━"

_MEAL_TYPE_LABELS = {
    "breakfast": "🍳 Завтрак",
    "lunch": "🥗 Обед",
    "dinner": "🍽 Ужин",
    "snack": "🍌 Перекус",
}


def format_daily_summary(summary: "DailySummary", meals: list["Meal"]) -> str:
    """Format the «Мой день» screen.

    Progress bar and the remaining/overshoot line both use ``net_calories``
    (eaten − burned) so the three numbers — bar fill, "Чистые калории",
    and "До цели осталось" — stay consistent.
    """
    lines: list[str] = [f"📊 <b>Ваш день — {summary.date.strftime('%d.%m.%Y')}</b>"]
    lines.append("")

    # --- Calorie block -------------------------------------------------
    norm_str = f" / {summary.calorie_norm}" if summary.calorie_norm else ""
    lines.append(f"🍽 Съедено: <b>{summary.total_calories:.0f}</b>{norm_str} ккал")
    lines.append(f"🔥 Сожжено: {summary.burned_calories:.0f} ккал")
    lines.append(f"⚖️ Чистые калории: <b>{summary.net_calories:.0f}</b> ккал")

    if summary.calorie_norm:
        remaining = summary.calorie_norm - summary.net_calories
        if remaining >= 0:
            lines.append(f"📉 До цели осталось: <b>{remaining:.0f}</b> ккал")
        else:
            lines.append(f"📈 Превышение цели: <b>{abs(remaining):.0f}</b> ккал")

    cal_bar = _progress_bar(summary.net_calories, summary.calorie_norm)
    if cal_bar:
        lines.append("")
        lines.append(cal_bar)

    # --- Activity block ------------------------------------------------
    lines.append("")
    if summary.workouts_count > 0:
        lines.append(f"🏋️ Тренировок сегодня: <b>{summary.workouts_count}</b>")
        activity_bits: list[str] = []
        if summary.sets_count:
            activity_bits.append(f"🔁 Подходов: {summary.sets_count}")
        if summary.training_minutes:
            activity_bits.append(f"⏱ {summary.training_minutes} мин")
        if summary.total_volume_kg > 0:
            activity_bits.append(f"📦 {summary.total_volume_kg:.0f} кг")
        if activity_bits:
            lines.append("   " + " · ".join(activity_bits))
    else:
        lines.append("🏋️ Тренировок сегодня: 0")

    # --- Macros --------------------------------------------------------
    lines.append("")
    lines.append(_DIVIDER)
    lines.append("")
    lines.append(_macro_line("🥩", "Белки", summary.total_protein, summary.protein_norm))
    lines.append(_macro_line("🧈", "Жиры", summary.total_fat, summary.fat_norm))
    lines.append(_macro_line("🍞", "Углеводы", summary.total_carbs, summary.carb_norm))

    # --- Meals ---------------------------------------------------------
    lines.append("")
    lines.append(_DIVIDER)
    if meals:
        for meal in meals:
            meal_type_value = meal.meal_type.value if meal.meal_type else ""
            label = _MEAL_TYPE_LABELS.get(meal_type_value, "🍽 Приём пищи")
            meal_cal = sum(item.calories for item in meal.items)
            lines.append("")
            lines.append(f"{label} — <b>{meal_cal:.0f} ккал</b>")
            for item in meal.items:
                lines.append(
                    f"• {item.name_snapshot}, {item.amount_grams:.0f} г — {item.calories:.0f} ккал"
                )
    else:
        lines.append("")
        lines.append("🍽 Сегодня приёмов пищи ещё нет.")

    return "\n".join(lines)


def _macro_line(emoji: str, label: str, current: float, norm: float | None, unit: str = "г") -> str:
    norm_str = f" / {norm}" if norm else ""
    return f"{emoji} {label}: <b>{current:.0f}</b>{norm_str} {unit}"
