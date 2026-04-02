from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional


def load_all(path: Path) -> List[dict]:
    if not path.exists():
        return []
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_all(path: Path, items: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def get_by_id(path: Path, credential_id: str) -> Optional[dict]:
    for c in load_all(path):
        if c.get("id") == credential_id:
            return c
    return None


def upsert(path: Path, cred: dict) -> None:
    items = load_all(path)
    cid = cred.get("id")
    found = False
    for i, c in enumerate(items):
        if c.get("id") == cid:
            items[i] = cred
            found = True
            break
    if not found:
        items.append(cred)
    save_all(path, items)


def delete_by_id(path: Path, credential_id: str) -> bool:
    items = load_all(path)
    new_items = [c for c in items if c.get("id") != credential_id]
    if len(new_items) == len(items):
        return False
    save_all(path, new_items)
    return True


def validate_credential_payload(payload: dict, is_update: bool) -> dict[str, Any]:
    name = (payload.get("name") or "").strip()
    username = (payload.get("username") or "").strip()
    if not name or not username:
        raise ValueError("name and username are required")
    password = payload.get("password")
    if password is None:
        password = ""
    enable_password = payload.get("enable_password")
    if enable_password is None:
        enable_password = payload.get("enablePassword")
    if enable_password is None:
        enable_password = ""
    description = (payload.get("description") or "").strip()
    return {
        "name": name,
        "username": username,
        "password": str(password),
        "enable_password": str(enable_password),
        "description": description,
    }
