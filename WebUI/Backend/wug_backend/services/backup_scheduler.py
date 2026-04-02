from __future__ import annotations

import asyncio
import os
from typing import Callable, Optional


class BackupScheduler:
    """
    Background scheduler that periodically triggers backend backup capture.

    Note: This is intentionally simple (interval-based) to avoid changing any
    backup collection logic; it only orchestrates when to run.
    """

    def __init__(
        self,
        backup_service,
        enabled: bool,
        interval_seconds: int,
        run_on_startup: bool,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self._backup_service = backup_service
        self._enabled = enabled
        self._interval_seconds = interval_seconds
        self._run_on_startup = run_on_startup
        self._logger = logger or print
        self._task: asyncio.Task | None = None
        self._running_guard = asyncio.Lock()

    @staticmethod
    def from_env(backup_service) -> "BackupScheduler":
        enabled = os.environ.get("WUG_BACKUP_SCHEDULER_ENABLED", "false").lower() == "true"
        interval_seconds = int(os.environ.get("WUG_BACKUP_SCHEDULER_INTERVAL_SECONDS", "3600"))
        run_on_startup = os.environ.get("WUG_BACKUP_SCHEDULER_RUN_ON_STARTUP", "false").lower() == "true"
        return BackupScheduler(
            backup_service=backup_service,
            enabled=enabled,
            interval_seconds=interval_seconds,
            run_on_startup=run_on_startup,
        )

    async def _loop(self) -> None:
        if self._run_on_startup:
            try:
                async with self._running_guard:
                    await asyncio.to_thread(self._backup_service.run_all_backups)
            except Exception as e:
                self._logger(f"[BACKUP SCHEDULER] startup run failed: {e}")

        while True:
            try:
                async with self._running_guard:
                    await asyncio.to_thread(self._backup_service.run_all_backups)
            except Exception as e:
                self._logger(f"[BACKUP SCHEDULER] error: {e}")

            await asyncio.sleep(self._interval_seconds)

    def install(self, app) -> None:
        @app.on_event("startup")
        async def _start() -> None:
            if not self._enabled:
                self._logger("[BACKUP SCHEDULER] Disabled via WUG_BACKUP_SCHEDULER_ENABLED")
                return
            self._task = asyncio.create_task(self._loop())
            self._logger(f"[BACKUP SCHEDULER] Started (interval={self._interval_seconds}s)")

        @app.on_event("shutdown")
        async def _stop() -> None:
            if self._task is None:
                return
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            self._logger("[BACKUP SCHEDULER] Stopped")

