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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS uuid_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE NOT NULL,
                server_name TEXT NOT NULL,
                is_used INTEGER DEFAULT 0,
                telegram_id INTEGER DEFAULT NULL
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


async def get_free_uuid(server_name: str) -> str | None:
    """Получить свободный UUID из пула."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT uuid FROM uuid_pool WHERE server_name = ? AND is_used = 0 LIMIT 1",
            (server_name,),
        )
        row = await cursor.fetchone()
        if row:
            return row[0]
        return None


async def assign_uuid(uuid: str, telegram_id: int):
    """Пометить UUID как занятый."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE uuid_pool SET is_used = 1, telegram_id = ? WHERE uuid = ?",
            (telegram_id, uuid),
        )
        await db.commit()


async def release_uuid(uuid: str):
    """Освободить UUID."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE uuid_pool SET is_used = 0, telegram_id = NULL WHERE uuid = ?",
            (uuid,),
        )
        await db.commit()


async def load_uuids_to_pool(uuids: list[str], server_name: str):
    """Загрузить UUID в пул."""
    async with aiosqlite.connect(DB_PATH) as db:
        for uuid in uuids:
            try:
                await db.execute(
                    "INSERT INTO uuid_pool (uuid, server_name) VALUES (?, ?)",
                    (uuid, server_name),
                )
            except aiosqlite.IntegrityError:
                pass
        await db.commit()


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
    
async def get_admin_stats() -> dict:
    """Статистика для админки."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Всего пользователей
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]

        # Активные подписки
        cursor = await db.execute("SELECT COUNT(*) FROM subscriptions WHERE is_active = 1")
        active_subs = (await cursor.fetchone())[0]

        # Доход
        cursor = await db.execute("""
            SELECT COALESCE(SUM(
                CASE plan_id
                    WHEN 'plan_1' THEN 99
                    WHEN 'plan_3' THEN 199
                    WHEN 'plan_6' THEN 499
                    WHEN 'plan_12' THEN 999
                    WHEN 'plan_test' THEN 1
                    ELSE 0
                END
            ), 0) FROM subscriptions
        """)
        total_income = (await cursor.fetchone())[0]

        # Свободные UUID
        cursor = await db.execute("SELECT COUNT(*) FROM uuid_pool WHERE is_used = 0")
        free_uuids = (await cursor.fetchone())[0]

        # Серверы
        cursor = await db.execute("""
            SELECT server_name,
                   SUM(CASE WHEN is_used = 1 THEN 1 ELSE 0 END) as used,
                   COUNT(*) as total
            FROM uuid_pool GROUP BY server_name
        """)
        servers = []
        for row in await cursor.fetchall():
            servers.append({"name": row[0], "used": row[1], "max": row[2]})

        return {
            "total_users": total_users,
            "active_subs": active_subs,
            "total_income": total_income,
            "free_uuids": free_uuids,
            "servers": servers,
        }


async def get_admin_users() -> list:
    """Список пользователей с подписками."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT u.telegram_id, u.username, u.full_name,
                   s.plan_id, s.is_active, s.end_date
            FROM users u
            LEFT JOIN subscriptions s ON u.telegram_id = s.telegram_id
                AND s.id = (SELECT MAX(id) FROM subscriptions WHERE telegram_id = u.telegram_id)
            ORDER BY u.created_at DESC
        """)
        rows = await cursor.fetchall()
        return [
            {
                "telegram_id": r[0],
                "username": r[1],
                "full_name": r[2],
                "plan_id": r[3],
                "is_active": r[4],
                "end_date": r[5],
            }
            for r in rows
        ]


async def get_admin_pool() -> list:
    """UUID пул для админки."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT uuid, server_name, is_used, telegram_id FROM uuid_pool ORDER BY is_used DESC, id LIMIT 200"
        )
        rows = await cursor.fetchall()
        return [
            {
                "uuid": r[0],
                "server_name": r[1],
                "is_used": r[2],
                "telegram_id": r[3],
            }
            for r in rows
        ]