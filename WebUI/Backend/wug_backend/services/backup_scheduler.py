from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable

from wug_backend.services.backup_schedule_config import (
    load_backup_schedule,
    seconds_until_next_daily_run,
)


class BackupScheduler:
    """
    Background scheduler: reads schedule from JSON (data/backup_schedule.json),
    falls back to env when file missing. Supports interval and daily-at-time modes.
    """

    def __init__(
        self,
        backup_service,
        schedule_path: Path,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self._backup_service = backup_service
        self._schedule_path = schedule_path
        self._logger = logger or print
        self._task: asyncio.Task | None = None
        self._running_guard = asyncio.Lock()
        self._startup_handled = False

    @staticmethod
    def create(backup_service, schedule_path: Path) -> "BackupScheduler":
        return BackupScheduler(backup_service=backup_service, schedule_path=schedule_path)

    async def _run_backups(self) -> None:
        async with self._running_guard:
            await asyncio.to_thread(self._backup_service.run_all_backups)

    async def _sleep_until_next(self, cfg: dict) -> None:
        mode = (cfg.get("mode") or "interval").strip().lower()
        interval_seconds = max(60, int(cfg.get("interval_seconds", 3600)))
        run_time = (cfg.get("run_time") or "02:00").strip()
        if mode == "daily":
            delay = seconds_until_next_daily_run(run_time)
            self._logger(f"[BACKUP SCHEDULER] next run in {delay:.0f}s (daily @ {run_time})")
            await asyncio.sleep(delay)
        else:
            self._logger(f"[BACKUP SCHEDULER] next run in {interval_seconds}s (interval)")
            await asyncio.sleep(interval_seconds)

    async def _loop(self) -> None:
        while True:
            cfg = load_backup_schedule(self._schedule_path)
            if not bool(cfg.get("enabled", False)):
                await asyncio.sleep(30)
                continue

            run_on_startup = bool(cfg.get("run_on_startup", False))
            if run_on_startup and not self._startup_handled:
                self._startup_handled = True
                try:
                    await self._run_backups()
                    self._logger("[BACKUP SCHEDULER] startup run completed")
                except Exception as e:
                    self._logger(f"[BACKUP SCHEDULER] startup run failed: {e}")
                cfg = load_backup_schedule(self._schedule_path)
                if not bool(cfg.get("enabled", False)):
                    continue
                await self._sleep_until_next(cfg)
                continue

            try:
                await self._run_backups()
            except Exception as e:
                self._logger(f"[BACKUP SCHEDULER] error: {e}")

            cfg = load_backup_schedule(self._schedule_path)
            if not bool(cfg.get("enabled", False)):
                await asyncio.sleep(30)
                continue
            await self._sleep_until_next(cfg)

    def install(self, app) -> None:
        @app.on_event("startup")
        async def _start() -> None:
            self._task = asyncio.create_task(self._loop())
            self._logger("[BACKUP SCHEDULER] Task started (enable via /backups/schedule or env)")

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
