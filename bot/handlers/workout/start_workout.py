"""Workout session handlers — section picker, logging, finish.

Flow:
    open_workout → section picker (warmup/gym/home/cooldown) →
    muscle-group picker (gym only) → exercise catalog →
    per-mode set entry → between-sets actions → exercise summary →
    finish workout.

Section / group / exercise picking calls live on top; the "log a set"
handlers sit in the middle; workout-finish and summary are at the bottom.
"""

from datetime import date, datetime, timezone
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.menu import NotMainMenuFilter
from bot.keyboards.reply import MAIN_MENU
from bot.keyboards.workout import (
    EXERCISES_PER_PAGE,
    GROUP_LABEL,
    bodyweight_load_kb,
    empty_catalog_kb,
    exercise_catalog_kb,
    exercise_summary_kb,
    muscle_group_kb,
    primary_group_pick_kb,
    set_action_kb,
    workout_back_kb,
    workout_section_kb,
)
from bot.models.exercise import (
    LOAD_BW_OPT_EXTRA,
    LOAD_EXTERNAL,
    LOAD_NO_WEIGHT,
    LOAD_TIME_ONLY,
    LOG_MODE_REPS,
    LOG_MODE_TIME,
    SECTION_COOLDOWN,
    SECTION_GYM,
    SECTION_HOME,
    SECTION_WARMUP,
    Exercise,
    ExerciseType,
    MuscleGroup,
)
from bot.models.user import User
from bot.repositories.exercise import ExerciseRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.workout import WorkoutService, estimate_calories_burned
from bot.states.app import AppState

router = Router(name="start_workout")

# Curated catalogs — ordered lists of canonical names resolved at render time.
# Full Body in Gym is a reference list pointing at canonical gym rows — no
# dedicated seed rows. Names here must match canonical exercise names exactly.
FULL_BODY_CURATED: list[str] = [
    "Становая тяга",
    "Жим штанги лёжа",
    "Подтягивания",
    "Приседания со штангой",
    "Подъём штанги на бицепс",
    "Махи гантелями в стороны",
]

HOME_CURATED: list[str] = [
    "Подтягивания",
    "Отжимания",
    "Приседания",
    "Скручивания",
    "Берпи",
    "Планка",
    "Обратные отжимания",
    "Выпады",
    "Подъём ног лёжа",
    "Альпинист",
]

WARMUP_CURATED: list[str] = [
    "Прыжки на месте",
    "Вращения руками",
    "Махи руками",
    "Приседания без веса",
    "Выпады без веса",
    "Планка",
    "Суставная разминка",
    "Бег на месте",
]

COOLDOWN_CURATED: list[str] = [
    "Растяжка груди",
    "Растяжка спины",
    "Растяжка ног",
    "Растяжка плеч",
    "Наклоны вперёд",
    "Дыхательное восстановление",
    "Ходьба",
    "Растяжка всего тела",
]

SECTION_CURATED: dict[str, list[str]] = {
    SECTION_HOME: HOME_CURATED,
    SECTION_WARMUP: WARMUP_CURATED,
    SECTION_COOLDOWN: COOLDOWN_CURATED,
}

SECTION_LABEL: dict[str, str] = {
    SECTION_WARMUP: "🔥 Разминка",
    SECTION_GYM: "🏋️ Зал",
    SECTION_HOME: "🏠 Домашние упражнения",
    SECTION_COOLDOWN: "🧘 Заминка",
}

# Defaults for custom exercises created inside a non-gym section.
SECTION_CUSTOM_DEFAULTS: dict[str, tuple[str, str, ExerciseType]] = {
    SECTION_HOME: (LOG_MODE_REPS, LOAD_BW_OPT_EXTRA, ExerciseType.bodyweight_reps),
    SECTION_WARMUP: (LOG_MODE_REPS, LOAD_NO_WEIGHT, ExerciseType.bodyweight_reps),
    SECTION_COOLDOWN: (LOG_MODE_TIME, LOAD_TIME_ONLY, ExerciseType.timed),
}


# States that accept free-text input or keep workout data in FSM — text typed
# here must be intercepted for "назад" / "меню" global nav before the regular
# input handlers parse it as a name/weight/reps value.
_WORKOUT_NAV_STATES = (
    AppState.workout_type_select,
    AppState.workout_muscle_group_select,
    AppState.workout_exercise_select,
    AppState.workout_name_input,
    AppState.workout_fullbody_group_pick,
    AppState.workout_load_choice,
    AppState.workout_weight_input,
    AppState.workout_extra_weight_input,
    AppState.workout_reps_input,
    AppState.workout_duration_input,
    AppState.workout_in_progress,
    AppState.workout_exercise_summary,
)


async def _send_view(
    target: Message, text: str, kb, *, edit: bool
) -> None:
    """Render a view either by editing an existing bot message or sending new.

    ``edit=True`` is used when the navigation originates from a callback
    (``callback.message`` can be edited in-place). ``edit=False`` is used for
    plain-text navigation where ``target`` is the user's message and we must
    send a fresh reply. Falls back to ``answer`` if edit fails (stale msg).
    """
    if edit:
        try:
            await target.edit_text(text, reply_markup=kb)
            return
        except Exception:  # noqa: BLE001
            pass
    await target.answer(text, reply_markup=kb)


