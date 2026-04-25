"""Workout-specific keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.inline import back_to_menu_button
from bot.models.exercise import Exercise, MuscleGroup

# Order + labels for muscle-group picker. Keys must match MuscleGroup members.
MUSCLE_GROUP_LABELS: list[tuple[MuscleGroup, str]] = [
    (MuscleGroup.chest, "Грудь"),
    (MuscleGroup.back, "Спина"),
    (MuscleGroup.legs, "Ноги"),
    (MuscleGroup.shoulders, "Плечи"),
    (MuscleGroup.arms, "Руки"),
    (MuscleGroup.abs, "Пресс"),
    (MuscleGroup.full_body, "Всё тело"),
]

# Same data, keyed by enum value for back-lookup.
GROUP_LABEL = {g.value: label for g, label in MUSCLE_GROUP_LABELS}

# Primary-group picker for "custom exercise from Всё тело" fallback.
PRIMARY_GROUP_PICK: list[tuple[MuscleGroup, str]] = [
    (MuscleGroup.chest, "Грудь"),
    (MuscleGroup.back, "Спина"),
    (MuscleGroup.legs, "Ноги"),
    (MuscleGroup.shoulders, "Плечи"),
    (MuscleGroup.arms, "Руки"),
    (MuscleGroup.abs, "Пресс"),
]

EXERCISES_PER_PAGE = 6


def workout_section_kb() -> InlineKeyboardMarkup:
    """Top picker: warmup / gym / home / cooldown."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Разминка", callback_data="wsec:warmup")],
            [InlineKeyboardButton(text="🏋️ Зал", callback_data="wsec:gym")],
            [InlineKeyboardButton(text="🏠 Домашние упражнения", callback_data="wsec:home")],
            [InlineKeyboardButton(text="🧘 Заминка", callback_data="wsec:cooldown")],
            [back_to_menu_button()],
        ]
    )


# --- Legacy alias kept so the old callback name still compiles ---
def workout_type_kb() -> InlineKeyboardMarkup:
    return workout_section_kb()


def muscle_group_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for group, label in MUSCLE_GROUP_LABELS:
        pair.append(
            InlineKeyboardButton(text=label, callback_data=f"wmg:{group.value}")
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="wcat:back_section")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def exercise_catalog_kb(
    exercises: list[Exercise],
    *,
    has_more: bool,
    back_target: str = "groups",
    show_custom: bool = True,
) -> InlineKeyboardMarkup:
    """Generic paginated list picker.

    back_target="groups" (default) returns to the muscle-group picker —
    used for the gym section.  back_target="section" returns to the section
    picker — used for home/warmup/cooldown.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for ex in exercises:
        rows.append([
            InlineKeyboardButton(
                text=ex.name,
                callback_data=f"wex:{ex.id}",
            )
        ])
    if has_more:
        rows.append([
            InlineKeyboardButton(text="➡️ Ещё 6", callback_data="wcat:next")
        ])
    if show_custom:
        rows.append([
            InlineKeyboardButton(
                text="✍️ Ввести своё упражнение",
                callback_data="wcat:custom",
            )
        ])
    back_cb = "wcat:back_groups" if back_target == "groups" else "wcat:back_section"
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def empty_catalog_kb(back_target: str = "groups") -> InlineKeyboardMarkup:
    """Shown when a catalog has no exercises."""
    back_cb = "wcat:back_groups" if back_target == "groups" else "wcat:back_section"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✍️ Ввести своё упражнение",
                callback_data="wcat:custom",
            )],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)],
        ]
    )


def workout_start_kb() -> InlineKeyboardMarkup:
    """Back-to-menu button shown during free-text custom exercise entry."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[back_to_menu_button()]]
    )


def workout_back_kb() -> InlineKeyboardMarkup:
    """Universal 'Назад' for any workout input prompt.

    Routed through the ``wback:step`` callback which figures out the previous
    logical step from the current FSM state — so the same keyboard works from
    weight / reps / duration / extra-weight / name-input screens.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="wback:step")]
        ]
    )


def quick_set_input_kb() -> InlineKeyboardMarkup:
    """External-weight set prompt: quick input plus legacy step-by-step."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Ввести пошагово",
                    callback_data="workout:stepwise_set",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="wback:step")],
        ]
    )


def bodyweight_load_kb() -> InlineKeyboardMarkup:
    """Bodyweight exercise: ask about optional extra weight."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🪶 Без доп. веса", callback_data="wload:bw_only")],
            [InlineKeyboardButton(text="⚖️ Ввести доп. вес", callback_data="wload:bw_extra")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="wback:step")],
        ]
    )


def primary_group_pick_kb() -> InlineKeyboardMarkup:
    """Picker shown when a custom Full-Body exercise has no canonical match."""
    rows: list[list[InlineKeyboardButton]] = []
    pair: list[InlineKeyboardButton] = []
    for group, label in PRIMARY_GROUP_PICK:
        pair.append(
            InlineKeyboardButton(text=label, callback_data=f"wpg:{group.value}")
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="wback:step")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def set_action_kb() -> InlineKeyboardMarkup:
    """Between-sets controls."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё подход", callback_data="workout:add_set")],
            [InlineKeyboardButton(text="✅ Завершить упражнение", callback_data="workout:finish_exercise")],
            [InlineKeyboardButton(text="❌ Отменить последний подход", callback_data="workout:delete_last_set")],
        ]
    )


def exercise_summary_kb() -> InlineKeyboardMarkup:
    """Shown after the user finishes an exercise."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё упражнение", callback_data="workout:next_exercise")],
            [InlineKeyboardButton(text="🔁 Повторить это упражнение", callback_data="workout:repeat_exercise")],
            [InlineKeyboardButton(text="✅ Завершить тренировку", callback_data="workout:finish")],
            [InlineKeyboardButton(text="⬅️ К списку упражнений", callback_data="workout:back_to_catalog")],
        ]
    )


# --- Legacy alias for any call sites that still reference the old name -----
def workout_action_kb() -> InlineKeyboardMarkup:
    return set_action_kb()
