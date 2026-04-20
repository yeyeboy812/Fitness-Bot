"""Telegram Stars subscription: /subscribe, tariff picker, invoice, payment."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.models.user import User
from bot.repositories.user import UserRepository
from bot.services.subscription import TARIFFS, extend_from, get_tariff, is_pro_active

logger = logging.getLogger(__name__)

router = Router(name="subscription")

_PAYLOAD_PREFIX = "sub:"


def _tariffs_kb() -> InlineKeyboardMarkup:
    from bot.keyboards.inline import back_to_menu_button

    rows = [
        [
            InlineKeyboardButton(
                text=f"{t.title} — {t.stars} ⭐",
                callback_data=f"sub:buy:{t.key}",
            )
        ]
        for t in TARIFFS.values()
    ]
    rows.append([back_to_menu_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _status_line(user: User) -> str:
    if is_pro_active(user):
        until = user.subscription_expires_at.strftime("%d.%m.%Y")
        return f"Сейчас у тебя <b>Pro</b> до <b>{until}</b>."
    return "Сейчас у тебя <b>Free</b>-подписка."


async def open_subscription(message: Message, user: User) -> None:
    """Entry point shared by /subscribe and the inline menu "⭐ Pro" button."""
    await message.answer(
        f"{_status_line(user)}\n\n"
        "Выбери тариф — оплата проходит звёздами Telegram ⭐:",
        reply_markup=_tariffs_kb(),
    )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, user: User) -> None:
    await open_subscription(message, user)


@router.callback_query(F.data.startswith("sub:buy:"))
async def on_buy(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 2)[2]
    tariff = get_tariff(key)
    if tariff is None:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await callback.message.answer_invoice(
        title=tariff.title,
        description=tariff.description,
        payload=f"{_PAYLOAD_PREFIX}{tariff.key}",
        provider_token="",  # empty for Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label=tariff.title, amount=tariff.stars)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery) -> None:
    payload = query.invoice_payload or ""
    if not payload.startswith(_PAYLOAD_PREFIX):
        await query.answer(ok=False, error_message="Неизвестный платёж")
        return

    key = payload[len(_PAYLOAD_PREFIX):]
    if get_tariff(key) is None:
        await query.answer(ok=False, error_message="Тариф больше не доступен")
        return

    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message, user: User, user_repo: UserRepository
) -> None:
    payment = message.successful_payment
    payload = payment.invoice_payload or ""

    if not payload.startswith(_PAYLOAD_PREFIX):
        logger.warning("successful_payment with unknown payload=%r", payload)
        return

    key = payload[len(_PAYLOAD_PREFIX):]
    tariff = get_tariff(key)
    if tariff is None:
        logger.error("successful_payment for missing tariff=%r user=%s", key, user.id)
        return

    new_expiry = extend_from(user, tariff)
    await user_repo.set_subscription(user.id, new_expiry)

    logger.info(
        "subscription_extended user=%s tariff=%s stars=%s until=%s charge_id=%s",
        user.id, tariff.key, payment.total_amount,
        new_expiry.isoformat(), payment.telegram_payment_charge_id,
    )

    await message.answer(
        f"Оплата получена ✅\n"
        f"Pro-доступ активен до <b>{new_expiry.strftime('%d.%m.%Y')}</b>.\n"
        f"Спасибо, что поддерживаешь проект!",
    )
