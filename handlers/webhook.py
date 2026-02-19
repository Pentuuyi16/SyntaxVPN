import json
import logging

from aiohttp import web
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_free_uuid, assign_uuid, activate_subscription
from utils.texts import PLAN_DETAILS
from utils.vpn import generate_vless_link
from utils.monitoring import get_best_server

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

    # Находим лучший сервер
    server_name = get_best_server()
    if not server_name:
        logger.error("Все серверы переполнены!")
        bot: Bot = request.app["bot"]
        await bot.send_message(
            chat_id=telegram_id,
            text="⚠️ Оплата прошла, но все серверы заняты. Обратитесь в поддержку.",
        )
        return web.Response(status=200)

    # Берём свободный UUID из пула этого сервера
    user_uuid = await get_free_uuid(server_name)
    if not user_uuid:
        logger.error("Нет свободных UUID для сервера %s", server_name)
        bot: Bot = request.app["bot"]
        await bot.send_message(
            chat_id=telegram_id,
            text="⚠️ Оплата прошла, но все места заняты. Обратитесь в поддержку.",
        )
        return web.Response(status=200)

    # Помечаем UUID как занятый
    await assign_uuid(user_uuid, telegram_id)

    # Генерируем VLESS ссылку
    from config.settings import VPN_SERVERS
    label = VPN_SERVERS[server_name].get("label", server_name)
    vless_key = generate_vless_link(user_uuid, server_name, f"SyntaxVPN {label}")

    # Сохраняем подписку
    await activate_subscription(telegram_id, plan_id, user_uuid, vless_key)

    # Уведомляем пользователя
    sub_url = f"https://syntax-vpn.tech/sub/{user_uuid}"
    bot: Bot = request.app["bot"]
    await bot.send_message(
        chat_id=telegram_id,
        text=(
            "Готово! Оплата подтверждена ✅\n\n"
            "Спасибо, что выбрали нас — это много значит для нашей команды. "
            "С любовью, SyntaxVPN 🤍\n\n"
            f"<blockquote>Ваша подписка:\n{sub_url}</blockquote>"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 Добавить в приложение", url=f"happ://add?url={sub_url}")],
            [InlineKeyboardButton(text="📋 Скопировать ссылку", callback_data=f"copy_sub_{user_uuid}")],
            [InlineKeyboardButton(text="📥 Скачать приложение", callback_data="download_app")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")],
        ]),
        parse_mode="HTML",
    )

    logger.info("Оплата: user=%s, plan=%s, server=%s, uuid=%s", telegram_id, plan_id, server_name, user_uuid)
    return web.Response(status=200)