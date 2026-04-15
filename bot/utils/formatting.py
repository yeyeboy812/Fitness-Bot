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


def format_daily_summary(summary: "DailySummary", meals: list["Meal"]) -> str:
    """Format full daily summary message."""
    lines = [f"📊 <b>Ваш день — {summary.date.strftime('%d.%m.%Y')}</b>\n"]

    # Calorie progress
    cal_bar = _progress_bar(summary.total_calories, summary.calorie_norm)
    norm_str = f" / {summary.calorie_norm}" if summary.calorie_norm else ""
    lines.append(f"🔥 Калории: {summary.total_calories:.0f}{norm_str} ккал")
    if cal_bar:
        lines.append(cal_bar)
    lines.append("")

    # Macros with progress bars
    def _macro_line(emoji: str, label: str, current: float, norm: float | None, unit: str = "г") -> list[str]:
        rows = [f"{emoji} {label}: {current:.0f}{f' / {norm}' if norm else ''} {unit}"]
        bar = _progress_bar(current, norm)
        if bar:
            rows.append(bar)
        return rows

    lines.extend(_macro_line("🥩", "Белки", summary.total_protein, summary.protein_norm))
    lines.extend(_macro_line("🧈", "Жиры", summary.total_fat, summary.fat_norm))
    lines.extend(_macro_line("🍞", "Углеводы", summary.total_carbs, summary.carb_norm))

    # Meal list
    type_labels = {
        "breakfast": "🍳 Завтрак",
        "lunch": "🥗 Обед",
        "dinner": "🍽 Ужин",
        "snack": "🍌 Перекус",
    }

    if meals:
        lines.append("\n━━━━━━━━━━━━━━━━━")
        for meal in meals:
            label = type_labels.get(meal.meal_type.value if meal.meal_type else "", "🍽 Приём пищи")
            meal_cal = sum(item.calories for item in meal.items)
            lines.append(f"\n{label} ({meal_cal:.0f} ккал)")
            for item in meal.items:
                lines.append(f"  • {item.name_snapshot} {item.amount_grams:.0f}г — {item.calories:.0f} ккал")

    # Remaining
    if summary.calorie_norm:
        remaining = summary.calorie_norm - summary.total_calories
        lines.append(f"\nОсталось: <b>{remaining:.0f} ккал</b>")

    return "\n".join(lines)
