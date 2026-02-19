import base64
import logging

from aiohttp import web

from config.settings import VPN_SERVERS
from database.db import get_subscription_by_uuid
from utils.vpn import generate_vless_link

logger = logging.getLogger(__name__)


async def subscription_handler(request: web.Request) -> web.Response:
    """Отдаёт список серверов для VPN-приложения."""
    user_uuid = request.match_info.get("uuid", "")

    if not user_uuid:
        return web.Response(status=404, text="Not found")

    # Проверяем что UUID активен
    sub = await get_subscription_by_uuid(user_uuid)
    if not sub or not sub["is_active"]:
        return web.Response(status=403, text="Subscription expired")

    # Генерируем ссылки на все серверы
    links = []
    for name, server in VPN_SERVERS.items():
        label = server.get("label", name)
        link = generate_vless_link(user_uuid, name, f"SyntaxVPN {label}")
        links.append(link)

    # Happ/V2rayTun ожидает base64
    raw = "\n".join(links)
    encoded = base64.b64encode(raw.encode()).decode()

    return web.Response(
        text=encoded,
        content_type="text/plain",
        headers={
            "Subscription-Userinfo": f"upload=0; download=0; total=0; expire=0",
            "Content-Disposition": "inline",
        },
    )