async def _show_load_choice(
    target: Message, state: FSMContext, user: User, *, edit: bool
) -> None:
    bw = user.weight_kg or 0
    hint = f"\nВес тела из профиля: <b>{bw:.0f} кг</b>" if bw else ""
    await _send_view(
        target, "Как логируем этот подход?" + hint, bodyweight_load_kb(), edit=edit
    )
    await state.set_state(AppState.workout_load_choice)


async def _rerender_catalog(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    *,
    edit: bool,
) -> None:
    """Return user to the exercise catalog they came from (gym group / curated section)."""
    data = await state.get_data()
    section = data.get("current_section") or SECTION_GYM
    group_value = data.get("current_group")

    if section == SECTION_GYM and group_value:
        try:
            group = MuscleGroup(group_value)
        except ValueError:
            group = None
        if group is MuscleGroup.full_body:
            await _render_full_body_catalog(target, state, session, user, edit=edit)
            return
        if group is not None:
            await _render_catalog_page(
                target, state, session, user, group, page=0, edit=edit
            )
            return

    if section != SECTION_GYM:
        await _render_curated_section(target, state, session, user, section, edit=edit)
        return

    # Fallback — section picker.
    await _send_view(
        target, "Выбери раздел тренировки:", workout_section_kb(), edit=edit
    )
    await state.set_state(AppState.workout_type_select)


async def _navigate_back(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    *,
    edit: bool,
) -> None:
    """Route the user one logical step back based on current FSM state."""
    current = await state.get_state()
    data = await state.get_data()

    if current == AppState.workout_fullbody_group_pick.state:
        await state.update_data(pending_custom_name=None)
        await _send_view(
            target, "Введи название упражнения:", workout_back_kb(), edit=edit
        )
        await state.set_state(AppState.workout_name_input)
        return

    if current == AppState.workout_name_input.state:
        await _rerender_catalog(target, state, session, user, edit=edit)
        return

    if current in (
        AppState.workout_load_choice.state,
        AppState.workout_weight_input.state,
        AppState.workout_duration_input.state,
    ):
        await _rerender_catalog(target, state, session, user, edit=edit)
        return

    if current == AppState.workout_extra_weight_input.state:
        await _show_load_choice(target, state, user, edit=edit)
        return

    if current == AppState.workout_reps_input.state:
        load_mode = data.get("current_load_mode")
        if load_mode == LOAD_EXTERNAL:
            await _send_view(
                target,
                "Введи вес (кг), например: <code>60</code>",
                workout_back_kb(),
                edit=edit,
            )
            await state.set_state(AppState.workout_weight_input)
            return
        if load_mode == LOAD_BW_OPT_EXTRA:
            pending_extra = data.get("pending_extra")
            if pending_extra is not None and float(pending_extra) > 0:
                await _send_view(
                    target,
                    "Введи доп. вес в кг (например: <code>10</code>):",
                    workout_back_kb(),
                    edit=edit,
                )
                await state.set_state(AppState.workout_extra_weight_input)
                return
            await _show_load_choice(target, state, user, edit=edit)
            return
        await _rerender_catalog(target, state, session, user, edit=edit)
        return

    if current == AppState.workout_exercise_select.state:
        section = data.get("current_section") or SECTION_GYM
        if section == SECTION_GYM:
            await _send_view(
                target, "Выбери группу мышц:", muscle_group_kb(), edit=edit
            )
            await state.set_state(AppState.workout_muscle_group_select)
        else:
            await _send_view(
                target, "Выбери раздел тренировки:", workout_section_kb(), edit=edit
            )
            await state.set_state(AppState.workout_type_select)
        return

    if current == AppState.workout_muscle_group_select.state:
        await _send_view(
            target, "Выбери раздел тренировки:", workout_section_kb(), edit=edit
        )
        await state.set_state(AppState.workout_type_select)
        return

    if current == AppState.workout_type_select.state:
        # First step — back exits to main menu (same as the keyboard's own back).
        from bot.keyboards.inline import main_menu_kb  # lazy: avoid circular import

        await state.clear()
        await target.answer("🎯 Меню:", reply_markup=main_menu_kb(user.id))
        return

    # Fallback — section picker.
    await _send_view(
        target, "Выбери раздел тренировки:", workout_section_kb(), edit=edit
    )
    await state.set_state(AppState.workout_type_select)


# ---------------------------------------------------------------------------
# Section entry point
# ---------------------------------------------------------------------------
async def open_workout(message: Message, state: FSMContext) -> None:
    await state.update_data(
        exercises=[],
        workout_started_at=datetime.now(timezone.utc).isoformat(),
    )
    await message.answer(
        "Начинаем тренировку!\nВыбери раздел:",
        reply_markup=workout_section_kb(),
    )
    await state.set_state(AppState.workout_type_select)


