from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def _defaults_from_env() -> dict[str, Any]:
    return {
        "enabled": os.environ.get("WUG_BACKUP_SCHEDULER_ENABLED", "false").lower() == "true",
        "mode": "interval",
        "interval_seconds": int(os.environ.get("WUG_BACKUP_SCHEDULER_INTERVAL_SECONDS", "3600")),
        "run_time": "02:00",
        "run_on_startup": os.environ.get("WUG_BACKUP_SCHEDULER_RUN_ON_STARTUP", "false").lower() == "true",
    }


def load_backup_schedule(schedule_path: Path) -> dict[str, Any]:
    base = _defaults_from_env()
    if not schedule_path.exists():
        return base
    try:
        raw = schedule_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            for k in ("enabled", "mode", "interval_seconds", "run_time", "run_on_startup"):
                if k in data:
                    base[k] = data[k]
    except (json.JSONDecodeError, OSError):
        pass
    return base


def save_backup_schedule(schedule_path: Path, payload: dict[str, Any]) -> None:
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    schedule_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def validate_backup_schedule(payload: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(payload.get("enabled", False))
    mode = (payload.get("mode") or "interval").strip().lower()
    if mode not in ("interval", "daily"):
        raise ValueError("mode must be 'interval' or 'daily'")

    interval_seconds = int(payload.get("interval_seconds", 3600))
    if interval_seconds < 60:
        raise ValueError("interval_seconds must be at least 60")
    if interval_seconds > 604800:
        raise ValueError("interval_seconds must be at most 604800 (7 days)")

    run_time = (payload.get("run_time") or "02:00").strip()
    parts = run_time.split(":")
    if len(parts) != 2:
        raise ValueError("run_time must be HH:MM")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("run_time must be a valid 24h time")

    run_on_startup = bool(payload.get("run_on_startup", False))

    return {
        "enabled": enabled,
        "mode": mode,
        "interval_seconds": interval_seconds,
        "run_time": f"{h:02d}:{m:02d}",
        "run_on_startup": run_on_startup,
    }


def seconds_until_next_daily_run(run_time: str) -> float:
    now = datetime.now()
    parts = (run_time or "02:00").strip().split(":")
    h = int(parts[0]) if parts else 0
    m = int(parts[1]) if len(parts) > 1 else 0
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if now >= target:
        target = target + timedelta(days=1)
    return max(1.0, (target - now).total_seconds())
