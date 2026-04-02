from __future__ import annotations

from typing import Optional, Tuple

from fastapi import HTTPException

from auth import is_credential_allowed_for_user
from constants import SSH_CREDENTIALS_FILE
from wug_backend.repos import ssh_credentials_repo


def resolve_ssh_for_router_run(
    current_user: dict,
    credential_id: Optional[str],
    username: Optional[str],
    password: Optional[str],
    enable_password: Optional[str],
) -> Tuple[str, str, str]:
    """
    Returns (username, password, enable_password) for SSH.
    If credential_id is set, loads from server store and enforces per-user allowlist.
    """
    cid = (credential_id or "").strip()
    if cid:
        if not is_credential_allowed_for_user(current_user, cid):
            raise HTTPException(
                status_code=403,
                detail="You are not allowed to use this saved credential",
            )
        cred = ssh_credentials_repo.get_by_id(SSH_CREDENTIALS_FILE, cid)
        if not cred:
            raise HTTPException(status_code=404, detail="Saved credential not found")
        u = (cred.get("username") or "").strip()
        p = cred.get("password") or ""
        en = cred.get("enable_password") or ""
        if not u:
            raise HTTPException(status_code=400, detail="Saved credential has no username")
        enable = en if en else p
        return u, p, enable

    u = (username or "").strip()
    p = (password or "").strip()
    en = (enable_password or "").strip()
    if not u or not p:
        raise HTTPException(
            status_code=400,
            detail="Username and password are required, or select an allowed saved credential",
        )
    return u, p, en or p
