"""Keyboards for the collector bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.exercise import ExerciseType, MuscleGroup


def submission_kind_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏋️ Упражнение", callback_data="collector_kind:exercise")],
            [InlineKeyboardButton(text="🥗 Продукт", callback_data="collector_kind:product")],
            [InlineKeyboardButton(text="🧾 Рецепт", callback_data="collector_kind:recipe")],
        ]
    )


def muscle_group_kb() -> InlineKeyboardMarkup:
    rows = []
    for value, label in (
        (MuscleGroup.chest.value, "Грудь"),
        (MuscleGroup.back.value, "Спина"),
        (MuscleGroup.shoulders.value, "Плечи"),
        (MuscleGroup.arms.value, "Руки"),
        (MuscleGroup.biceps.value, "Бицепс"),
        (MuscleGroup.triceps.value, "Трицепс"),
        (MuscleGroup.legs.value, "Ноги"),
        (MuscleGroup.abs.value, "Пресс"),
        (MuscleGroup.full_body.value, "Фулбоди"),
        (MuscleGroup.cardio.value, "Кардио"),
        (MuscleGroup.other.value, "Другое"),
    ):
        rows.append([InlineKeyboardButton(text=label, callback_data=f"collector_muscle:{value}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def exercise_type_kb() -> InlineKeyboardMarkup:
    rows = []
    for value, label in (
        (ExerciseType.weight_reps.value, "Вес + повторы"),
        (ExerciseType.bodyweight_reps.value, "Собственный вес"),
        (ExerciseType.timed.value, "По времени"),
        (ExerciseType.distance.value, "По дистанции"),
        (ExerciseType.cardio_machine.value, "Кардио-тренажёр"),
    ):
        rows.append([InlineKeyboardButton(text=label, callback_data=f"collector_ex_type:{value}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def moderation_kb(submission_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"collector_review:approve:{submission_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"collector_review:reject:{submission_id}",
                ),
            ]
        ]
    )
