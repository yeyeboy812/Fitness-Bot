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
    """Text-based progress bar."""
    if not target or target <= 0:
        return ""
    ratio = min(current / target, 1.0)
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled) + f" {ratio:.0%}"


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

    # Macros
    pro_str = f"{summary.total_protein:.0f}"
    if summary.protein_norm:
        pro_str += f" / {summary.protein_norm}"
    fat_str = f"{summary.total_fat:.0f}"
    if summary.fat_norm:
        fat_str += f" / {summary.fat_norm}"
    carb_str = f"{summary.total_carbs:.0f}"
    if summary.carb_norm:
        carb_str += f" / {summary.carb_norm}"

    lines.append(f"🥩 Белки: {pro_str} г")
    lines.append(f"🧈 Жиры: {fat_str} г")
    lines.append(f"🍞 Углеводы: {carb_str} г")

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
