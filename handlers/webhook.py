import json
import logging

from aiohttp import web
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_free_uuid, assign_uuid, activate_subscription
from utils.texts import PLAN_DETAILS
from utils.vpn import generate_vless_link

logger = logging.getLogger(__name__)


async def yookassa_webhook(request: web.Request) -> web.Response:
    """Обработчик вебхука от ЮКассы."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.Response(status=400)

    if data.get("event") != "payment.succeeded":
        return web.Response(status=200)

    payment = data.get("object", {})
    metadata = payment.get("metadata", {})

    telegram_id = metadata.get("telegram_id")
    plan_id = metadata.get("plan_id")

    if not telegram_id or not plan_id:
        logger.warning("Webhook без metadata: %s", data)
        return web.Response(status=200)

    telegram_id = int(telegram_id)
    plan = PLAN_DETAILS.get(plan_id)

    if not plan:
        logger.warning("Неизвестный тариф: %s", plan_id)
        return web.Response(status=200)

    # Берём свободный UUID из пула
    user_uuid = await get_free_uuid("germany")
    if not user_uuid:
        logger.error("Нет свободных UUID для сервера germany")
        bot: Bot = request.app["bot"]
        await bot.send_message(
            chat_id=telegram_id,
            text="⚠️ Оплата прошла, но все места заняты. Обратитесь в поддержку.",
        )
        return web.Response(status=200)

    # Помечаем UUID как занятый
    await assign_uuid(user_uuid, telegram_id)

    # Генерируем VLESS ссылку
    vless_key = generate_vless_link(user_uuid, "germany", "🇩🇪 SyntaxVPN Germany")

    # Сохраняем подписку
    await activate_subscription(telegram_id, plan_id, user_uuid, vless_key)

    # Уведомляем пользователя
    bot: Bot = request.app["bot"]
    await bot.send_message(
        chat_id=telegram_id,
        text=(
            "Готово! Оплата подтверждена ✅\n\n"
            "Спасибо, что выбрали нас — это много значит для нашей команды. "
            "С любовью, SyntaxVPN 🤍\n\n"
            f"<blockquote>Ваш ключ:\n{vless_key}</blockquote>"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Добавить VPN в приложение", callback_data="add_to_app")],
            [InlineKeyboardButton(text="📥 Скачать приложение", callback_data="download_app")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")],
        ]),
        parse_mode="HTML",
    )

    logger.info("Оплата: user=%s, plan=%s, uuid=%s", telegram_id, plan_id, user_uuid)
    return web.Response(status=200)