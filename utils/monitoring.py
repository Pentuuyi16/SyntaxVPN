import paramiko
from config.settings import VPN_SERVERS


def get_connections(server_name: str) -> dict:
    """Получить количество устройств на каждый ключ."""
    server = VPN_SERVERS[server_name]
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server["host"],
            username=server["ssh_user"],
            password=server["ssh_password"],
        )

        cmd = (
            "awk '{"
            'ip=$3; gsub(/.*from /,"",ip); gsub(/:[0-9]+$/,"",ip); email=$NF'
            "} email{a[email][ip]=1} "
            "END{for(e in a){n=0; for(i in a[e])n++; print e,n}}' "
            "/var/log/xray/access.log"
        )

        stdin, stdout, stderr = ssh.exec_command(cmd)
        result = stdout.read().decode().strip()
        ssh.close()

        connections = {}
        for line in result.split("\n"):
            if line.strip():
                parts = line.strip().split()
                if len(parts) == 2:
                    connections[parts[0]] = int(parts[1])

        return connections
    except Exception as e:
        print(f"Ошибка мониторинга: {e}")
        return {}


def get_online_count(server_name: str) -> int:
    """Получить количество онлайн пользователей."""
    server = VPN_SERVERS[server_name]
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server["host"],
            username=server["ssh_user"],
            password=server["ssh_password"],
        )

        cmd = (
            "ss -tnp | grep xray | grep ESTAB | "
            "awk '{if ($4 ~ /:443$/) print $5}' | "
            "rev | cut -d: -f2- | rev | sort -u | wc -l"
        )

        stdin, stdout, stderr = ssh.exec_command(cmd)
        result = stdout.read().decode().strip()
        ssh.close()

        return int(result) if result else 0
    except Exception as e:
        print(f"Ошибка мониторинга: {e}")
        return 0


def get_all_servers_online() -> dict:
    """Получить онлайн по всем серверам."""
    result = {}
    for name in VPN_SERVERS:
        result[name] = get_online_count(name)
    return result


def get_best_server() -> str | None:
    """Найти сервер с наименьшей нагрузкой и свободными местами."""
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