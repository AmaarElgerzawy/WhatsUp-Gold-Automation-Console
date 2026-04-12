from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from netmiko import ConnectHandler

from constants import BACKUP_BASE_DIR, BACKUP_DEVICE_CREDENTIALS_FILE, ROUTERS_FILE

from wug_backend.repos.backup_device_credentials_repo import (
    connect_host_for_backup_line,
    load_map,
    resolve_effective_credentials,
    storage_folder_for_backup_line,
)
from wug_backend.repos import backup_device_credentials_repo


def load_backup_target_lines(routers_path: Path | None = None) -> list[str]:
    path = routers_path or ROUTERS_FILE
    if not path.exists():
        return []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


@dataclass(frozen=True)
class BackupCommand:
    label: str
    command: str
    output_filename_prefix: str


class BackupCollector:
    def __init__(self, credentials_path: Path | None = None) -> None:
        self._credentials_path = credentials_path or BACKUP_DEVICE_CREDENTIALS_FILE

    def _load_routers(self) -> list[str]:
        return load_backup_target_lines(ROUTERS_FILE)

    def _load_credentials(self) -> dict[str, dict[str, str]]:
        return load_map(self._credentials_path)

    def _create_connection(
        self,
        ip: str,
        device_type: str,
        username: str,
        password: str,
        secret: str,
    ):
        device = {
            "device_type": device_type,
            "host": ip,
            "username": username,
            "password": password,
            "secret": secret,
        }
        return ConnectHandler(**device)

    def _collect_one(
        self,
        connect_host: str,
        storage_folder: str,
        backup_command: BackupCommand,
        username: str,
        password: str,
        enable_password: str,
    ) -> None:
        folder = BACKUP_BASE_DIR / storage_folder
        folder.mkdir(parents=True, exist_ok=True)

        secret = enable_password if (enable_password or "").strip() else password
        conn = None
        try:
            conn = self._create_connection(
                connect_host, "cisco_ios", username, password, secret
            )
            conn.enable()

            print(
                f"Getting {backup_command.label} from {connect_host} ...",
                flush=True,
            )
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
            err_msg = f"ERROR on {connect_host}: {e}"
            print(err_msg, file=sys.stderr, flush=True)
            try:
                if conn is not None:
                    conn.disconnect()
            except Exception:
                pass

    def collect(self, backup_command: BackupCommand) -> int:
        ips = self._load_routers()
        if not ips:
            print(f"No router IPs/lines found in {ROUTERS_FILE.name}", flush=True)
            raise SystemExit(1)

        creds = self._load_credentials()
        err = backup_device_credentials_repo.validate_all_targets_have_credentials(ips, creds)
        if err:
            print(err, file=sys.stderr, flush=True)
            raise SystemExit(2)

        print(f"Found {len(ips)} router(s) in {ROUTERS_FILE.name}")

        for line in ips:
            c = resolve_effective_credentials(line, creds)
            if not c:
                print(
                    f"ERROR: no credentials for line {line!r}",
                    file=sys.stderr,
                    flush=True,
                )
                raise SystemExit(2)
            u = c["username"]
            p = c["password"]
            en = c.get("enable_password") or ""
            host = connect_host_for_backup_line(line)
            folder_name = storage_folder_for_backup_line(line)
            print(f"\n=== Connecting to {host} ===", flush=True)
            self._collect_one(
                host, folder_name, backup_command, u, p, en
            )

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
