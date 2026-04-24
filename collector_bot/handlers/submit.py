"""Submission flow and moderation handlers for the collector bot."""

from __future__ import annotations

from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.access import is_admin
from bot.models.submission import SubmissionKind, SubmissionStatus
from bot.models.user import User
from bot.repositories.submission import SubmissionRepository
from bot.services.submission_publish import publish_submission

from collector_bot.keyboards import (
    exercise_type_kb,
    moderation_kb,
    muscle_group_kb,
    submission_kind_kb,
)
from collector_bot.states import CollectorSG

router = Router(name="collector_submit")


def _as_float(text: str) -> float:
    return float(text.replace(",", ".").strip())


def _message_text(message: Message) -> str | None:
    text = (message.text or "").strip()
    return text or None


async def _require_text(message: Message, *, prompt: str) -> str | None:
    text = _message_text(message)
    if text is None:
        await message.answer(prompt)
        return None
    return text


async def _require_positive_float(message: Message, *, field_name: str) -> float | None:
    text = _message_text(message)
    if text is None:
        await message.answer(f"Отправь числовое значение для поля «{field_name}».")
        return None

    try:
        value = _as_float(text)
    except ValueError:
        await message.answer(f"Для поля «{field_name}» нужно число. Можно с точкой или запятой.")
        return None

    if value <= 0:
        await message.answer(f"Для поля «{field_name}» нужно число больше нуля.")
        return None

    return value


async def _require_positive_int(message: Message, *, field_name: str) -> int | None:
    text = _message_text(message)
    if text is None:
        await message.answer(f"Отправь целое число для поля «{field_name}».")
        return None

    try:
        value = int(text)
    except ValueError:
        await message.answer(f"Для поля «{field_name}» нужно целое число.")
        return None

    if value <= 0:
        await message.answer(f"Для поля «{field_name}» нужно число больше нуля.")
        return None

    return value


async def _save_submission(
    session: AsyncSession,
    user: User,
    *,
    kind: str,
    title: str,
    raw_text: str,
    payload: dict[str, str | int | float],
) -> str:
    repo = SubmissionRepository(session)
    submission = await repo.create(
        telegram_user_id=user.id,
        kind=SubmissionKind(kind),
        title=title,
        raw_text=raw_text,
        payload=payload,
    )
    return str(submission.id)


@router.callback_query(F.data.startswith("collector_kind:"))
async def on_kind_pick(callback: CallbackQuery, state: FSMContext) -> None:
    kind = callback.data.split(":", 1)[1]
    await state.clear()
    await state.update_data(kind=kind)

    if kind == "exercise":
        await state.set_state(CollectorSG.exercise_name)
        await callback.message.answer("Введи название упражнения.")
    elif kind == "product":
        await state.set_state(CollectorSG.product_name)
        await callback.message.answer("Введи название продукта.")
    elif kind == "recipe":
        await state.set_state(CollectorSG.recipe_name)
        await callback.message.answer("Введи название рецепта.")

    await callback.answer()


@router.message(CollectorSG.exercise_name)
async def exercise_name(message: Message, state: FSMContext) -> None:
    text = await _require_text(message, prompt="Введи текстовое название упражнения.")
    if text is None:
        return

    await state.update_data(name=text)
    await state.set_state(CollectorSG.exercise_muscle_group)
    await message.answer("Выбери основную группу мышц.", reply_markup=muscle_group_kb())


