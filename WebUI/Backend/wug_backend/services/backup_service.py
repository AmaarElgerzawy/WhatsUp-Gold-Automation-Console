from __future__ import annotations

import subprocess


class BackupService:
    def run_running_backup(self) -> dict:
        proc = subprocess.run(
            ["python", "-m", "wug_backend.runners.backup_running"],
            capture_output=True,
            text=True,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    def run_startup_backup(self) -> dict:
        proc = subprocess.run(
            ["python", "-m", "wug_backend.runners.backup_startup"],
            capture_output=True,
            text=True,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    def run_all_backups(self) -> dict:
        running = self.run_running_backup()
        startup = self.run_startup_backup()
        return {"running": running, "startup": startup}

