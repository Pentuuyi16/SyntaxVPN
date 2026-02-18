import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher

from config.settings import BOT_TOKEN, WEBHOOK_PATH, WEBHOOK_PORT
from database.db import init_db
from handlers import start
from handlers import payment
from handlers.webhook import yookassa_webhook


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(payment.router)

    # Инициализация БД
    await init_db()

    # Webhook сервер для ЮКассы
    app = web.Application()
    app["bot"] = bot
    app.router.add_post(WEBHOOK_PATH, yookassa_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    await site.start()

    logging.info("Webhook сервер запущен на порту %s", WEBHOOK_PORT)
    logging.info("Бот запущен")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())