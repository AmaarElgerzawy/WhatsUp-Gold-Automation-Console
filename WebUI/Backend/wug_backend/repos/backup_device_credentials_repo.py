from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def try_parse_inline_backup_credentials(line: str) -> Optional[Dict[str, str]]:
    """
    If the line looks like host,username,password,enable_password (four fields,
    split on the first three commas), return parsed credentials. Otherwise None.

    Passwords containing commas are not supported in this shorthand; use the
    Config backups credential table or JSON file for those devices.
    """
    raw = (line or "").strip()
    if not raw or raw.startswith("#"):
        return None
    parts = [p.strip() for p in raw.split(",", 3)]
    if len(parts) != 4:
        return None
    host, username, password, enable_password = parts
    if not host or not username:
        return None
    return {
        "host": host,
        "username": username,
        "password": password,
        "enable_password": enable_password,
    }


def resolve_effective_credentials(
    line: str,
    stored: Dict[str, Dict[str, str]],
) -> Optional[Dict[str, str]]:
    """Credentials for one routers.txt line: inline shorthand or entry in stored map."""
    inl = try_parse_inline_backup_credentials(line)
    if inl:
        return {
            "username": inl["username"],
            "password": inl["password"],
            "enable_password": inl.get("enable_password") or "",
        }
    row = stored.get(line.strip())
    if not row:
        return None
    return {
        "username": str(row.get("username") or "").strip(),
        "password": str(row.get("password") or ""),
        "enable_password": str(row.get("enable_password") or ""),
    }


def connect_host_for_backup_line(line: str) -> str:
    inl = try_parse_inline_backup_credentials(line)
    if inl:
        return inl["host"]
    return line.strip()


def storage_folder_for_backup_line(line: str) -> str:
    inl = try_parse_inline_backup_credentials(line)
    key = inl["host"] if inl else line.strip()
    return _safe_path_segment(key)


def _safe_path_segment(s: str) -> str:
    bad = '<>:"/\\|?*'
    t = "".join("_" if c in bad else c for c in (s or "").strip())
    return t or "device"


def normalize_routers_editor_save(
    content: str,
) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """
    Parse the backup-routers text editor: write host-only lines to routers.txt and
    collect credentials from host,user,password,enable lines.

    Preserves # comment lines in order. De-duplicates hosts (first occurrence keeps
    position; later duplicate lines update credentials only).
    """
    out_lines: List[str] = []
    cred_updates: Dict[str, Dict[str, str]] = {}
    seen_hosts: set[str] = set()

    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            out_lines.append(stripped)
            continue
        inl = try_parse_inline_backup_credentials(stripped)
        if inl:
            h = inl["host"].strip()
            cred_updates[h] = {
                "username": inl["username"],
                "password": inl["password"],
                "enable_password": inl.get("enable_password") or "",
            }
            if h not in seen_hosts:
                seen_hosts.add(h)
                out_lines.append(h)
        else:
            h = stripped
            if h not in seen_hosts:
                seen_hosts.add(h)
                out_lines.append(h)

    return out_lines, cred_updates


def router_output_lines_to_host_set(lines: List[str]) -> set[str]:
    return {
        ln.strip()
        for ln in lines
        if ln.strip() and not ln.strip().startswith("#")
    }


def migrate_legacy_credential_keys_to_hosts(
    existing: Dict[str, Dict[str, str]],
    hosts_in_file: set[str],
) -> None:
    """
    Drop JSON keys that were the full comma-separated line; copy into host key if needed.
    """
    for key in list(existing.keys()):
        if key in hosts_in_file:
            continue
        inl = try_parse_inline_backup_credentials(key)
        if not inl:
            continue
        host = inl["host"]
        if host not in hosts_in_file:
            continue
        if host not in existing:
            prev = existing[key]
            existing[host] = {
                "username": (prev.get("username") or "").strip() or inl["username"],
                "password": str(prev.get("password") or "") or inl["password"],
                "enable_password": str(prev.get("enable_password") or "")
                or (inl.get("enable_password") or ""),
            }
        del existing[key]


