import paramiko
from config.settings import VPN_SERVERS


def _ssh_command(server_name: str, cmd: str) -> str:
    """Выполнить SSH команду."""
    server = VPN_SERVERS[server_name]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=server["host"],
        username=server["ssh_user"],
        password=server["ssh_password"],
    )
    stdin, stdout, stderr = ssh.exec_command(cmd)
    result = stdout.read().decode().strip()
    ssh.close()
    return result


def get_active_ips(server_name: str) -> list:
    """Получить список активных IP подключённых к VPN."""
    cmd = (
        "ss -tnp | grep xray | grep ESTAB | "
        "awk '{if ($4 ~ /:443$/) print $5}' | "
        "rev | cut -d: -f2- | rev | "
        "sed 's/\\[::ffff://;s/\\]//' | sort -u"
    )
    result = _ssh_command(server_name, cmd)
    if not result:
        return []
    return [ip.strip() for ip in result.split("\n") if ip.strip()]


def get_connections(server_name: str) -> dict:
    """Получить количество устройств на каждый ключ (только активные)."""
    active_ips = get_active_ips(server_name)
    if not active_ips:
        return {}

    # Для каждого активного IP находим email в логе
    email_ips = {}
    for ip in active_ips:
        cmd = f"grep '{ip}' /var/log/xray/access.log | tail -1 | grep -oP 'email: \\K\\S+'"
        result = _ssh_command(server_name, cmd)
        if result:
            email = result.strip()
            if email not in email_ips:
                email_ips[email] = set()
            email_ips[email].add(ip)

    return {email: len(ips) for email, ips in email_ips.items()}


def get_online_count(server_name: str) -> int:
    """Получить количество онлайн пользователей."""
    return len(get_active_ips(server_name))


def get_all_servers_online() -> dict:
    """Получить онлайн по всем серверам."""
    result = {}
    for name in VPN_SERVERS:
        result[name] = get_online_count(name)
    return result


def get_best_server() -> str | None:
    """Найти сервер с наименьшей нагрузкой."""
    online = get_all_servers_online()
    best = None
    min_load = float("inf")

    for name, server in VPN_SERVERS.items():
        count = online.get(name, 0)
        max_users = server.get("max_users", 80)

        if count < max_users and count < min_load:
            min_load = count
            best = name

    return best