@router.callback_query(CollectorSG.exercise_muscle_group, F.data.startswith("collector_muscle:"))
async def exercise_muscle(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    await state.update_data(muscle_group=value)
    await state.set_state(CollectorSG.exercise_type)
    await callback.message.answer("Выбери тип упражнения.", reply_markup=exercise_type_kb())
    await callback.answer()


@router.callback_query(CollectorSG.exercise_type, F.data.startswith("collector_ex_type:"))
async def exercise_type(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    value = callback.data.split(":", 1)[1]
    await state.update_data(exercise_type=value)
    data = await state.get_data()
    payload = {
        "name": data["name"],
        "muscle_group": data["muscle_group"],
        "exercise_type": value,
    }
    raw_text = (
        f"Упражнение: {payload['name']}\n"
        f"Группа мышц: {payload['muscle_group']}\n"
        f"Тип: {payload['exercise_type']}"
    )
    submission_id = await _save_submission(
        session,
        user,
        kind="exercise",
        title=str(payload["name"]),
        raw_text=raw_text,
        payload=payload,
    )
    await state.clear()
    await state.set_state(CollectorSG.choosing_kind)
    await callback.message.answer(
        "Упражнение сохранено и отправлено на модерацию.\n"
        f"ID заявки: <code>{submission_id}</code>",
        reply_markup=submission_kind_kb(),
    )
    await callback.answer()


@router.message(CollectorSG.product_name)
async def product_name(message: Message, state: FSMContext) -> None:
    text = await _require_text(message, prompt="Введи текстовое название продукта.")
    if text is None:
        return

    await state.update_data(name=text)
    await state.set_state(CollectorSG.product_brand)
    await message.answer("Введи бренд продукта или отправь `-`, если бренда нет.")


@router.message(CollectorSG.product_brand)
async def product_brand(message: Message, state: FSMContext) -> None:
    brand = await _require_text(message, prompt="Введи бренд продукта или отправь `-`.")
    if brand is None:
        return

    await state.update_data(brand="" if brand == "-" else brand)
    await state.set_state(CollectorSG.product_calories)
    await message.answer("Сколько калорий на 100 г?")


@router.message(CollectorSG.product_calories)
async def product_calories(message: Message, state: FSMContext) -> None:
    value = await _require_positive_float(message, field_name="калории на 100 г")
    if value is None:
        return

    await state.update_data(calories_per_100g=value)
    await state.set_state(CollectorSG.product_protein)
    await message.answer("Сколько белка на 100 г?")


@router.message(CollectorSG.product_protein)
async def product_protein(message: Message, state: FSMContext) -> None:
    value = await _require_positive_float(message, field_name="белки на 100 г")
    if value is None:
        return

    await state.update_data(protein_per_100g=value)
    await state.set_state(CollectorSG.product_fat)
    await message.answer("Сколько жиров на 100 г?")


@router.message(CollectorSG.product_fat)
async def product_fat(message: Message, state: FSMContext) -> None:
    value = await _require_positive_float(message, field_name="жиры на 100 г")
    if value is None:
        return

    await state.update_data(fat_per_100g=value)
    await state.set_state(CollectorSG.product_carbs)
    await message.answer("Сколько углеводов на 100 г?")


@router.message(CollectorSG.product_carbs)
async def product_carbs(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    value = await _require_positive_float(message, field_name="углеводы на 100 г")
    if value is None:
        return

    await state.update_data(carbs_per_100g=value)
    data = await state.get_data()
    payload = {
        "name": data["name"],
        "brand": data["brand"],
        "calories_per_100g": data["calories_per_100g"],
        "protein_per_100g": data["protein_per_100g"],
        "fat_per_100g": data["fat_per_100g"],
        "carbs_per_100g": data["carbs_per_100g"],
    }
    raw_text = (
        f"Продукт: {payload['name']}\n"
        f"Бренд: {payload['brand'] or '—'}\n"
        f"КБЖУ на 100 г: {payload['calories_per_100g']} / "
        f"{payload['protein_per_100g']} / {payload['fat_per_100g']} / "
        f"{payload['carbs_per_100g']}"
    )
    submission_id = await _save_submission(
        session,
        user,
        kind="product",
        title=str(payload["name"]),
        raw_text=raw_text,
        payload=payload,
    )
    await state.clear()
    await state.set_state(CollectorSG.choosing_kind)
    await message.answer(
        "Продукт сохранён и отправлен на модерацию.\n"
        f"ID заявки: <code>{submission_id}</code>",
        reply_markup=submission_kind_kb(),
    )


@router.message(CollectorSG.recipe_name)
async def recipe_name(message: Message, state: FSMContext) -> None:
    text = await _require_text(message, prompt="Введи текстовое название рецепта.")
    if text is None:
        return

    await state.update_data(name=text)
    await state.set_state(CollectorSG.recipe_total_weight)
    await message.answer("Какой общий вес рецепта в граммах?")


@router.message(CollectorSG.recipe_total_weight)
async def recipe_total_weight(message: Message, state: FSMContext) -> None:
    value = await _require_positive_float(message, field_name="общий вес рецепта")
    if value is None:
        return

    await state.update_data(total_weight_grams=value)
    await state.set_state(CollectorSG.recipe_servings)
    await message.answer("На сколько порций рассчитан рецепт?")


@router.message(CollectorSG.recipe_servings)
async def recipe_servings(message: Message, state: FSMContext) -> None:
    value = await _require_positive_int(message, field_name="количество порций")
    if value is None:
        return

    await state.update_data(servings=value)
    await state.set_state(CollectorSG.recipe_calories)
    await message.answer("Сколько калорий на 100 г?")


@router.message(CollectorSG.recipe_calories)
async def recipe_calories(message: Message, state: FSMContext) -> None:
    value = await _require_positive_float(message, field_name="калории на 100 г")
    if value is None:
        return

    await state.update_data(calories_per_100g=value)
    await state.set_state(CollectorSG.recipe_protein)
    await message.answer("Сколько белка на 100 г?")


@router.message(CollectorSG.recipe_protein)
async def recipe_protein(message: Message, state: FSMContext) -> None:
    value = await _require_positive_float(message, field_name="белки на 100 г")
    if value is None:
        return

    await state.update_data(protein_per_100g=value)
    await state.set_state(CollectorSG.recipe_fat)
    await message.answer("Сколько жиров на 100 г?")


@router.message(CollectorSG.recipe_fat)
async def recipe_fat(message: Message, state: FSMContext) -> None:
    value = await _require_positive_float(message, field_name="жиры на 100 г")
    if value is None:
        return

    await state.update_data(fat_per_100g=value)
    await state.set_state(CollectorSG.recipe_carbs)
    await message.answer("Сколько углеводов на 100 г?")


@router.message(CollectorSG.recipe_carbs)
async def recipe_carbs(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    value = await _require_positive_float(message, field_name="углеводы на 100 г")
    if value is None:
        return

    await state.update_data(carbs_per_100g=value)
    data = await state.get_data()
    payload = {
        "name": data["name"],
        "total_weight_grams": data["total_weight_grams"],
        "servings": data["servings"],
        "calories_per_100g": data["calories_per_100g"],
        "protein_per_100g": data["protein_per_100g"],
        "fat_per_100g": data["fat_per_100g"],
        "carbs_per_100g": data["carbs_per_100g"],
    }
    raw_text = (
        f"Рецепт: {payload['name']}\n"
        f"Вес: {payload['total_weight_grams']} г\n"
        f"Порции: {payload['servings']}\n"
        f"КБЖУ на 100 г: {payload['calories_per_100g']} / "
        f"{payload['protein_per_100g']} / {payload['fat_per_100g']} / "
        f"{payload['carbs_per_100g']}"
    )
    submission_id = await _save_submission(
        session,
        user,
        kind="recipe",
        title=str(payload["name"]),
        raw_text=raw_text,
        payload=payload,
    )
    await state.clear()
    await state.set_state(CollectorSG.choosing_kind)
    await message.answer(
        "Рецепт сохранён и отправлен на модерацию.\n"
        f"ID заявки: <code>{submission_id}</code>",
        reply_markup=submission_kind_kb(),
    )


@router.message(Command("pending"))
async def list_pending(message: Message, session: AsyncSession, user: User) -> None:
    if not is_admin(user.id):
        await message.answer("Команда доступна только администратору.")
        return

    repo = SubmissionRepository(session)
    items = await repo.list_pending(limit=5)
    if not items:
        await message.answer("Сейчас нет заявок на модерации.")
        return

    for item in items:
        text = (
            f"<b>{item.kind.value.upper()}</b> · {item.title}\n"
            f"Автор: <code>{item.telegram_user_id}</code>\n"
            f"Создано: {item.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"{item.raw_text}"
        )
        await message.answer(text, reply_markup=moderation_kb(str(item.id)))


@router.callback_query(F.data.startswith("collector_review:"))
async def review_submission(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    if not is_admin(user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    _, _, decision, raw_id = callback.data.split(":")
    repo = SubmissionRepository(session)
    submission = await repo.get_by_id(UUID(raw_id))
    if submission is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if submission.status != SubmissionStatus.pending:
        await callback.answer("Эта заявка уже обработана.", show_alert=True)
        return

    if decision == "reject":
        await repo.set_review(
            submission.id,
            status=SubmissionStatus.rejected,
            reviewed_by=user.id,
            review_comment="Rejected in collector bot",
        )
        base_text = callback.message.html_text or callback.message.text or "Заявка"
        await callback.message.edit_text(f"{base_text}\n\nОтклонено.")
        await callback.answer("Заявка отклонена")
        return

    try:
        target_entity, target_entity_id = await publish_submission(session, submission)
    except ValueError as exc:
        await callback.answer(str(exc), show_alert=True)
        return

    await repo.set_review(
        submission.id,
        status=SubmissionStatus.approved,
        reviewed_by=user.id,
        review_comment="Approved in collector bot",
        target_entity=target_entity,
        target_entity_id=target_entity_id,
    )
    base_text = callback.message.html_text or callback.message.text or "Заявка"
    await callback.message.edit_text(
        f"{base_text}\n\n"
        f"Одобрено и опубликовано в <b>{target_entity}</b>."
    )
    await callback.answer("Заявка опубликована")
