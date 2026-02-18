from config.settings import VPN_SERVERS


def generate_vless_link(user_uuid: str, server_name: str, label: str, fingerprint: str = "safari") -> str:
    """Генерация VLESS ссылки для клиента."""
    server = VPN_SERVERS[server_name]
    return (
        f"vless://{user_uuid}@{server['host']}:{server['port']}"
        f"?encryption=none&security=reality"
        f"&sni={server['sni']}"
        f"&fp={fingerprint}"
        f"&pbk={server['public_key']}"
        f"&sid={server['short_id']}"
        f"&type=tcp"
        f"#{label}"
    )