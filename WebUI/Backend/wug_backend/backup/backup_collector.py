from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from netmiko import ConnectHandler

from constants import BACKUP_BASE_DIR, ROUTERS_FILE, SSH_ENABLE_PASSWORD, SSH_PASSWORD, SSH_USERNAME


@dataclass(frozen=True)
class BackupCommand:
    label: str
    command: str
    output_filename_prefix: str


class BackupCollector:
    def _load_routers(self) -> list[str]:
        # Fallback IPs from the referenced scripts (kept for compatibility).
        fallback_ips = ["10.216.191.213", "12.100.7.92"]
        if not ROUTERS_FILE.exists():
            return list(fallback_ips)

        ips: list[str] = []
        for line in Path(ROUTERS_FILE).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ips.append(line)
        return ips if ips else list(fallback_ips)

    def _create_connection(self, ip: str, device_type: str = "cisco_ios"):
        # Note: device_type is fixed to preserve original script behavior.
        device = {
            "device_type": device_type,
            "ip": ip,
            "username": SSH_USERNAME,
            "password": SSH_PASSWORD,
            "secret": SSH_ENABLE_PASSWORD,
        }
        return ConnectHandler(**device)

    def _collect_one(self, ip: str, backup_command: BackupCommand) -> None:
        folder = BACKUP_BASE_DIR / ip
        folder.mkdir(parents=True, exist_ok=True)

        conn = None
        try:
            conn = self._create_connection(ip)
            conn.enable()  # enter enable mode if needed

            print(f"Getting {backup_command.label} from {ip} ...", flush=True)
            output = conn.send_command(
                backup_command.command,
                expect_string=r"#",
                read_timeout=60,
            )

            conn.disconnect()

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = folder / f"{backup_command.output_filename_prefix}_{timestamp}.txt"
            filename.write_text(output, encoding="utf-8")
            print(f"Saved config to {filename}", flush=True)
        except Exception as e:
            err_msg = f"ERROR on {ip}: {e}"
            print(err_msg, file=sys.stderr, flush=True)
            try:
                if conn is not None:
                    conn.disconnect()
            except Exception:
                pass

    def collect(self, backup_command: BackupCommand) -> int:
        ips = self._load_routers()
        if not ips:
            print(f"No router IPs found in {ROUTERS_FILE.name}")
            raise SystemExit(1)

        print(f"Found {len(ips)} router(s) in {ROUTERS_FILE.name}")

        for ip in ips:
            print(f"\n=== Connecting to {ip} ===", flush=True)
            self._collect_one(ip, backup_command)

        return 0


def run_running_cli(argv: list[str] | None = None) -> int:
    return BackupCollector().collect(
        BackupCommand(
            label="running-config",
            command="show running-config",
            output_filename_prefix="running-config",
        )
    )


def run_startup_cli(argv: list[str] | None = None) -> int:
    return BackupCollector().collect(
        BackupCommand(
            label="start-config",
            command="show startup-config",
            output_filename_prefix="startup_config",
        )
    )