def load_map(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            continue
        key = k.strip()
        if not key:
            continue
        out[key] = {
            "username": str(v.get("username") or "").strip(),
            "password": str(v.get("password") or ""),
            "enable_password": str(
                v.get("enable_password") if v.get("enable_password") is not None else v.get("enablePassword") or ""
            ),
        }
    return out


def save_map(path: Path, creds: Dict[str, Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(creds, indent=2, ensure_ascii=False), encoding="utf-8")


def merge_put_devices(
    existing: Dict[str, Dict[str, str]],
    devices: List[dict],
    required_targets: List[str],
) -> Tuple[Dict[str, Dict[str, str]], Optional[str]]:
    """
    Build a new credential map from the UI payload. Every line in required_targets
    must appear in devices. Empty password / enable_password strings keep previous
    values when present.
    """
    if not isinstance(devices, list):
        return {}, "devices must be a list"

    by_ip: Dict[str, dict] = {}
    for row in devices:
        if not isinstance(row, dict):
            return {}, "Each device entry must be an object"
        ip = (row.get("ip") or "").strip()
        if not ip:
            continue
        by_ip[ip] = row

    for t in required_targets:
        if t not in by_ip:
            return {}, f"Missing credential row for backup target: {t}"

    result: Dict[str, Dict[str, str]] = {}
    for ip in required_targets:
        row = by_ip[ip]
        inl = try_parse_inline_backup_credentials(ip)
        username = (row.get("username") or "").strip()
        if not username and inl:
            username = (inl.get("username") or "").strip()
        password_in = row.get("password")
        enable_in = row.get("enable_password")
        if enable_in is None:
            enable_in = row.get("enablePassword")

        prev = dict(existing.get(ip, {}))
        if inl:
            if not prev.get("username"):
                prev["username"] = inl["username"]
            if not prev.get("password"):
                prev["password"] = inl.get("password") or ""
            if not str(prev.get("enable_password") or "").strip():
                prev["enable_password"] = inl.get("enable_password") or ""

        if password_in is None or str(password_in).strip() == "":
            password = str(prev.get("password") or "")
        else:
            password = str(password_in)

        if enable_in is None or str(enable_in).strip() == "":
            enable_password = str(prev.get("enable_password") or "")
        else:
            enable_password = str(enable_in)

        if not username:
            return {}, f"Username is required for {ip}"
        if not password.strip():
            return {}, f"Password is required for {ip} (enter a password or keep an existing one)"

        result[ip] = {
            "username": username,
            "password": password,
            "enable_password": enable_password,
        }

    return result, None


def device_row_for_api(
    ip: str,
    stored: Optional[Dict[str, str]],
) -> dict[str, Any]:
    inl = try_parse_inline_backup_credentials(ip)
    if inl:
        has_pw = bool((inl.get("password") or "").strip())
        has_en = bool(str(inl.get("enable_password") or "").strip())
        return {
            "ip": ip,
            # Shown in UI instead of raw line so comma-shorthand secrets are not echoed.
            "target_label": inl.get("host") or ip,
            "username": inl.get("username") or "",
            "password": "",
            "enable_password": "",
            "password_configured": has_pw,
            "enable_password_configured": has_en,
            "inline_format": True,
        }
    has_pw = bool(stored and (stored.get("password") or "").strip())
    en = (stored or {}).get("enable_password") or ""
    has_en = bool(str(en).strip())
    return {
        "ip": ip,
        "target_label": ip,
        "username": (stored or {}).get("username") or "",
        "password": "",
        "enable_password": "",
        "password_configured": has_pw,
        "enable_password_configured": has_en,
        "inline_format": False,
    }


def validate_all_targets_have_credentials(
    targets: List[str],
    creds: Dict[str, Dict[str, str]],
) -> Optional[str]:
    missing: List[str] = []
    missing_pw: List[str] = []
    for t in targets:
        eff = resolve_effective_credentials(t, creds)
        if not eff or not (eff.get("username") or "").strip():
            missing.append(t)
        elif not (eff.get("password") or "").strip():
            missing_pw.append(t)
    if missing:
        return "Missing credentials for: " + ", ".join(missing[:20]) + (
            f" (+{len(missing) - 20} more)" if len(missing) > 20 else ""
        )
    if missing_pw:
        return "Missing password for: " + ", ".join(missing_pw[:20])
    return None
