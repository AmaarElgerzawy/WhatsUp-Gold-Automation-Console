from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from netmiko import ConnectHandler

from constants import SSH_ENABLE_PASSWORD, SSH_PASSWORD, SSH_USERNAME


@dataclass(frozen=True)
class RouterTarget:
    ip: str
    device_type: str


class RouterListParser:
    def parse_router_line(self, line: str, default_device_type: str) -> RouterTarget | None:
        if not line:
            return None
        raw = line.strip()
        if not raw or raw.startswith("#"):
            return None

        normalized = raw.replace("|", ",").replace("\t", ",")
        parts = [p.strip() for p in normalized.split(",") if p.strip()]

        if len(parts) == 1:
            space_parts = [p for p in parts[0].split(" ") if p.strip()]
            if len(space_parts) >= 2:
                return RouterTarget(ip=space_parts[0].strip(), device_type=space_parts[1].strip())
            return RouterTarget(ip=parts[0], device_type=default_device_type)

        ip = parts[0]
        dev = parts[1] if len(parts) >= 2 else default_device_type
        return RouterTarget(ip=ip, device_type=(dev or default_device_type))

    def parse_from_text(self, text: str, default_device_type: str) -> list[RouterTarget]:
        routers: list[RouterTarget] = []
        for line in (text or "").splitlines():
            parsed = self.parse_router_line(line, default_device_type)
            if parsed:
                routers.append(parsed)
        return routers


class SimpleConfigPusher:
    def push_from_file(self, router: RouterTarget, config_file: str, device_type_default: str) -> None:
        device_type = (router.device_type or device_type_default).strip() or device_type_default
        print("\\n=== Connecting to {router.ip} ({device_type}) ===")

        device = {
            "device_type": device_type,
            "ip": router.ip,
            "username": SSH_USERNAME,
            "password": SSH_PASSWORD,
            "secret": SSH_ENABLE_PASSWORD,
        }

        conn = ConnectHandler(**device)
        conn.enable()
        output = conn.send_config_from_file(config_file)
        conn.disconnect()
        print(output, flush=True)

