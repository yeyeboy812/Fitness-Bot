"""Profile and personalization handlers."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.profile import (
    body_composition_confirm_kb,
    profile_back_kb,
    profile_choice_kb,
    profile_confirm_kb,
    profile_kb,
)
from bot.models.user import ActivityLevel, Goal, User
from bot.repositories.user import UserRepository
from bot.services.body_composition import (
    BodyCompGender,
    BodyCompositionError,
    calculate_bmi,
    estimate_body_composition,
)
from bot.services.user import UserService
from bot.states.app import AppState

router = Router(name="profile")


GOAL_LABELS = {
    Goal.lose.value: "Похудеть",
    Goal.maintain.value: "Поддерживать вес",
    Goal.gain.value: "Набрать массу",
}

ACTIVITY_LABELS = {
    ActivityLevel.sedentary.value: "Сидячий образ жизни",
    ActivityLevel.light.value: "Лёгкая активность (1-2 тр/нед)",
    ActivityLevel.moderate.value: "Умеренная (3-5 тр/нед)",
    ActivityLevel.active.value: "Высокая (6-7 тр/нед)",
    ActivityLevel.very_active.value: "Очень высокая (2 раза/день)",
}

GENDER_LABELS = {
    "male": "Мужской",
    "female": "Женский",
}

FIELD_LABELS = {
    "first_name": "имя",
    "gender": "пол",
    "birth_year": "год рождения",
    "weight_kg": "вес",
    "height_cm": "рост",
    "goal": "цель",
    "activity_level": "активность",
}


async def open_profile(message: Message, state: FSMContext, user: User) -> None:
    await show_profile(message, state, user, edit=False)


async def show_profile(
    message: Message,
    state: FSMContext,
    user: User,
    *,
    edit: bool,
) -> None:
    await _show_profile(message, state, user, edit=edit)


def render_profile_text(user: User) -> str:
    lines = ["<b>👤 Профиль / Персонализация</b>", ""]
    lines.append(f"Имя: <b>{escape(user.first_name)}</b>")

    if user.birth_year is not None:
        age = date.today().year - user.birth_year
        lines.append(f"Год рождения / возраст: {user.birth_year} / {age}")
    if user.gender is not None:
        lines.append(f"Пол: {_enum_label(user.gender, GENDER_LABELS)}")
    if user.height_cm is not None:
        lines.append(f"Рост: {user.height_cm} см")
    if user.weight_kg is not None:
        lines.append(f"Вес: {_format_float(user.weight_kg)} кг")
    if user.goal is not None:
        lines.append(f"Цель: {_enum_label(user.goal, GOAL_LABELS)}")
    if user.activity_level is not None:
        lines.append(f"Активность: {_enum_label(user.activity_level, ACTIVITY_LABELS)}")

    lines.extend(["", "<b>Текущая норма</b>"])
    if user.calorie_norm is not None:
        lines.append(f"Калории: <b>{user.calorie_norm}</b> ккал")
    macros = []
    if user.protein_norm is not None:
        macros.append(f"Б {user.protein_norm} г")
    if user.fat_norm is not None:
        macros.append(f"Ж {user.fat_norm} г")
    if user.carb_norm is not None:
        macros.append(f"У {user.carb_norm} г")
    if macros:
        lines.append("БЖУ: " + " · ".join(macros))
    if user.body_fat_percent is not None and user.lean_mass_kg is not None:
        lines.extend(["", "<b>Состав тела</b>"])
        lines.append(f"Жир: {_format_float(user.body_fat_percent)}%")
        lines.append(f"Сухая масса: {_format_float(user.lean_mass_kg)} кг")
        if user.macro_basis_weight_kg is not None:
            lines.append(
                "Расчётная масса для БЖУ: "
                f"{_format_float(user.macro_basis_weight_kg)} кг"
            )

    return "\n".join(lines)


@router.callback_query(F.data.startswith("profile:edit:"))
async def on_profile_edit(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    field_key = callback.data.split(":", 2)[2]
    field = _field_name(field_key)
    if field is None:
        await callback.answer("Неизвестный параметр", show_alert=True)
        return

    await state.update_data(pending_profile_field=field)
    if field == "first_name":
        await callback.message.edit_text(
            "Введи новое имя (до 64 символов):",
            reply_markup=profile_back_kb(),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer()
        return
    if field == "gender":
        await callback.message.edit_text(
            "Выбери пол:",
            reply_markup=profile_choice_kb(field, list(GENDER_LABELS.items())),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer()
        return
    if field == "birth_year":
        await callback.message.edit_text(
            "Введи год рождения, например: <code>1995</code>",
            reply_markup=profile_back_kb(),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer()
        return
    if field == "weight_kg":
        await callback.message.edit_text(
            "Введи новый вес в кг, например: <code>75.5</code>",
            reply_markup=profile_back_kb(),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer()
        return
    if field == "height_cm":
        await callback.message.edit_text(
            "Введи новый рост в см, например: <code>180</code>",
            reply_markup=profile_back_kb(),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer()
        return
    if field == "goal":
        await callback.message.edit_text(
            "Выбери новую цель:",
            reply_markup=profile_choice_kb(field, list(GOAL_LABELS.items())),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer()
        return
    if field == "activity_level":
        await callback.message.edit_text(
            "Выбери новый уровень активности:",
            reply_markup=profile_choice_kb(field, list(ACTIVITY_LABELS.items())),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer()


@router.message(AppState.profile_value_input)
async def on_profile_value_input(
    message: Message,
    state: FSMContext,
    user: User,
) -> None:
    data = await state.get_data()
    field = data.get("pending_profile_field")
    if field == "first_name":
        value = _parse_name(message.text or "")
        if value is None:
            await message.answer(
                "Введи имя: непустая строка до 64 символов.",
                reply_markup=profile_back_kb(),
            )
            return
        await _show_confirm(message, state, user, field, value, edit=False)
        return
    if field == "birth_year":
        value = _parse_birth_year(message.text or "")
        if value is None:
            await message.answer(
                "Введи корректный год рождения: от 1940 до текущего года минус 10.",
                reply_markup=profile_back_kb(),
            )
            return
        await _show_confirm(message, state, user, field, value, edit=False)
        return
    if field == "weight_kg":
        value = _parse_weight(message.text or "")
        if value is None:
            await message.answer(
                "Введи вес числом в диапазоне 30-300 кг.",
                reply_markup=profile_back_kb(),
            )
            return
        await _show_confirm(message, state, user, field, value, edit=False)
        return
    if field == "height_cm":
        value = _parse_height(message.text or "")
        if value is None:
            await message.answer(
                "Введи рост целым числом в диапазоне 100-250 см.",
                reply_markup=profile_back_kb(),
            )
            return
        await _show_confirm(message, state, user, field, value, edit=False)
        return

    await message.answer("Выбери значение кнопкой ниже.", reply_markup=profile_back_kb())


@router.callback_query(AppState.profile_value_input, F.data.startswith("profile:value:"))
async def on_profile_choice(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    _, _, field, value = callback.data.split(":", 3)
    if field == "gender":
        if value not in GENDER_LABELS:
            await callback.answer("Неизвестный пол", show_alert=True)
            return
    elif field == "goal":
        if value not in GOAL_LABELS:
            await callback.answer("Неизвестная цель", show_alert=True)
            return
    elif field == "activity_level":
        if value not in ACTIVITY_LABELS:
            await callback.answer("Неизвестная активность", show_alert=True)
            return
    else:
        await callback.answer("Неизвестный параметр", show_alert=True)
        return

    await _show_confirm(callback.message, state, user, field, value, edit=True)
    await callback.answer()


@router.callback_query(F.data == "profile:body_comp:start")
async def on_body_composition_start(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    if user.gender is None or user.height_cm is None or user.weight_kg is None:
        await callback.answer(
            "Сначала заполни пол, рост и вес в профиле.",
            show_alert=True,
        )
        return

    await state.update_data(
        body_comp_neck_cm=None,
        body_comp_waist_cm=None,
        body_comp_hip_cm=None,
    )
    await callback.message.edit_text(
        "<b>📏 Состав тела / точный расчёт</b>\n\n"
        "Это примерная оценка, которая помогает точнее считать БЖУ при "
        "высоком текущем весе относительно роста.\n\n"
        "Введи обхват шеи в сантиметрах, например: <code>42</code>",
        reply_markup=profile_back_kb(),
    )
    await state.set_state(AppState.profile_body_neck_input)
    await callback.answer()


@router.message(AppState.profile_body_neck_input)
async def on_body_composition_neck(message: Message, state: FSMContext) -> None:
    neck_cm = _parse_measurement(message.text or "")
    if neck_cm is None:
        await message.answer(
            "Введи обхват шеи числом в сантиметрах, например: <code>42</code>",
            reply_markup=profile_back_kb(),
        )
        return
    await state.update_data(body_comp_neck_cm=neck_cm)
    await message.answer(
        "Введи обхват талии/живота в сантиметрах, например: <code>118</code>",
        reply_markup=profile_back_kb(),
    )
    await state.set_state(AppState.profile_body_waist_input)


@router.message(AppState.profile_body_waist_input)
async def on_body_composition_waist(
    message: Message,
    state: FSMContext,
    user: User,
) -> None:
    waist_cm = _parse_measurement(message.text or "")
    if waist_cm is None:
        await message.answer(
            "Введи обхват талии/живота числом в сантиметрах, например: <code>118</code>",
            reply_markup=profile_back_kb(),
        )
        return
    await state.update_data(body_comp_waist_cm=waist_cm)

    if _body_comp_gender(user) == BodyCompGender.female:
        await message.answer(
            "Введи обхват бёдер в сантиметрах, например: <code>112</code>",
            reply_markup=profile_back_kb(),
        )
        await state.set_state(AppState.profile_body_hip_input)
        return

    await _show_body_composition_result(message, state, user, edit=False)


@router.message(AppState.profile_body_hip_input)
async def on_body_composition_hip(
    message: Message,
    state: FSMContext,
    user: User,
) -> None:
    hip_cm = _parse_measurement(message.text or "")
    if hip_cm is None:
        await message.answer(
            "Введи обхват бёдер числом в сантиметрах, например: <code>112</code>",
            reply_markup=profile_back_kb(),
        )
        return
    await state.update_data(body_comp_hip_cm=hip_cm)
    await _show_body_composition_result(message, state, user, edit=False)


@router.callback_query(
    AppState.profile_body_confirm,
    F.data == "profile:body_comp:save",
)
async def on_body_composition_save(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    data = await state.get_data()
    result_data = data.get("body_comp_result")
    if not isinstance(result_data, dict):
        await callback.answer("Нет расчёта для сохранения", show_alert=True)
        return

    hip_value = data.get("body_comp_hip_cm")
    hip_cm = float(hip_value) if hip_value is not None else None
    updated_user = await UserService(UserRepository(session)).update_body_composition(
        user.id,
        neck_cm=float(data["body_comp_neck_cm"]),
        waist_cm=float(data["body_comp_waist_cm"]),
        hip_cm=hip_cm,
        result=estimate_body_composition(
            gender=_body_comp_gender(user),
            height_cm=user.height_cm,
            weight_kg=user.weight_kg,
            neck_cm=float(data["body_comp_neck_cm"]),
            waist_cm=float(data["body_comp_waist_cm"]),
            hip_cm=hip_cm,
        ),
    )
    await callback.answer("Сохранено")
    await _show_profile(callback.message, state, updated_user, edit=True)


@router.callback_query(F.data == "profile:body_comp:cancel")
async def on_body_composition_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    await callback.answer("Расчёт не сохранён")
    await _show_profile(callback.message, state, user, edit=True)


@router.callback_query(AppState.profile_confirm, F.data == "profile:save")
async def on_profile_save(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    data = await state.get_data()
    field = data.get("pending_profile_field")
    value = data.get("pending_profile_value")
    if not isinstance(field, str) or value is None:
        await callback.answer("Нет изменений для сохранения", show_alert=True)
        return

    updated_user = await UserService(UserRepository(session)).update_profile_field(
        user.id,
        field,
        value,
    )
    await callback.answer("Сохранено")
    await _show_profile(callback.message, state, updated_user, edit=True)


@router.callback_query(F.data == "profile:cancel")
async def on_profile_cancel(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    data = await state.get_data()
    if data.get("pending_goal_gain_warning"):
        await _clear_pending_profile_data(state)
        await state.update_data(pending_profile_field="goal")
        await callback.message.edit_text(
            "Выбери новую цель:",
            reply_markup=profile_choice_kb("goal", list(GOAL_LABELS.items())),
        )
        await state.set_state(AppState.profile_value_input)
        await callback.answer("Выбор не изменён")
        return

    await callback.answer("Изменение отменено")
    await _show_profile(callback.message, state, user, edit=True)


@router.callback_query(F.data == "profile:back")
async def on_profile_back(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await callback.answer()
    await _show_profile(callback.message, state, user, edit=True)


@router.callback_query(F.data == "profile:back_settings")
async def on_profile_back_settings(callback: CallbackQuery, state: FSMContext) -> None:
    from bot.handlers.settings import show_settings

    await show_settings(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(F.data == "profile:menu")
async def on_profile_menu(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    from bot.handlers.main_menu import _build_menu_markup, _render_menu_header

    await state.clear()
    text = await _render_menu_header(user, session, date.today())
    markup = await _build_menu_markup(user, session)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:  # noqa: BLE001
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


async def _show_profile(
    message: Message,
    state: FSMContext,
    user: User,
    *,
    edit: bool,
) -> None:
    await _clear_pending_profile_data(state)
    text = render_profile_text(user)
    if edit:
        try:
            await message.edit_text(text, reply_markup=profile_kb())
        except Exception:  # noqa: BLE001
            await message.answer(text, reply_markup=profile_kb())
    else:
        await message.answer(text, reply_markup=profile_kb())
    await state.set_state(AppState.viewing_profile)


async def _show_confirm(
    message: Message,
    state: FSMContext,
    user: User,
    field: str,
    value: Any,
    *,
    edit: bool,
) -> None:
    before = _display_field_value(user, field)
    after = _display_value(field, value)
    goal_gain_warning = _needs_goal_gain_warning(user, field, value)
    hint = _body_composition_hint(user, field, value)
    pending_data = {
        "pending_profile_field": field,
        "pending_profile_value": value,
    }
    if goal_gain_warning:
        pending_data["pending_goal_gain_warning"] = True
    await state.update_data(**pending_data)
    text = (
        f"Изменить {FIELD_LABELS[field]}?\n\n"
        f"Было: <b>{before}</b>\n"
        f"Стало: <b>{after}</b>"
    )
    if goal_gain_warning:
        text += (
            "\n\nПри текущем росте и весе набор массы может быть не лучшей целью. "
            "Чаще выбирают снижение веса или поддержание с силовыми тренировками. "
            "Всё равно выбрать набор массы?"
        )
    if hint:
        text += f"\n\n{hint}"
    if edit:
        await message.edit_text(text, reply_markup=profile_confirm_kb())
    else:
        await message.answer(text, reply_markup=profile_confirm_kb())
    await state.set_state(AppState.profile_confirm)


async def _clear_pending_profile_data(state: FSMContext) -> None:
    data = await state.get_data()
    changed = False
    for key in (
        "pending_profile_field",
        "pending_profile_value",
        "pending_goal_gain_warning",
        "body_comp_neck_cm",
        "body_comp_waist_cm",
        "body_comp_hip_cm",
        "body_comp_result",
    ):
        if key in data:
            data.pop(key)
            changed = True
    if changed:
        await state.set_data(data)


def _field_name(callback_key: str) -> str | None:
    return {
        "name": "first_name",
        "gender": "gender",
        "birth_year": "birth_year",
        "weight": "weight_kg",
        "height": "height_cm",
        "goal": "goal",
        "activity": "activity_level",
    }.get(callback_key)


def _parse_name(text: str) -> str | None:
    value = " ".join(text.strip().split())
    if not value or len(value) > 64:
        return None
    return value


def _parse_birth_year(text: str) -> int | None:
    try:
        value = int(text.strip())
    except ValueError:
        return None
    if not 1940 <= value <= date.today().year - 10:
        return None
    return value


def _parse_weight(text: str) -> float | None:
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    if not 30 <= value <= 300:
        return None
    return round(value, 1)


def _parse_height(text: str) -> int | None:
    try:
        value = int(text.strip())
    except ValueError:
        return None
    if not 100 <= value <= 250:
        return None
    return value


def _parse_measurement(text: str) -> float | None:
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    if value <= 0:
        return None
    return round(value, 1)


def _display_field_value(user: User, field: str) -> str:
    return _display_value(field, getattr(user, field))


def _display_value(field: str, value: Any) -> str:
    if value is None:
        return "не указано"
    if field == "weight_kg":
        return f"{_format_float(float(value))} кг"
    if field == "height_cm":
        return f"{value} см"
    if field == "gender":
        return _enum_label(value, GENDER_LABELS)
    if field == "birth_year":
        age = date.today().year - int(value)
        return f"{value} / {age}"
    if field == "goal":
        return _enum_label(value, GOAL_LABELS)
    if field == "activity_level":
        return _enum_label(value, ACTIVITY_LABELS)
    return str(value)


async def _show_body_composition_result(
    message: Message,
    state: FSMContext,
    user: User,
    *,
    edit: bool,
) -> None:
    data = await state.get_data()
    try:
        result = estimate_body_composition(
            gender=_body_comp_gender(user),
            height_cm=user.height_cm,
            weight_kg=user.weight_kg,
            neck_cm=float(data["body_comp_neck_cm"]),
            waist_cm=float(data["body_comp_waist_cm"]),
            hip_cm=data.get("body_comp_hip_cm"),
        )
    except (BodyCompositionError, KeyError, TypeError, ValueError) as exc:
        await message.answer(
            f"Не получилось рассчитать состав тела: {escape(str(exc))}",
            reply_markup=profile_back_kb(),
        )
        return

    await state.update_data(
        body_comp_result={
            "body_fat_percent": result.body_fat_percent,
            "lean_mass_kg": result.lean_mass_kg,
            "macro_basis_weight_kg": result.macro_basis_weight_kg,
            "method": result.method,
        }
    )
    text = (
        "Примерная оценка:\n"
        f"Жир: <b>{_format_float(result.body_fat_percent)}%</b>\n"
        f"Сухая масса: <b>{_format_float(result.lean_mass_kg)} кг</b>\n"
        "Для БЖУ используем расчётную массу: "
        f"<b>{_format_float(result.macro_basis_weight_kg)} кг</b>\n\n"
        "Сохранить замеры и пересчитать норму?"
    )
    if edit:
        await message.edit_text(text, reply_markup=body_composition_confirm_kb())
    else:
        await message.answer(text, reply_markup=body_composition_confirm_kb())
    await state.set_state(AppState.profile_body_confirm)


def _body_comp_gender(user: User) -> BodyCompGender:
    raw = user.gender.value if hasattr(user.gender, "value") else str(user.gender)
    return BodyCompGender(raw)


def _has_body_composition(user: User) -> bool:
    return (
        user.body_fat_percent is not None
        and user.lean_mass_kg is not None
        and user.macro_basis_weight_kg is not None
    )


def _is_high_bmi(user: User, *, weight_kg: float | None = None) -> bool:
    weight = weight_kg if weight_kg is not None else user.weight_kg
    if weight is None or user.height_cm is None:
        return False
    try:
        return calculate_bmi(float(weight), user.height_cm) >= 30
    except BodyCompositionError:
        return False


def _body_composition_hint(user: User, field: str, value: Any) -> str | None:
    if field not in {"goal", "weight_kg"} or _has_body_composition(user):
        return None
    weight = float(value) if field == "weight_kg" else None
    if not _is_high_bmi(user, weight_kg=weight):
        return None
    return (
        "Чтобы БЖУ не получились завышенными, можно добавить замеры тела "
        "в разделе «Состав тела / точный расчёт»."
    )


def _needs_goal_gain_warning(user: User, field: str, value: Any) -> bool:
    if field != "goal":
        return False
    raw = value.value if hasattr(value, "value") else str(value)
    return raw == Goal.gain.value and _is_high_bmi(user)


def _enum_label(value: Any, labels: dict[str, str]) -> str:
    raw = value.value if hasattr(value, "value") else str(value)
    return labels.get(raw, raw)


def _format_float(value: float) -> str:
    if abs(value - int(value)) < 1e-6:
        return str(int(value))
    return f"{value:.1f}"
