import os

from aiohttp import web

from config.settings import VPN_SERVERS
from database.db import get_admin_stats, get_admin_users, get_admin_pool, get_admin_connections
from utils.monitoring import get_connections, get_all_servers_online

ADMIN_HTML = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin", "panel.html")


async def admin_panel(request: web.Request) -> web.Response:
    """Отдаём HTML админки."""
    with open(ADMIN_HTML, "r", encoding="utf-8") as f:
        html = f.read()
    return web.Response(text=html, content_type="text/html")


async def admin_stats(request: web.Request) -> web.Response:
    """API статистики."""
    data = await get_admin_stats()
    online = get_all_servers_online()

    total_online = sum(online.values())
    data["online"] = total_online

    servers = []
    for name, server in VPN_SERVERS.items():
        servers.append({
            "name": server.get("label", name),
            "online": online.get(name, 0),
            "max": server.get("max_users", 80),
        })
    data["servers"] = servers

    return web.json_response(data)


async def admin_users(request: web.Request) -> web.Response:
    """API пользователей."""
    data = await get_admin_users()
    return web.json_response(data)


async def admin_pool(request: web.Request) -> web.Response:
    """API UUID пула."""
    data = await get_admin_pool()
    return web.json_response(data)


async def admin_connections(request: web.Request) -> web.Response:
    """API подключений по ключам."""
    connections = get_connections("germany")
    users = await get_admin_connections()

    result = []
    for user in users:
        short_uuid = user["uuid"][:8]
        devices = connections.get(short_uuid, 0)
        result.append({
            "uuid": user["uuid"],
            "telegram_id": user["telegram_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "devices": devices,
        })

    return web.json_response(result)