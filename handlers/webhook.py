import json
import logging

from aiohttp import web
from aiogram import Bot

from database.db import activate_subscription
from utils.texts import PLAN_DETAILS

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

    # Активируем подписку в БД
    await activate_subscription(telegram_id, plan_id)

    # Уведомляем пользователя
    bot: Bot = request.app["bot"]
    await bot.send_message(
        chat_id=telegram_id,
        text=(
            "✅ Оплата прошла успешно!\n\n"
            f"<blockquote>"
            f"Тариф: {plan['name']}\n"
            f"Лимит подключений: {plan['connections']}"
            f"</blockquote>\n\n"
            "Нажмите «🔐 Мой ключ» в главном меню для получения ключа подключения."
        ),
        parse_mode="HTML",
    )

    logger.info("Оплата: user=%s, plan=%s", telegram_id, plan_id)
    return web.Response(status=200)