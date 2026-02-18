from datetime import datetime, timedelta

import aiosqlite
from config.settings import DB_PATH

PLAN_DURATION = {
    "plan_1": 30,
    "plan_3": 90,
    "plan_6": 180,
    "plan_12": 365,
    "plan_test": 1,
}


async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                uuid TEXT NOT NULL,
                vless_key TEXT NOT NULL,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)
        await db.commit()


async def add_user(telegram_id: int, username: str | None, full_name: str) -> bool:
    """Добавить пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)",
                (telegram_id, username, full_name),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def activate_subscription(telegram_id: int, plan_id: str, user_uuid: str, vless_key: str):
    """Активировать подписку после оплаты."""
    days = PLAN_DURATION.get(plan_id, 30)
    end_date = datetime.now() + timedelta(days=days)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET is_active = 0 WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,),
        )
        await db.execute(
            "INSERT INTO subscriptions (telegram_id, plan_id, uuid, vless_key, end_date) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, plan_id, user_uuid, vless_key, end_date.isoformat()),
        )
        await db.commit()


async def get_active_subscription(telegram_id: int) -> dict | None:
    """Получить активную подписку пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM subscriptions WHERE telegram_id = ? AND is_active = 1",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None