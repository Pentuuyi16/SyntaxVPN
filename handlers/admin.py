import os

from aiohttp import web

from database.db import get_admin_stats, get_admin_users, get_admin_pool

ADMIN_HTML = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin", "panel.html")


async def admin_panel(request: web.Request) -> web.Response:
    """Отдаём HTML админки."""
    with open(ADMIN_HTML, "r", encoding="utf-8") as f:
        html = f.read()
    return web.Response(text=html, content_type="text/html")


async def admin_stats(request: web.Request) -> web.Response:
    """API статистики."""
    data = await get_admin_stats()
    return web.json_response(data)


async def admin_users(request: web.Request) -> web.Response:
    """API пользователей."""
    data = await get_admin_users()
    return web.json_response(data)


async def admin_pool(request: web.Request) -> web.Response:
    """API UUID пула."""
    data = await get_admin_pool()
    return web.json_response(data)