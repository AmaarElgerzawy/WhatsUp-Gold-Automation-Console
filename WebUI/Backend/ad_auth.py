import os
import re
from datetime import datetime
from typing import Optional, Dict, Tuple

from ldap3 import Server, Connection, SUBTREE, BASE
from ldap3.utils.conv import escape_filter_chars

from auth import load_users, save_users


def _debug(msg: str) -> None:
    if str(os.environ.get("WUG_AD_DEBUG", "")).lower() in ("1", "true", "yes"):
        print(msg)


def _log_auth_failure(reason: str) -> None:
    """Always log why AD login failed (no passwords). Helps diagnose without WUG_AD_DEBUG."""
    print(f"[AD AUTH] failed: {reason}")


def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = os.environ.get(name, default)
    if required and (val is None or str(val).strip() == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def _make_user_id(email: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", email.strip()).strip("_").lower()


def _extract_domain_dn_from_group_dn(group_dn: str) -> str:
    dc_parts = []
    for part in group_dn.split(","):
        p = part.strip()
        if p.upper().startswith("DC="):
            dc_parts.append(p)
    return ",".join(dc_parts) if dc_parts else group_dn


def _ad_connect(
    service_bind_dn: str,
    service_bind_password: str,
    ad_url: str,
    use_starttls: bool,
) -> Connection:
    server = Server(ad_url, get_info=None)
    conn = Connection(
        server,
        user=service_bind_dn,
        password=service_bind_password,
        auto_bind=False,
    )
    conn.open()

    if use_starttls:
        conn.start_tls()

    # Must succeed or searches may run as anonymous and return no rows for restricted OUs.
    if not conn.bind():
        err = getattr(conn, "result", None)
        try:
            conn.unbind()
        except Exception:
            pass
        raise RuntimeError(f"LDAP service bind failed: {err}")

    if not conn.bound:
        try:
            conn.unbind()
        except Exception:
            pass
        raise RuntimeError("LDAP service bind did not leave connection authenticated")

    return conn


def _build_user_search_filter(login_value: str) -> str:
    """
    Match your working script:
    (&(objectClass=user)(|(mail=...)(userPrincipalName=...)(sAMAccountName=...)(cn=...)))
    """
    u = escape_filter_chars(login_value.strip())
    return (
        f"(&(objectClass=user)"
        f"(|(mail={u})(userPrincipalName={u})(sAMAccountName={u})(cn={u})))"
    )


def _build_user_search_filter_ad_standard(login_value: str) -> str:
    """Common AD pattern; use if objectClass-only filter misses."""
    u = escape_filter_chars(login_value.strip())
    return (
        f"(&(objectCategory=person)(objectClass=user)"
        f"(|(mail={u})(userPrincipalName={u})(sAMAccountName={u})(cn={u})))"
    )


def _member_of_contains_group(entry, group_dn: str) -> bool:
    """Prefer checking the user's memberOf — works when the service account cannot read group objects."""
    gd = (group_dn or "").strip().lower()
    if not gd:
        return False
    try:
        attr = entry["memberOf"]
    except Exception:
        return False
    if attr is None or not getattr(attr, "value", None):
        return False
    raw = attr.value
    if isinstance(raw, (list, tuple)):
        vals = [str(x) for x in raw]
    else:
        vals = [str(raw)]
    return any(v.strip().lower() == gd for v in vals)


def _find_ad_user(
    conn: Connection,
    search_base: str,
    login_value: str,
) -> Optional[Tuple[str, bool]]:
    """Returns (user_dn, is_enabled) or None."""
    filters = [_build_user_search_filter(login_value)]
    if str(os.environ.get("WUG_AD_TRY_OBJECT_CATEGORY_FILTER", "true")).lower() in (
        "1",
        "true",
        "yes",
    ):
        filters.append(_build_user_search_filter_ad_standard(login_value))

    attrs = [
        "distinguishedName",
        "userAccountControl",
        "mail",
        "userPrincipalName",
        "sAMAccountName",
        "cn",
        "memberOf",
    ]

    last_result = None
    for filt in filters:
        _debug(f"[AD AUTH] search_base={search_base!r} filter={filt}")
        conn.search(
            search_base=search_base,
            search_filter=filt,
            search_scope=SUBTREE,
            attributes=attrs,
        )
        last_result = getattr(conn, "result", None)
        if isinstance(last_result, dict) and last_result.get("result") not in (0, None):
            _debug(f"[AD AUTH] LDAP search error: {last_result}")
        if conn.entries:
            break
        _debug(f"[AD AUTH] no entries; result={last_result}")

    if not conn.entries:
        _debug(f"[AD AUTH] user not found after filters; last_result={last_result}")
        return None

    entry = conn.entries[0]
    user_dn = (
        str(entry.distinguishedName)
        if "distinguishedName" in entry
        else str(entry.entry_dn)
    )

    uac_raw = None
    if "userAccountControl" in entry and entry["userAccountControl"]:
        uac_raw = entry["userAccountControl"].value

    try:
        uac = int(uac_raw) if uac_raw is not None else 0
    except Exception:
        uac = 0

    enabled = (uac & 2) == 0
    return (user_dn, enabled)


def _is_member_of_group(conn: Connection, group_dn: str, user_dn: str) -> bool:
    conn.search(
        search_base=group_dn,
        search_filter="(objectClass=group)",
        search_scope=BASE,
        attributes=["member", "uniqueMember"],
    )
    if not conn.entries:
        return False

    entry = conn.entries[0]

    members = []
    if "member" in entry and entry["member"]:
        members.extend([str(v) for v in entry["member"]])
    if "uniqueMember" in entry and entry["uniqueMember"]:
        members.extend([str(v) for v in entry["uniqueMember"]])

    user_dn_norm = user_dn.lower()
    return any(m.lower() == user_dn_norm for m in members)


def _ensure_ad_provisioned_user(username: str, ad_enabled: bool) -> Dict:
    users = load_users()

    existing = next((u for u in users if u.get("username") == username), None)
    if existing is None:
        now = datetime.now().isoformat()
        new_user = {
            "id": _make_user_id(username),
            "username": username,
            "email": username,
            "password_hash": "",
            "role": "custom",
            "privileges": [],
            "active": bool(ad_enabled),
            "created_at": now,
        }
        users.append(new_user)
        save_users(users)
        return new_user

    existing["active"] = bool(ad_enabled)
    existing["email"] = username
    existing["username"] = username

    if "privileges" not in existing or not isinstance(existing.get("privileges"), list):
        existing["privileges"] = []
    if "role" not in existing or not existing.get("role"):
        existing["role"] = "custom"

    users = [u for u in users if u.get("id") != existing.get("id")] + [existing]
    save_users(users)
    return existing


def ad_login_and_get_user(username: str, password: str) -> Optional[Dict]:
    try:
        ad_url = _get_env("WUG_AD_URL", required=True)
        group_dn = _get_env("WUG_AD_GROUP_DN", required=True)
        service_bind_dn = _get_env("WUG_AD_SERVICE_BIND_DN", required=True)
        service_bind_password = _get_env("WUG_AD_SERVICE_PASSWORD", required=True)
    except RuntimeError as e:
        _log_auth_failure(str(e))
        return None

    search_base = _get_env("WUG_AD_USER_SEARCH_BASE_DN")
    if not search_base:
        search_base = _extract_domain_dn_from_group_dn(group_dn)

    use_starttls = str(_get_env("WUG_AD_USE_STARTTLS", "false")).lower() == "true"

    login_value = (username or "").strip()
    password = password or ""

    if not login_value or not password:
        _log_auth_failure("missing username or password")
        return None

    _debug(
        "[AD AUTH] config: "
        + str(
            {
                "ad_url": ad_url,
                "group_dn": group_dn,
                "service_bind_dn": service_bind_dn,
                "search_base": search_base,
                "use_starttls": use_starttls,
            }
        )
    )

    try:
        svc_conn = _ad_connect(
            service_bind_dn=service_bind_dn,
            service_bind_password=service_bind_password.strip(),
            ad_url=ad_url,
            use_starttls=use_starttls,
        )
    except Exception as e:
        _log_auth_failure(f"service bind: {e}")
        return None

    user_dn = None
    ad_enabled = False
    user_entry = None

    try:
        user_lookup = _find_ad_user(svc_conn, search_base, login_value)
        if user_lookup is None:
            _log_auth_failure("user not found in LDAP search (check WUG_AD_USER_SEARCH_BASE_DN and filter)")
            return None

        user_dn, ad_enabled = user_lookup
        _debug(f"[AD AUTH] found DN={user_dn}, enabled={ad_enabled}")

        if not ad_enabled:
            _log_auth_failure("account disabled in AD (userAccountControl)")
            return None

        if not svc_conn.entries:
            _log_auth_failure("internal: no LDAP entry after user search")
            return None

        user_entry = svc_conn.entries[0]

        # Prefer memberOf on the user (same data your test script printed).
        in_group = _member_of_contains_group(user_entry, group_dn)
        if not in_group:
            in_group = _is_member_of_group(svc_conn, group_dn=group_dn, user_dn=user_dn)

        if not in_group:
            _log_auth_failure(
                f"user is not in required group (check memberOf / group membership for {group_dn})"
            )
            return None
    finally:
        try:
            svc_conn.unbind()
        except Exception:
            pass

    user_server = Server(ad_url, get_info=None)
    try:
        user_conn = Connection(user_server, user=user_dn, password=password, auto_bind=True)
        try:
            user_conn.unbind()
        except Exception:
            pass
    except Exception as e:
        _log_auth_failure(f"user password bind failed: {e}")
        return None

    internal_user = _ensure_ad_provisioned_user(username=login_value, ad_enabled=ad_enabled)
    _debug(f"[AD AUTH] success for {login_value}, internal id {internal_user.get('id')}")
    print(f"[AD AUTH] success for {login_value} (id={internal_user.get('id')})")
    return internal_user