@router.message(Command("workout"))
async def cmd_start_workout(message: Message, state: FSMContext) -> None:
    await open_workout(message, state)


# ---------------------------------------------------------------------------
# Universal navigation: "⬅️ Назад" callback + plain-text "назад" / "меню"
# ---------------------------------------------------------------------------
# These two handlers are intentionally registered BEFORE any state-bound input
# handler (on_custom_exercise_name, on_weight_input, ...). NotMainMenuFilter
# only rejects the exact "🎯 Меню" reply label — plain text "назад"/"меню"
# would otherwise be parsed as a name/weight/reps value.
@router.callback_query(F.data == "wback:step")
async def on_wback_step(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    await _navigate_back(callback.message, state, session, user, edit=True)
    await callback.answer()


@router.message(
    StateFilter(*_WORKOUT_NAV_STATES),
    F.text.func(lambda t: isinstance(t, str) and t.strip().lower() in {"назад", "меню"}),
)
async def on_workout_text_nav(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    word = (message.text or "").strip().lower()
    if word == "меню":
        # Mirror the reply "🎯 Меню" button: open the inline picker without
        # clearing scenario state — the interruptible-state confirm fires only
        # when the user actually picks an action.
        from bot.handlers.main_menu import _render_menu_header  # lazy: circular
        from bot.keyboards.inline import main_menu_kb  # lazy: circular

        header = await _render_menu_header(user, session, date.today())
        await message.answer(header, reply_markup=main_menu_kb(user.id))
        return
    await _navigate_back(message, state, session, user, edit=False)


# ---------------------------------------------------------------------------
# Section pick
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_type_select, F.data.startswith("wsec:"))
async def on_pick_section(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    section = callback.data.split(":", 1)[1]
    if section not in SECTION_LABEL:
        await callback.answer("Неизвестный раздел", show_alert=True)
        return

    await state.update_data(current_section=section, current_group=None, current_page=0)

    if section == SECTION_GYM:
        await callback.message.edit_text(
            "Выбери группу мышц:",
            reply_markup=muscle_group_kb(),
        )
        await state.set_state(AppState.workout_muscle_group_select)
        await callback.answer()
        return

    # Home / warmup / cooldown → flat curated catalog.
    await _render_curated_section(
        callback.message, state, session, user, section, edit=True
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Gym: muscle-group pick
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_muscle_group_select, F.data.startswith("wmg:"))
async def on_pick_muscle_group(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    group_value = callback.data.split(":", 1)[1]
    try:
        group = MuscleGroup(group_value)
    except ValueError:
        await callback.answer("Неизвестная группа", show_alert=True)
        return

    await state.update_data(current_group=group.value, current_page=0)

    if group is MuscleGroup.full_body:
        await _render_full_body_catalog(
            callback.message, state, session, user, edit=True
        )
        await callback.answer()
        return

    await _render_catalog_page(
        callback.message, state, session, user, group, page=0, edit=True
    )
    await callback.answer()


async def _render_catalog_page(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    group: MuscleGroup,
    *,
    page: int,
    edit: bool,
) -> None:
    repo = ExerciseRepository(session)
    total = await repo.count_by_muscle_group(group, user.id)
    if total == 0:
        await _send_view(
            target,
            f"{GROUP_LABEL.get(group.value, group.value)}: упражнений пока нет.\n"
            "Ты можешь ввести своё:",
            empty_catalog_kb(back_target="groups"),
            edit=edit,
        )
        await state.set_state(AppState.workout_exercise_select)
        return

    total_pages = max(1, (total + EXERCISES_PER_PAGE - 1) // EXERCISES_PER_PAGE)
    page = page % total_pages
    offset = page * EXERCISES_PER_PAGE
    items = await repo.list_by_muscle_group(
        muscle_group=group,
        user_id=user.id,
        limit=EXERCISES_PER_PAGE,
        offset=offset,
    )
    has_more = total_pages > 1

    await state.update_data(current_page=page)
    label = GROUP_LABEL.get(group.value, group.value)
    page_marker = f" ({page + 1}/{total_pages})" if total_pages > 1 else ""
    await _send_view(
        target,
        f"<b>{label}</b>{page_marker}\nВыбери упражнение:",
        exercise_catalog_kb(items, has_more=has_more, back_target="groups"),
        edit=edit,
    )
    await state.set_state(AppState.workout_exercise_select)


async def _render_full_body_catalog(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    *,
    edit: bool,
) -> None:
    repo = ExerciseRepository(session)
    items = await repo.list_by_names(FULL_BODY_CURATED, user_id=user.id)
    if not items:
        await _send_view(
            target,
            "Всё тело: каталог пока не засеян.\nТы можешь ввести своё упражнение:",
            empty_catalog_kb(back_target="groups"),
            edit=edit,
        )
        await state.set_state(AppState.workout_exercise_select)
        return

    await _send_view(
        target,
        "<b>Всё тело</b>\nВыбери упражнение:",
        exercise_catalog_kb(items, has_more=False, back_target="groups"),
        edit=edit,
    )
    await state.set_state(AppState.workout_exercise_select)


async def _render_curated_section(
    target: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
    section: str,
    *,
    edit: bool,
) -> None:
    """Render home/warmup/cooldown as a flat curated list."""
    curated = SECTION_CURATED.get(section, [])
    repo = ExerciseRepository(session)
    items = await repo.list_by_names(curated, user_id=user.id)
    label = SECTION_LABEL.get(section, section)
    if not items:
        await _send_view(
            target,
            f"{label}: каталог пока не засеян.\nТы можешь ввести своё упражнение:",
            empty_catalog_kb(back_target="section"),
            edit=edit,
        )
        await state.set_state(AppState.workout_exercise_select)
        return

    await _send_view(
        target,
        f"<b>{label}</b>\nВыбери упражнение:",
        exercise_catalog_kb(items, has_more=False, back_target="section"),
        edit=edit,
    )
    await state.set_state(AppState.workout_exercise_select)


# ---------------------------------------------------------------------------
# Catalog pagination / back / custom
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_exercise_select, F.data == "wcat:next")
async def on_catalog_next(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    data = await state.get_data()
    group_value = data.get("current_group")
    page = int(data.get("current_page") or 0)
    if not group_value:
        await callback.answer()
        return
    try:
        group = MuscleGroup(group_value)
    except ValueError:
        await callback.answer()
        return
    await _render_catalog_page(
        callback.message, state, session, user, group, page=page + 1, edit=True
    )
    await callback.answer()


@router.callback_query(AppState.workout_exercise_select, F.data == "wcat:back_groups")
async def on_catalog_back_to_groups(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await callback.message.edit_text(
        "Выбери группу мышц:",
        reply_markup=muscle_group_kb(),
    )
    await state.set_state(AppState.workout_muscle_group_select)
    await callback.answer()


@router.callback_query(
    AppState.workout_exercise_select, F.data == "wcat:back_section"
)
@router.callback_query(
    AppState.workout_muscle_group_select, F.data == "wcat:back_section"
)
async def on_catalog_back_to_section(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await callback.message.edit_text(
        "Выбери раздел тренировки:",
        reply_markup=workout_section_kb(),
    )
    await state.set_state(AppState.workout_type_select)
    await callback.answer()


@router.callback_query(AppState.workout_exercise_select, F.data == "wcat:custom")
async def on_catalog_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Введи название упражнения:",
        reply_markup=workout_back_kb(),
    )
    await state.set_state(AppState.workout_name_input)
    await callback.answer()


# ---------------------------------------------------------------------------
# Exercise pick → dispatch into the right entry state
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_exercise_select, F.data.startswith("wex:"))
async def on_pick_exercise(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    raw_id = callback.data.split(":", 1)[1]
    try:
        exercise_id = UUID(raw_id)
    except ValueError:
        await callback.answer("Некорректное упражнение", show_alert=True)
        return

    repo = ExerciseRepository(session)
    exercise = await repo.get_by_id(exercise_id)
    if exercise is None or (
        exercise.user_id is not None and exercise.user_id != user.id
    ):
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    await _begin_exercise(callback, state, user, exercise)


async def _begin_exercise(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    exercise: Exercise,
) -> None:
    """Store current_exercise_* in FSM and route to the first input state."""
    await state.update_data(
        current_exercise_id=str(exercise.id),
        current_exercise=exercise.name,
        current_log_mode=exercise.log_mode,
        current_load_mode=exercise.load_mode,
        sets=[],
        pending_weight=None,
        pending_extra=None,
        pending_bw_snapshot=None,
        pending_duration=None,
    )
    await _prompt_next_set_input(callback.message, state, user, is_first_set=True)
    await callback.answer()


async def _prompt_next_set_input(
    message: Message,
    state: FSMContext,
    user: User,
    *,
    is_first_set: bool,
) -> None:
    """Send the first prompt for a new set, matching the exercise's modes."""
    data = await state.get_data()
    name = data.get("current_exercise", "Упражнение")
    log_mode = data.get("current_log_mode")
    load_mode = data.get("current_load_mode")

    header = f"Упражнение: <b>{name}</b>\n\n" if is_first_set else ""

    if log_mode == LOG_MODE_TIME:
        await message.answer(
            header
            + "Введи длительность подхода (например: <code>60</code> сек или <code>1:30</code>):",
            reply_markup=workout_back_kb(),
        )
        await state.set_state(AppState.workout_duration_input)
        return

    if load_mode == LOAD_EXTERNAL:
        await message.answer(
            header + "Введи вес (кг), например: <code>60</code>",
            reply_markup=workout_back_kb(),
        )
        await state.set_state(AppState.workout_weight_input)
        return

    if load_mode == LOAD_BW_OPT_EXTRA:
        bw = user.weight_kg or 0
        hint = f"\nВес тела из профиля: <b>{bw:.0f} кг</b>" if bw else ""
        await message.answer(
            header + "Как логируем этот подход?" + hint,
            reply_markup=bodyweight_load_kb(),
        )
        await state.set_state(AppState.workout_load_choice)
        return

    # LOAD_NO_WEIGHT — straight to reps.
    await message.answer(
        header + "Введи количество повторений (например: <code>12</code>)",
        reply_markup=workout_back_kb(),
    )
    await state.set_state(AppState.workout_reps_input)


# ---------------------------------------------------------------------------
# Custom exercise name
# ---------------------------------------------------------------------------
@router.message(AppState.workout_name_input, NotMainMenuFilter())
async def on_custom_exercise_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer(
            "Введи название упражнения:", reply_markup=workout_back_kb()
        )
        return
    if len(name) > 120:
        await message.answer(
            "Слишком длинное название (до 120 символов).",
            reply_markup=workout_back_kb(),
        )
        return

    data = await state.get_data()
    section = data.get("current_section") or SECTION_GYM
    group_value = data.get("current_group") or MuscleGroup.other.value
    try:
        group = MuscleGroup(group_value)
    except ValueError:
        group = MuscleGroup.other

    repo = ExerciseRepository(session)

    # Try to reuse an existing exercise (canonical or personal) by normalized name.
    existing = await repo.find_by_name(name, user_id=user.id)
    if existing is not None:
        await _begin_exercise_from_message(message, state, user, existing)
        return

    # Full Body + unknown name → ask for primary muscle group before creating.
    if group is MuscleGroup.full_body and section == SECTION_GYM:
        await state.update_data(pending_custom_name=name)
        await message.answer(
            f"Я не нашёл «{name}» в каталоге.\nВыбери основную группу мышц:",
            reply_markup=primary_group_pick_kb(),
        )
        await state.set_state(AppState.workout_fullbody_group_pick)
        return

    # Gym + known group / home / warmup / cooldown → create personal exercise.
    if section == SECTION_GYM:
        log_mode, load_mode, etype = LOG_MODE_REPS, LOAD_EXTERNAL, ExerciseType.weight_reps
    else:
        log_mode, load_mode, etype = SECTION_CUSTOM_DEFAULTS[section]

    exercise = await repo.create_personal(
        name=name,
        user_id=user.id,
        muscle_group=group,
        exercise_type=etype,
        section=section,
        log_mode=log_mode,
        load_mode=load_mode,
    )
    await _begin_exercise_from_message(message, state, user, exercise)


async def _begin_exercise_from_message(
    message: Message,
    state: FSMContext,
    user: User,
    exercise: Exercise,
) -> None:
    """Same as _begin_exercise but triggered from a text message handler."""
    await state.update_data(
        current_exercise_id=str(exercise.id),
        current_exercise=exercise.name,
        current_log_mode=exercise.log_mode,
        current_load_mode=exercise.load_mode,
        sets=[],
        pending_weight=None,
        pending_extra=None,
        pending_bw_snapshot=None,
        pending_duration=None,
    )
    await message.answer(f"Упражнение: <b>{exercise.name}</b>")
    await _prompt_next_set_input(message, state, user, is_first_set=False)


# ---------------------------------------------------------------------------
# Full Body custom name: pick primary muscle group, create, continue.
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_fullbody_group_pick, F.data.startswith("wpg:"))
async def on_fullbody_group_pick(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    group_value = callback.data.split(":", 1)[1]
    try:
        group = MuscleGroup(group_value)
    except ValueError:
        await callback.answer("Неизвестная группа", show_alert=True)
        return
    data = await state.get_data()
    name = (data.get("pending_custom_name") or "").strip()
    if not name:
        await callback.answer("Введи название заново", show_alert=True)
        await state.set_state(AppState.workout_name_input)
        return

    repo = ExerciseRepository(session)
    exercise = await repo.create_personal(
        name=name,
        user_id=user.id,
        muscle_group=group,
        exercise_type=ExerciseType.weight_reps,
        section=SECTION_GYM,
        log_mode=LOG_MODE_REPS,
        load_mode=LOAD_EXTERNAL,
    )
    await state.update_data(pending_custom_name=None)
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await _begin_exercise_from_message(callback.message, state, user, exercise)
    await callback.answer()


# ---------------------------------------------------------------------------
# Bodyweight load choice
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_load_choice, F.data == "wload:bw_only")
async def on_bw_only(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    bw = float(user.weight_kg or 0.0)
    await state.update_data(
        pending_weight=None,
        pending_extra=0.0,
        pending_bw_snapshot=bw,
    )
    await callback.message.edit_text(
        "Без доп. веса.\nВведи количество повторений (например: <code>12</code>)",
        reply_markup=workout_back_kb(),
    )
    await state.set_state(AppState.workout_reps_input)
    await callback.answer()


@router.callback_query(AppState.workout_load_choice, F.data == "wload:bw_extra")
async def on_bw_extra(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Введи доп. вес в кг (например: <code>10</code>):",
        reply_markup=workout_back_kb(),
    )
    await state.set_state(AppState.workout_extra_weight_input)
    await callback.answer()


# ---------------------------------------------------------------------------
# Input states
# ---------------------------------------------------------------------------
def _parse_float(text: str) -> float | None:
    try:
        return float(text.replace(",", ".").strip())
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except ValueError:
        return None


def _parse_duration(text: str) -> int | None:
    """Accept '60', '60s', '1:30', '1м 30с' → seconds. None on parse error."""
    t = text.strip().lower()
    if ":" in t:
        parts = t.split(":")
        if len(parts) == 2:
            m = _parse_int(parts[0])
            s = _parse_int(parts[1])
            if m is not None and s is not None and m >= 0 and 0 <= s < 60:
                return m * 60 + s
        return None
    digits = "".join(ch for ch in t if ch.isdigit())
    if not digits:
        return None
    n = int(digits)
    return n if n > 0 else None


@router.message(AppState.workout_weight_input, NotMainMenuFilter())
async def on_weight_input(
    message: Message, state: FSMContext, user: User
) -> None:
    val = _parse_float(message.text or "")
    if val is None or val < 0:
        await message.answer(
            "Введи вес числом, например: <code>60</code>",
            reply_markup=workout_back_kb(),
        )
        return
    await state.update_data(pending_weight=val)
    await message.answer(
        "Введи количество повторений:", reply_markup=workout_back_kb()
    )
    await state.set_state(AppState.workout_reps_input)


@router.message(AppState.workout_extra_weight_input, NotMainMenuFilter())
async def on_extra_weight_input(
    message: Message, state: FSMContext, user: User
) -> None:
    val = _parse_float(message.text or "")
    if val is None or val < 0:
        await message.answer(
            "Введи доп. вес числом, например: <code>10</code>",
            reply_markup=workout_back_kb(),
        )
        return
    bw = float(user.weight_kg or 0.0)
    await state.update_data(
        pending_extra=val,
        pending_bw_snapshot=bw,
    )
    await message.answer(
        "Введи количество повторений:", reply_markup=workout_back_kb()
    )
    await state.set_state(AppState.workout_reps_input)


@router.message(AppState.workout_reps_input, NotMainMenuFilter())
async def on_reps_input(message: Message, state: FSMContext, user: User) -> None:
    reps = _parse_int(message.text or "")
    if reps is None or reps <= 0:
        await message.answer(
            "Введи количество повторений числом, например: <code>12</code>",
            reply_markup=workout_back_kb(),
        )
        return
    await _save_set_and_show_action(message, state, reps=reps, duration=None)


@router.message(AppState.workout_duration_input, NotMainMenuFilter())
async def on_duration_input(message: Message, state: FSMContext, user: User) -> None:
    seconds = _parse_duration(message.text or "")
    if seconds is None or seconds <= 0:
        await message.answer(
            "Формат: <code>60</code> (секунды) или <code>1:30</code> (мм:сс)",
            reply_markup=workout_back_kb(),
        )
        return
    await _save_set_and_show_action(message, state, reps=None, duration=seconds)


# ---------------------------------------------------------------------------
# Save set into FSM + show set action kb
# ---------------------------------------------------------------------------
def _format_duration(seconds: int) -> str:
    if seconds >= 60:
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"
    return f"{int(seconds)} сек"


def _format_weight(value: float) -> str:
    if abs(value - int(value)) < 1e-6:
        return f"{int(value)}"
    return f"{value:.1f}"


def _render_set_line(s: dict, *, index: int) -> str:
    load_mode = s.get("load_mode")
    reps = s.get("reps")
    duration = s.get("duration")
    eff = s.get("effective_weight")

    if load_mode == LOAD_TIME_ONLY or duration:
        return f"  {index}. {_format_duration(int(duration or 0))}"
    if load_mode == LOAD_NO_WEIGHT:
        return f"  {index}. {reps} повт."
    if load_mode == LOAD_BW_OPT_EXTRA:
        extra = s.get("extra_weight") or 0.0
        bw = s.get("user_body_weight_snapshot") or 0.0
        eff_str = _format_weight(float(eff or (bw + extra)))
        if extra and extra > 0:
            return f"  {index}. {eff_str}кг (тело+{_format_weight(extra)}) × {reps}"
        if bw:
            return f"  {index}. {eff_str}кг (вес тела) × {reps}"
        return f"  {index}. × {reps}"
    # external weight
    w = eff if eff is not None else s.get("weight")
    return f"  {index}. {_format_weight(float(w or 0))}кг × {reps}"


async def _save_set_and_show_action(
    message: Message,
    state: FSMContext,
    *,
    reps: int | None,
    duration: int | None,
) -> None:
    data = await state.get_data()
    load_mode = data.get("current_load_mode") or LOAD_EXTERNAL

    pending_weight = data.get("pending_weight")
    pending_extra = data.get("pending_extra")
    bw_snapshot = data.get("pending_bw_snapshot")

    effective: float | None
    if load_mode == LOAD_EXTERNAL:
        effective = float(pending_weight or 0.0)
    elif load_mode == LOAD_BW_OPT_EXTRA:
        bw = float(bw_snapshot or 0.0)
        extra = float(pending_extra or 0.0)
        effective = bw + extra
    else:
        effective = None

    set_entry = {
        "load_mode": load_mode,
        "reps": reps,
        "duration": duration,
        "weight": pending_weight,
        "extra_weight": pending_extra,
        "user_body_weight_snapshot": bw_snapshot,
        "effective_weight": effective,
    }

    sets = data.get("sets", [])
    sets.append(set_entry)
    await state.update_data(
        sets=sets,
        pending_weight=None,
        pending_extra=None,
        pending_bw_snapshot=None,
    )

    confirm = "Подход сохранён: " + _render_set_line(set_entry, index=len(sets)).strip()
    # Replace leading "N. " numbering with plain content for the confirmation line.
    confirm_payload = confirm.split(". ", 1)[-1]
    await message.answer(
        f"✅ Подход сохранён: {confirm_payload}\n\n"
        f"<b>{data['current_exercise']}</b>\n"
        + "\n".join(_render_set_line(s, index=i + 1) for i, s in enumerate(sets)),
        reply_markup=set_action_kb(),
    )
    await state.set_state(AppState.workout_in_progress)


# ---------------------------------------------------------------------------
# Between-sets actions
# ---------------------------------------------------------------------------
@router.callback_query(AppState.workout_in_progress, F.data == "workout:add_set")
async def on_add_set(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    await _prompt_next_set_input(callback.message, state, user, is_first_set=False)
    await callback.answer()


@router.callback_query(AppState.workout_in_progress, F.data == "workout:delete_last_set")
async def on_delete_last_set(
    callback: CallbackQuery, state: FSMContext, user: User
) -> None:
    data = await state.get_data()
    sets = list(data.get("sets") or [])
    if not sets:
        await callback.answer("Нет подходов для удаления", show_alert=True)
        return
    sets.pop()
    await state.update_data(sets=sets)

    name = data.get("current_exercise", "Упражнение")
    if not sets:
        await callback.message.edit_text(
            f"Все подходы удалены.\n<b>{name}</b> — введи первый подход заново."
        )
        await _prompt_next_set_input(callback.message, state, user, is_first_set=False)
        await callback.answer("Удалено")
        return

    body = "\n".join(_render_set_line(s, index=i + 1) for i, s in enumerate(sets))
    await callback.message.edit_text(
        f"Последний подход удалён. Остались подходы:\n<b>{name}</b>\n{body}",
        reply_markup=set_action_kb(),
    )
    await callback.answer("Удалено")


@router.callback_query(AppState.workout_in_progress, F.data == "workout:finish_exercise")
async def on_finish_exercise(
    callback: CallbackQuery, state: FSMContext
) -> None:
    data = await state.get_data()
    sets = list(data.get("sets") or [])
    if not sets:
        await callback.answer("Сначала сохрани хотя бы один подход", show_alert=True)
        return
    await _show_exercise_summary(callback, state)


async def _show_exercise_summary(
    callback: CallbackQuery, state: FSMContext
) -> None:
    data = await state.get_data()
    sets = list(data.get("sets") or [])
    name = data.get("current_exercise", "Упражнение")
    body = "\n".join(_render_set_line(s, index=i + 1) for i, s in enumerate(sets))
    await callback.message.edit_text(
        f"Упражнение завершено: <b>{name}</b>\n"
        f"Подходов: {len(sets)}\n{body}",
        reply_markup=exercise_summary_kb(),
    )
    await state.set_state(AppState.workout_exercise_summary)
    await callback.answer()


# ---------------------------------------------------------------------------
# Exercise summary actions
# ---------------------------------------------------------------------------
def _flush_current_exercise(data: dict) -> list[dict]:
    """Move current exercise from FSM 'current_*' into the 'exercises' list."""
    exercises = list(data.get("exercises") or [])
    if data.get("current_exercise_id") and data.get("sets"):
        exercises.append({
            "exercise_id": data["current_exercise_id"],
            "name": data.get("current_exercise") or "",
            "log_mode": data.get("current_log_mode"),
            "load_mode": data.get("current_load_mode"),
            "sets": list(data["sets"]),
        })
    return exercises


@router.callback_query(
    AppState.workout_exercise_summary, F.data == "workout:next_exercise"
)
@router.callback_query(
    AppState.workout_exercise_summary, F.data == "workout:back_to_catalog"
)
async def on_after_exercise_pick_next(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    data = await state.get_data()
    exercises = _flush_current_exercise(data)
    section = data.get("current_section") or SECTION_GYM
    group_value = data.get("current_group")
    await state.update_data(
        exercises=exercises,
        current_exercise_id=None,
        current_exercise=None,
        current_log_mode=None,
        current_load_mode=None,
        sets=[],
        current_page=0,
    )

    if section == SECTION_GYM and group_value:
        try:
            group = MuscleGroup(group_value)
        except ValueError:
            group = None
        if group is MuscleGroup.full_body:
            await _render_full_body_catalog(
                callback.message, state, session, user, edit=True
            )
            await callback.answer()
            return
        if group is not None:
            await _render_catalog_page(
                callback.message, state, session, user, group, page=0, edit=True
            )
            await callback.answer()
            return

    if section != SECTION_GYM:
        await _render_curated_section(
            callback.message, state, session, user, section, edit=True
        )
        await callback.answer()
        return

    # Fallback: section picker.
    await callback.message.edit_text(
        "Выбери раздел тренировки:",
        reply_markup=workout_section_kb(),
    )
    await state.set_state(AppState.workout_type_select)
    await callback.answer()


@router.callback_query(
    AppState.workout_exercise_summary, F.data == "workout:repeat_exercise"
)
async def on_repeat_exercise(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Flush current exercise, then restart the same one fresh."""
    data = await state.get_data()
    exercises = _flush_current_exercise(data)
    # Keep exercise_id/name/modes; reset the in-progress sets to a new round.
    await state.update_data(
        exercises=exercises,
        sets=[],
        pending_weight=None,
        pending_extra=None,
        pending_bw_snapshot=None,
    )
    await _prompt_next_set_input(callback.message, state, user, is_first_set=True)
    await callback.answer()


# ---------------------------------------------------------------------------
# Finish whole workout
# ---------------------------------------------------------------------------
def _parse_started_at(raw: object, *, fallback: datetime) -> datetime:
    if not isinstance(raw, str) or not raw:
        return fallback
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@router.callback_query(AppState.workout_exercise_summary, F.data == "workout:finish")
@router.callback_query(AppState.workout_in_progress, F.data == "workout:finish")
async def on_finish_workout(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    data = await state.get_data()
    exercises = _flush_current_exercise(data)

    if not exercises:
        await state.clear()
        await callback.message.edit_text("Тренировка пуста — ничего не сохранено.")
        await callback.message.answer("Выбери действие:", reply_markup=MAIN_MENU)
        await callback.answer()
        return

    workout_service = WorkoutService(
        WorkoutRepository(session),
        ExerciseRepository(session),
    )

    finished_at = datetime.now(timezone.utc)
    started_at = _parse_started_at(data.get("workout_started_at"), fallback=finished_at)

    workout = await workout_service.start_workout(
        user_id=user.id,
        workout_date=date.today(),
        name=None,
        started_at=started_at,
        finished_at=finished_at,
    )

    total_sets = 0
    total_volume = 0.0
    for order, ex in enumerate(exercises, 1):
        ex_id = ex.get("exercise_id")
        try:
            exercise_uuid = UUID(ex_id) if ex_id else None
        except ValueError:
            exercise_uuid = None
        if exercise_uuid is not None:
            we = await workout_service.attach_exercise(
                workout_id=workout.id,
                exercise_id=exercise_uuid,
                order=order,
            )
        else:
            we = await workout_service.add_exercise_to_workout(
                workout_id=workout.id,
                user_id=user.id,
                exercise_name=ex.get("name") or "Без названия",
                order=order,
            )

        for set_num, s in enumerate(ex["sets"], 1):
            load_mode = s.get("load_mode")
            reps = s.get("reps")
            duration = s.get("duration")
            effective = s.get("effective_weight")
            await workout_service.log_set(
                workout_exercise_id=we.id,
                set_number=set_num,
                weight_kg=effective if load_mode in (LOAD_EXTERNAL, LOAD_BW_OPT_EXTRA) else None,
                reps=reps,
                duration_seconds=duration,
                load_mode=load_mode,
                user_body_weight_snapshot=s.get("user_body_weight_snapshot"),
                extra_weight_kg=s.get("extra_weight"),
                effective_weight_kg=effective,
            )
            total_sets += 1
            if effective and reps:
                total_volume += float(effective) * int(reps)

    duration_minutes = max(1, round((finished_at - started_at).total_seconds() / 60))
    workout.estimated_calories_burned = estimate_calories_burned(
        duration_minutes=duration_minutes,
        user_weight_kg=user.weight_kg,
        total_sets=total_sets,
        total_volume_kg=total_volume,
    )

    await state.clear()

    lines = ["Тренировка завершена! Отличная работа!\n"]
    for ex in exercises:
        lines.append(f"<b>{ex['name']}</b>")
        for i, s in enumerate(ex["sets"], 1):
            lines.append(_render_set_line(s, index=i))
    lines.append(
        f"\nИтого: {len(exercises)} упр., {total_sets} подх., "
        f"объём {total_volume:.0f} кг"
    )
    lines.append(
        f"⏱ Время: {duration_minutes} мин · 🔥 ~{workout.estimated_calories_burned:.0f} ккал"
    )

    await callback.message.edit_text("\n".join(lines))
    await callback.message.answer("Выбери действие:", reply_markup=MAIN_MENU)
    await callback.answer("Сохранено!")
