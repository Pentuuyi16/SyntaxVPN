import json
import uuid

import paramiko

from config.settings import VPN_SERVERS


def generate_uuid() -> str:
    """Генерация UUID для нового клиента."""
    return str(uuid.uuid4())


def generate_vless_link(user_uuid: str, server_name: str, label: str) -> str:
    """Генерация VLESS ссылки для клиента."""
    server = VPN_SERVERS[server_name]
    return (
        f"vless://{user_uuid}@{server['host']}:{server['port']}"
        f"?encryption=none&security=reality"
        f"&sni={server['sni']}"
        f"&fp=chrome"
        f"&pbk={server['public_key']}"
        f"&sid={server['short_id']}"
        f"&type=tcp"
        f"#{label}"
    )


def add_client_to_server(user_uuid: str, server_name: str) -> bool:
    """Добавить клиента на VPN-сервер через SSH."""
    server = VPN_SERVERS[server_name]

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server["host"],
            username=server["ssh_user"],
            password=server["ssh_password"],
        )

        # Читаем текущий конфиг
        stdin, stdout, stderr = ssh.exec_command(f"cat {server['config_path']}")
        config = json.loads(stdout.read().decode())

        # Проверяем нет ли уже такого UUID
        clients = config["inbounds"][0]["settings"]["clients"]
        for client in clients:
            if client["id"] == user_uuid:
                ssh.close()
                return True

        # Добавляем нового клиента
        clients.append({"id": user_uuid})

        # Записываем конфиг
        new_config = json.dumps(config, indent=4)
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{new_config}' > {server['config_path']}"
        )
        stdout.read()

        # Перезапускаем Xray
        stdin, stdout, stderr = ssh.exec_command("systemctl restart xray")
        stdout.read()

        ssh.close()
        return True

    except Exception as e:
        print(f"Ошибка SSH: {e}")
        return False


def remove_client_from_server(user_uuid: str, server_name: str) -> bool:
    """Удалить клиента с VPN-сервера."""
    server = VPN_SERVERS[server_name]

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=server["host"],
            username=server["ssh_user"],
            password=server["ssh_password"],
        )

        stdin, stdout, stderr = ssh.exec_command(f"cat {server['config_path']}")
        config = json.loads(stdout.read().decode())

        clients = config["inbounds"][0]["settings"]["clients"]
        config["inbounds"][0]["settings"]["clients"] = [
            c for c in clients if c["id"] != user_uuid
        ]

        new_config = json.dumps(config, indent=4)
        stdin, stdout, stderr = ssh.exec_command(
            f"echo '{new_config}' > {server['config_path']}"
        )
        stdout.read()

        stdin, stdout, stderr = ssh.exec_command("systemctl restart xray")
        stdout.read()

        ssh.close()
        return True

    except Exception as e:
        print(f"Ошибка SSH: {e}")
        return False