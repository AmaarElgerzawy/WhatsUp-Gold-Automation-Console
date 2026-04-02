from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import io
import json
import pandas as pd

from auth import (
    get_user_by_username,
    verify_password,
    create_access_token,
    get_current_user,
    check_privilege,
    require_privilege,
    log_activity,
    load_users,
    save_users,
    get_password_hash,
    PAGE_PRIVILEGES,
    ROLE_PRIVILEGES,
    AVAILABLE_PRIVILEGES,
    user_has_admin_access,
    get_allowed_credential_ids_for_user,
)
from ad_auth import ad_login_and_get_user
from constants import (
    ALLOWED_ORIGINS,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    DATA_DIR,
    BACKUP_BASE_DIR,
    CONFIG_BULK_ADD_DIR,
    CONFIG_BULK_UPDATE_DIR,
    CONFIG_BULK_DELETE_DIR,
    CONFIG_ROUTER_SIMPLE_DIR,
    CONFIG_ROUTER_INTERACTIVE_DIR,
    LOG_DIR,
    CONFIG_DIR,
    TEMPLATE_FILE,
    MEDIA_TYPE_EXCEL,
    DEFAULT_ENCODING,
    ROUTER_SCRIPTS_DIR,
    BULK_SCRIPTS_DIR,
    BACKUP_SCRIPTS_DIR,
    REPORTING_SCRIPTS_DIR,
    WORKDIR_PLACEHOLDER,
    LOG_PREFIX_EXIT_CODE,
    LOG_PREFIX_STDOUT,
    LOG_PREFIX_STDERR,
    ERROR_INVALID_OPERATION,
    ERROR_UNKNOWN_TEMPLATE,
    LOG_FILE_PREFIX_INTERACTIVE,
    LOG_FILE_PREFIX_SIMPLE,
    ACTIVITY_BULK_OPERATION,
    ACTIVITY_INTERACTIVE_COMMANDS,
    ACTIVITY_INTERACTIVE_COMMANDS_ERROR,
    ACTIVITY_SIMPLE_COMMANDS,
    CONFIG_PREFIX_BULK,
    CONFIG_PREFIX_INTERACTIVE,
    CONFIG_PREFIX_SIMPLE,
    ROUTERS_FILE,
    SSH_CREDENTIALS_FILE,
    REPORT_SCHEDULE_JSON_FILE,
    BACKUP_SCHEDULE_JSON_FILE,
    get_connection_string,
)

from wug_backend.reporting.availability_report import AvailabilityReportService, OUTPUT_FOLDER
from wug_backend.reporting.device_uptime_report import DeviceUpTimeReportService
from wug_backend.reporting.report_scheduler import run_scheduled_reports

from wug_backend.infra.db import DbConnectionFactory
from wug_backend.repos.device_repo import DeviceLookupRepository
from wug_backend.repos.template_repo import BulkTemplateRepository
from wug_backend.services.bulk_service import BulkOperationService
from wug_backend.services.router_service import RouterCommandService
from wug_backend.services.backup_service import BackupService
from wug_backend.services.backup_scheduler import BackupScheduler
from wug_backend.services.backup_schedule_config import (
    load_backup_schedule,
    save_backup_schedule,
    validate_backup_schedule,
)
from wug_backend.services.router_credential_resolver import resolve_ssh_for_router_run
from wug_backend.repos import ssh_credentials_repo
from wug_backend.utils.file_utils import FileNameService
from wug_backend.utils.log_utils import LogCollector, OutputSanitizer, LogWriter


def _parse_credential_ids_json(raw: Optional[str]) -> Optional[List[str]]:
    if raw is None or not str(raw).strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid credential_ids JSON: {e}") from e
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="credential_ids must be a list")
    return [str(x) for x in data if x]


def _validate_credential_ids_exist(ids: List[str]) -> None:
    if not ids:
        return
    all_creds = ssh_credentials_repo.load_all(SSH_CREDENTIALS_FILE)
    known = {c.get("id") for c in all_creds}
    invalid = [x for x in ids if x not in known]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown credential id(s): {invalid}")


def _credential_public_meta(c: dict) -> dict:
    return {
        "id": c.get("id"),
        "name": c.get("name") or "",
        "username": c.get("username") or "",
        "description": c.get("description") or "",
    }


def create_app() -> FastAPI:
    # ================= INITIALIZATION =================
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_BASE_DIR.mkdir(parents=True, exist_ok=True)

    for d in [
        CONFIG_BULK_ADD_DIR,
        CONFIG_BULK_UPDATE_DIR,
        CONFIG_BULK_DELETE_DIR,
        CONFIG_ROUTER_SIMPLE_DIR,
        CONFIG_ROUTER_INTERACTIVE_DIR,
        LOG_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="WhatsUp Gold WebUI Wrapper")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        allow_credentials=True,
    )

    filename_service = FileNameService()
    output_sanitizer = OutputSanitizer(
        router_scripts_dir=ROUTER_SCRIPTS_DIR,
        bulk_scripts_dir=BULK_SCRIPTS_DIR,
        backup_scripts_dir=BACKUP_SCRIPTS_DIR,
        reporting_scripts_dir=REPORTING_SCRIPTS_DIR,
        workdir_placeholder=WORKDIR_PLACEHOLDER,
    )
    log_collector = LogCollector()
    log_writer = LogWriter(
        log_dir=LOG_DIR,
        default_encoding=DEFAULT_ENCODING,
        filename_service=filename_service,
        log_prefix_exit_code=LOG_PREFIX_EXIT_CODE,
        log_prefix_stdout=LOG_PREFIX_STDOUT,
        log_prefix_stderr=LOG_PREFIX_STDERR,
    )

    db_factory = DbConnectionFactory()
    device_repo = DeviceLookupRepository(db_factory=db_factory)
    bulk_service = BulkOperationService(
        device_repo=device_repo,
        config_dir=CONFIG_DIR,
        filename_service=filename_service,
        output_sanitizer=output_sanitizer,
        log_writer=log_writer,
        activity_logger=log_activity,
        config_prefix_bulk=CONFIG_PREFIX_BULK,
        activity_bulk_operation=ACTIVITY_BULK_OPERATION,
    )
    router_service = RouterCommandService(
        router_scripts_dir=ROUTER_SCRIPTS_DIR,
        log_dir=LOG_DIR,
        config_router_interactive_dir=CONFIG_ROUTER_INTERACTIVE_DIR,
        config_router_simple_dir=CONFIG_ROUTER_SIMPLE_DIR,
        default_encoding=DEFAULT_ENCODING,
        log_collector=log_collector,
        log_writer=log_writer,
        activity_logger=log_activity,
        env_wug_routers="WUG_ROUTERS",
        env_wug_tasks="WUG_TASKS",
        env_wug_ssh_user="WUG_SSH_USER",
        env_wug_ssh_pass="WUG_SSH_PASS",
        env_wug_ssh_enable="WUG_SSH_ENABLE",
        config_prefix_interactive=CONFIG_PREFIX_INTERACTIVE,
        config_prefix_simple=CONFIG_PREFIX_SIMPLE,
        log_file_prefix_interactive=LOG_FILE_PREFIX_INTERACTIVE,
        log_file_prefix_simple=LOG_FILE_PREFIX_SIMPLE,
        activity_interactive_commands=ACTIVITY_INTERACTIVE_COMMANDS,
        activity_interactive_commands_error=ACTIVITY_INTERACTIVE_COMMANDS_ERROR,
        activity_simple_commands=ACTIVITY_SIMPLE_COMMANDS,
    )
    backup_service = BackupService()
    BackupScheduler.create(backup_service, BACKUP_SCHEDULE_JSON_FILE).install(app)
    template_repo = BulkTemplateRepository(template_file=TEMPLATE_FILE, default_encoding=DEFAULT_ENCODING)
    availability_service = AvailabilityReportService()
    uptime_service = DeviceUpTimeReportService()

    # ================= BULK RUN =================
    @app.post("/run")
    def run_bulk(
        operation: str = Form(...),
        file: UploadFile = File(...),
        config_name: str = Form(""),
        log_name: str = Form(""),
        current_user: dict = Depends(require_privilege("bulk_operations")),
    ):
        try:
            return bulk_service.run_bulk(
                operation=operation,
                upload_file=file,
                config_name=config_name,
                log_name=log_name,
                current_user=current_user,
            )
        except ValueError:
            raise HTTPException(400, ERROR_INVALID_OPERATION)

    @app.get("/bulk/template/{operation}")
    def download_bulk_template(
        operation: str,
        current_user: dict = Depends(require_privilege("bulk_operations")),
    ):
        templates = template_repo.load_templates()

        if operation not in templates:
            raise HTTPException(404, ERROR_UNKNOWN_TEMPLATE)

        df = pd.DataFrame(columns=templates[operation])

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Template")
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type=MEDIA_TYPE_EXCEL,
            headers={
                "Content-Disposition": f'attachment; filename="bulk_{operation}_template.xlsx"'
            },
        )

    # ================= ROUTER Config =================
    @app.post("/routers/run-interactive")
    def run_interactive(
        routers: str = Form(...),
        device_type_default: str = Form("cisco_ios"),
        tasks_json: str = Form(...),
        username: str = Form(""),
        password: str = Form(""),
        enable_password: str = Form(""),
        credential_id: str = Form(""),
        config_name: str = Form(""),
        log_name: str = Form(""),
        current_user: dict = Depends(require_privilege("router_commands")),
    ):
        u, p, en = resolve_ssh_for_router_run(
            current_user,
            credential_id or None,
            username,
            password,
            enable_password,
        )
        return router_service.run_interactive(
            routers=routers,
            device_type_default=device_type_default,
            tasks_json=tasks_json,
            username=u,
            password=p,
            enable_password=en,
            config_name=config_name,
            log_name=log_name,
            current_user=current_user,
            filename_service=filename_service,
        )

    @app.post("/routers/run-simple")
    def run_simple(
        routers: str = Form(...),
        config: str = Form(...),
        device_type_default: str = Form("cisco_ios"),
        username: str = Form(""),
        password: str = Form(""),
        enable_password: str = Form(""),
        credential_id: str = Form(""),
        config_name: str = Form(""),
        log_name: str = Form(""),
        current_user: dict = Depends(require_privilege("router_commands")),
    ):
        u, p, en = resolve_ssh_for_router_run(
            current_user,
            credential_id or None,
            username,
            password,
            enable_password,
        )
        return router_service.run_simple(
            routers=routers,
            config=config,
            device_type_default=device_type_default,
            username=u,
            password=p,
            enable_password=en,
            config_name=config_name,
            log_name=log_name,
            current_user=current_user,
            filename_service=filename_service,
        )

    # ================= SSH CREDENTIALS (eligible = metadata only; secrets server-side) =================
    @app.get("/credentials/eligible")
    def list_eligible_credentials(current_user: dict = Depends(get_current_user)):
        rows = ssh_credentials_repo.load_all(SSH_CREDENTIALS_FILE)
        allowed = get_allowed_credential_ids_for_user(current_user)
        if allowed is None:
            return [_credential_public_meta(c) for c in rows if c.get("id")]
        return [_credential_public_meta(c) for c in rows if c.get("id") in allowed]

    @app.get("/admin/credentials")
    def admin_list_credentials(current_user: dict = Depends(require_privilege("admin_access"))):
        log_activity(current_user["id"], "list_ssh_credentials", "Listed SSH credential vault", "admin")
        return ssh_credentials_repo.load_all(SSH_CREDENTIALS_FILE)

    @app.post("/admin/credentials")
    def admin_create_credential(
        name: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
        enable_password: str = Form(""),
        description: str = Form(""),
        current_user: dict = Depends(require_privilege("admin_access")),
    ):
        if not (password or "").strip():
            raise HTTPException(status_code=400, detail="Password is required for a new credential")
        try:
            payload = ssh_credentials_repo.validate_credential_payload(
                {
                    "name": name,
                    "username": username,
                    "password": password,
                    "enable_password": enable_password,
                    "description": description,
                },
                is_update=False,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        cid = str(uuid.uuid4())
        cred = {
            "id": cid,
            **payload,
            "updated_at": datetime.now().isoformat(),
        }
        ssh_credentials_repo.upsert(SSH_CREDENTIALS_FILE, cred)
        log_activity(
            current_user["id"],
            "create_ssh_credential",
            f"Created SSH credential set: {payload['name']}",
            "admin",
        )
        return cred

    @app.put("/admin/credentials/{credential_id}")
    def admin_update_credential(
        credential_id: str,
        name: str = Form(...),
        username: str = Form(...),
        password: Optional[str] = Form(None),
        enable_password: Optional[str] = Form(None),
        description: str = Form(""),
        current_user: dict = Depends(require_privilege("admin_access")),
    ):
        existing = ssh_credentials_repo.get_by_id(SSH_CREDENTIALS_FILE, credential_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Credential not found")
        p = existing.get("password") or ""
        if password is not None and str(password).strip():
            p = str(password)
        en = existing.get("enable_password") or ""
        if enable_password is not None and str(enable_password).strip():
            en = str(enable_password)
        cred = {
            "id": credential_id,
            "name": name.strip(),
            "username": username.strip(),
            "password": p,
            "enable_password": en,
            "description": (description or "").strip(),
            "updated_at": datetime.now().isoformat(),
        }
        if not cred["name"] or not cred["username"]:
            raise HTTPException(status_code=400, detail="Name and username are required")
        ssh_credentials_repo.upsert(SSH_CREDENTIALS_FILE, cred)
        log_activity(
            current_user["id"],
            "update_ssh_credential",
            f"Updated SSH credential set: {cred['name']}",
            "admin",
        )
        return cred

    @app.delete("/admin/credentials/{credential_id}")
    def admin_delete_credential(
        credential_id: str,
        current_user: dict = Depends(require_privilege("admin_access")),
    ):
        if not ssh_credentials_repo.delete_by_id(SSH_CREDENTIALS_FILE, credential_id):
            raise HTTPException(status_code=404, detail="Credential not found")
        users = load_users()
        changed = False
        for u in users:
            if user_has_admin_access(u):
                continue
            cids = u.get("credential_ids")
            if isinstance(cids, list) and credential_id in cids:
                u["credential_ids"] = [x for x in cids if x != credential_id]
                changed = True
        if changed:
            save_users(users)
        log_activity(
            current_user["id"],
            "delete_ssh_credential",
            f"Deleted SSH credential id: {credential_id}",
            "admin",
        )
        return {"status": "deleted"}

    # ================= AUTHENTICATION =================
    @app.post("/auth/login")
    def login(username: str = Form(...), password: str = Form(...)):
        username = (username or "").strip()
        local_user = get_user_by_username(username)
        if local_user and local_user.get("password_hash") and verify_password(password, local_user["password_hash"]):
            user = local_user
            print(f"[LOGIN] local auth success for {username}")
        else:
            print(f"[LOGIN] local auth failed for {username}, trying AD")
            try:
                user = ad_login_and_get_user(username=username, password=password)
            except Exception as e:
                print(f"[LOGIN] AD login exception for {username}: {e}")
                user = None
            if not user:
                print(f"[LOGIN] authentication failed for {username}")
                raise HTTPException(status_code=401, detail="Incorrect username or password")

        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user["id"]}, expires_delta=access_token_expires)
        log_activity(user["id"], "login", f"User {username} logged in", "login")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user.get("email", ""),
                "role": user["role"],
                "privileges": user.get("privileges", []),
                "credential_ids": user.get("credential_ids") if isinstance(user.get("credential_ids"), list) else [],
            },
        }

    @app.get("/auth/me")
    def get_current_user_info(current_user: dict = Depends(get_current_user)):
        return {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user.get("email", ""),
            "role": current_user["role"],
            "privileges": current_user.get("privileges", []),
            "credential_ids": current_user.get("credential_ids")
            if isinstance(current_user.get("credential_ids"), list)
            else [],
        }

    @app.get("/auth/check-page-access")
    def check_page_access(page: str, current_user: dict = Depends(get_current_user)):
        required_privilege = PAGE_PRIVILEGES.get(page)
        if not required_privilege:
            return {"has_access": False, "reason": "Unknown page"}
        has_access = check_privilege(current_user, required_privilege)
        return {
            "has_access": has_access,
            "required_privilege": required_privilege,
            "user_privileges": current_user.get("privileges", []),
        }

    # ================= ADMIN ENDPOINTS =================
    @app.get("/admin/users")
    def list_users_route(current_user: dict = Depends(require_privilege("admin_access"))):
        log_activity(current_user["id"], "list_users", "Viewed user list", "admin")
        users = load_users()
        return [
            {
                "id": u["id"],
                "username": u["username"],
                "email": u.get("email", ""),
                "role": u["role"],
                "privileges": u.get("privileges", []),
                "active": u.get("active", True),
                "created_at": u.get("created_at", ""),
                "credential_ids": u.get("credential_ids")
                if isinstance(u.get("credential_ids"), list)
                else [],
            }
            for u in users
        ]

    @app.post("/admin/users")
    def create_user_route(
        username: str = Form(...),
        password: str = Form(...),
        email: str = Form(""),
        role: str = Form("operator"),
        privileges_json: str = Form(""),
        credential_ids_json: str = Form(""),
        current_user: dict = Depends(require_privilege("admin_access")),
    ):
        users = load_users()
        if any(u["username"] == username for u in users):
            raise HTTPException(status_code=400, detail="Username already exists")

        if privileges_json and privileges_json.strip():
            try:
                privileges = json.loads(privileges_json)
                if not isinstance(privileges, list):
                    raise ValueError("Privileges must be a list")
                if len(privileges) == 0:
                    raise HTTPException(status_code=400, detail="At least one privilege must be selected")
                all_privileges = [p["id"] for p in AVAILABLE_PRIVILEGES]
                invalid = [p for p in privileges if p not in all_privileges]
                if invalid:
                    raise HTTPException(status_code=400, detail=f"Invalid privileges: {invalid}")
                if role not in ROLE_PRIVILEGES:
                    role = "custom"
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid privileges JSON: {str(e)}")
        else:
            if role not in ROLE_PRIVILEGES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid role. Must be one of: {', '.join(list(ROLE_PRIVILEGES.keys()) + ['custom'])}",
                )
            privileges = ROLE_PRIVILEGES.get(role, [])

        new_user = {
            "id": username.lower().replace(" ", "_"),
            "username": username,
            "email": email,
            "password_hash": get_password_hash(password),
            "role": role,
            "privileges": privileges,
            "active": True,
            "created_at": datetime.now().isoformat(),
        }

        if "admin_access" in privileges:
            new_user["credential_ids"] = []
        else:
            parsed = _parse_credential_ids_json(credential_ids_json)
            cid_list = parsed if parsed is not None else []
            _validate_credential_ids_exist(cid_list)
            new_user["credential_ids"] = cid_list

        users.append(new_user)
        save_users(users)

        log_activity(
            current_user["id"],
            "create_user",
            f"Created user: {username} with privileges: {', '.join(privileges)}",
            "admin",
        )

        return {
            "id": new_user["id"],
            "username": new_user["username"],
            "email": new_user["email"],
            "role": new_user["role"],
            "privileges": new_user["privileges"],
            "credential_ids": new_user.get("credential_ids", []),
        }

    @app.put("/admin/users/{user_id}")
    def update_user_route(
        user_id: str,
        username: Optional[str] = Form(None),
        email: Optional[str] = Form(None),
        role: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        active: Optional[bool] = Form(None),
        privileges_json: Optional[str] = Form(None),
        credential_ids_json: Optional[str] = Form(None),
        current_user: dict = Depends(require_privilege("admin_access")),
    ):
        users = load_users()
        user_index = None
        for i, u in enumerate(users):
            if u["id"] == user_id:
                user_index = i
                break
        if user_index is None:
            raise HTTPException(status_code=404, detail="User not found")

        user = users[user_index]

        if user.get("privileges", []).count("admin_access") > 0 and active is False:
            admin_count = sum(
                1 for u in users if "admin_access" in u.get("privileges", []) and u.get("active", True)
            )
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot deactivate the last admin user")

        if username is not None:
            if any(u["username"] == username and u["id"] != user_id for u in users):
                raise HTTPException(status_code=400, detail="Username already exists")
            user["username"] = username

        if email is not None:
            user["email"] = email

        if role is not None:
            if role != "custom" and role not in ROLE_PRIVILEGES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid role. Must be one of: {', '.join(list(ROLE_PRIVILEGES.keys()) + ['custom'])}",
                )
            user["role"] = role
            if privileges_json is None or privileges_json.strip() == "":
                if role in ROLE_PRIVILEGES:
                    user["privileges"] = ROLE_PRIVILEGES[role]

        if privileges_json is not None and privileges_json.strip():
            try:
                privileges = json.loads(privileges_json)
                if not isinstance(privileges, list):
                    raise ValueError("Privileges must be a list")
                if len(privileges) == 0:
                    raise HTTPException(status_code=400, detail="At least one privilege must be selected")
                all_privileges = [p["id"] for p in AVAILABLE_PRIVILEGES]
                invalid = [p for p in privileges if p not in all_privileges]
                if invalid:
                    raise HTTPException(status_code=400, detail=f"Invalid privileges: {invalid}")
                user["privileges"] = privileges
                if "admin_access" in privileges:
                    user["credential_ids"] = []
                if role is not None and role not in ROLE_PRIVILEGES:
                    user["role"] = "custom"
                elif role is None and user.get("role") not in ROLE_PRIVILEGES:
                    user["role"] = "custom"
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid privileges JSON: {str(e)}")

        if password is not None and password.strip():
            user["password_hash"] = get_password_hash(password)

        if active is not None:
            user["active"] = active

        if credential_ids_json is not None and str(credential_ids_json).strip():
            parsed = _parse_credential_ids_json(credential_ids_json)
            if parsed is None:
                parsed = []
            if "admin_access" in user.get("privileges", []):
                user["credential_ids"] = []
            else:
                _validate_credential_ids_exist(parsed)
                user["credential_ids"] = parsed

        users[user_index] = user
        save_users(users)

        log_activity(
            current_user["id"],
            "update_user",
            f"Updated user: {user_id} ({user.get('username', 'unknown')}) with privileges: {', '.join(user.get('privileges', []))}",
            "admin",
        )

        return {
            "id": user["id"],
            "username": user["username"],
            "email": user.get("email", ""),
            "role": user["role"],
            "privileges": user["privileges"],
            "active": user.get("active", True),
            "credential_ids": user.get("credential_ids") if isinstance(user.get("credential_ids"), list) else [],
        }

    @app.delete("/admin/users/{user_id}")
    def delete_user_route(user_id: str, current_user: dict = Depends(require_privilege("admin_access"))):
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")

        users = load_users()
        user = next((u for u in users if u["id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if "admin_access" in user.get("privileges", []):
            admin_count = sum(
                1 for u in users if "admin_access" in u.get("privileges", []) and u.get("active", True)
            )
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last admin user")

        users = [u for u in users if u["id"] != user_id]
        save_users(users)
        log_activity(current_user["id"], "delete_user", f"Deleted user: {user_id} ({user['username']})", "admin")
        return {"status": "deleted"}

    @app.get("/admin/activity")
    def get_activity_log_route(
        limit: int = 500,
        user_id: Optional[str] = None,
        current_user: dict = Depends(require_privilege("admin_access")),
    ):
        from auth import ACTIVITY_LOG_FILE

        if not ACTIVITY_LOG_FILE.exists():
            log_activity(current_user["id"], "view_activity_log", "Viewed activity log (empty)", "admin")
            return []

        try:
            with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []

        if user_id:
            logs = [log for log in logs if log.get("user_id") == user_id]

        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        result = logs[:limit]
        log_activity(current_user["id"], "view_activity_log", f"Viewed {len(result)} activity log entries", "admin")
        return result

    @app.get("/admin/stats")
    def get_admin_stats_route(current_user: dict = Depends(require_privilege("admin_access"))):
        users = load_users()
        from auth import ACTIVITY_LOG_FILE

        active_users = sum(1 for u in users if u.get("active", True))
        total_users = len(users)

        recent_activities = 0
        if ACTIVITY_LOG_FILE.exists():
            try:
                with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
                recent_activities = sum(1 for log in logs if log.get("timestamp", "") > cutoff)
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        return {
            "total_users": total_users,
            "active_users": active_users,
            "recent_activities_24h": recent_activities,
        }

    @app.get("/admin/privileges")
    def get_admin_privileges_list_route(current_user: dict = Depends(require_privilege("admin_access"))):
        from auth import AVAILABLE_PRIVILEGES as AUTH_AVAILABLE_PRIVILEGES

        return {"privileges": AUTH_AVAILABLE_PRIVILEGES, "page_privileges": PAGE_PRIVILEGES}

    @app.get("/admin/db-connection")
    def get_db_connection_settings(current_user: dict = Depends(require_privilege("admin_access"))):
        """Get current database connection string (admin only)."""
        return {"connection_string": get_connection_string()}

    @app.put("/admin/db-connection")
    def update_db_connection_settings(payload: dict = Body(...), current_user: dict = Depends(require_privilege("admin_access"))):
        """Update database connection string and persist it (admin only)."""
        value = (payload.get("connection_string") or "").strip()
        if not value:
            raise HTTPException(400, "connection_string is required")

        config_path = DATA_DIR / "db_connection.json"
        try:
            config_path.write_text(json.dumps({"connection_string": value}, indent=2), encoding="utf-8")
        except Exception as e:
            raise HTTPException(500, f"Failed to save connection string: {e}")

        log_activity(current_user["id"], "update_db_connection", "Updated database connection string", "admin")
        return {"status": "saved"}

    @app.get("/admin/bulk-templates")
    def get_bulk_templates_route(current_user: dict = Depends(require_privilege("admin_access"))):
        return template_repo.load_templates()

    @app.put("/admin/bulk-templates")
    def update_bulk_templates_route(payload: dict, current_user: dict = Depends(require_privilege("admin_access"))):
        for op, cols in payload.items():
            if not isinstance(cols, list) or not all(isinstance(c, str) for c in cols):
                raise HTTPException(400, f"Invalid columns for {op}")
        template_repo.save_templates(payload)
        return {"status": "ok"}

    # ================= VIEW / DELETE =================
    @app.get("/configs/{section}")
    def list_configs(section: str, current_user: dict = Depends(require_privilege("view_history"))):
        import os

        log_activity(current_user["id"], "list_configs", f"Listed configs in {section}", "history")
        return os.listdir(CONFIG_DIR / section)

    @app.get("/configs/{section}/{name}")
    def get_config(section: str, name: str, download: bool = False, current_user: dict = Depends(require_privilege("view_history"))):
        file_path = CONFIG_DIR / section / name
        if not file_path.exists():
            raise HTTPException(404, "File not found")
        log_activity(current_user["id"], "view_config", f"Viewed {section}/{name}", "history")
        if download:
            return FileResponse(path=str(file_path), filename=name, media_type="application/octet-stream")
        return file_path.read_text()

    @app.delete("/configs/{section}/{name}")
    def delete_config(section: str, name: str, current_user: dict = Depends(require_privilege("view_history"))):
        import os

        os.remove(CONFIG_DIR / section / name)
        log_activity(current_user["id"], "delete_config", f"Deleted {section}/{name}", "history")
        return {"status": "deleted"}

    @app.put("/configs/{section}/{name}")
    def rename_config(section: str, name: str, payload: dict = Body(...), current_user: dict = Depends(require_privilege("view_history"))):
        old_path = CONFIG_DIR / section / name
        new_name = payload.get("new_name", "").strip()
        if not new_name:
            raise HTTPException(400, "new_name is required")
        sanitized = filename_service.sanitize_filename(new_name)
        if not sanitized:
            raise HTTPException(400, "Invalid filename")
        old_ext = old_path.suffix
        new_path = CONFIG_DIR / section / f"{sanitized}{old_ext}"
        if new_path.exists():
            raise HTTPException(400, "File with this name already exists")
        if not old_path.exists():
            raise HTTPException(404, "File not found")
        old_path.rename(new_path)
        log_activity(current_user["id"], "rename_config", f"Renamed {section}/{name} to {sanitized}{old_ext}", "history")
        return {"status": "renamed", "new_name": f"{sanitized}{old_ext}"}

    @app.get("/logs")
    def list_logs(current_user: dict = Depends(require_privilege("view_history"))):
        import os

        log_activity(current_user["id"], "list_logs", "Listed log files", "history")
        return os.listdir(LOG_DIR)

    @app.get("/logs/{name}")
    def get_log(name: str, download: bool = False, current_user: dict = Depends(require_privilege("view_history"))):
        file_path = LOG_DIR / name
        if not file_path.exists():
            raise HTTPException(404, "File not found")
        log_activity(current_user["id"], "view_log", f"Viewed log: {name}", "history")
        if download:
            return FileResponse(path=str(file_path), filename=name, media_type="text/plain")
        return file_path.read_text()

    @app.delete("/logs/{name}")
    def delete_log(name: str, current_user: dict = Depends(require_privilege("view_history"))):
        import os

        os.remove(LOG_DIR / name)
        log_activity(current_user["id"], "delete_log", f"Deleted log: {name}", "history")
        return {"status": "deleted"}

    @app.put("/logs/{name}")
    def rename_log(name: str, payload: dict = Body(...), current_user: dict = Depends(require_privilege("view_history"))):
        old_path = LOG_DIR / name
        new_name = payload.get("new_name", "").strip()
        if not new_name:
            raise HTTPException(400, "new_name is required")
        sanitized = filename_service.sanitize_filename(new_name)
        if not sanitized:
            raise HTTPException(400, "Invalid filename")
        old_ext = old_path.suffix
        new_path = LOG_DIR / f"{sanitized}{old_ext}"
        if new_path.exists():
            raise HTTPException(400, "File with this name already exists")
        if not old_path.exists():
            raise HTTPException(404, "File not found")
        old_path.rename(new_path)
        log_activity(current_user["id"], "rename_log", f"Renamed log {name} to {sanitized}{old_ext}", "history")
        return {"status": "renamed", "new_name": f"{sanitized}{old_ext}"}

    # ================= Backup =================
    @app.get("/backups/devices")
    def list_backup_devices(current_user: dict = Depends(require_privilege("view_backups"))):
        if not BACKUP_BASE_DIR.exists():
            return []
        log_activity(current_user["id"], "list_backup_devices", "Listed backup devices", "backups")
        return [d.name for d in BACKUP_BASE_DIR.iterdir() if d.is_dir()]

    @app.get("/backups/{device}")
    def list_device_configs(device: str, current_user: dict = Depends(require_privilege("view_backups"))):
        device_dir = BACKUP_BASE_DIR / device
        if not device_dir.exists():
            raise HTTPException(404, "Device not found")
        log_activity(current_user["id"], "list_device_configs", f"Listed configs for {device}", "backups")
        return [f.name for f in device_dir.iterdir() if f.is_file()]

    @app.get("/backups/{device}/{filename}")
    def view_backup_file(device: str, filename: str, current_user: dict = Depends(require_privilege("view_backups"))):
        file_path = BACKUP_BASE_DIR / device / filename
        if not file_path.exists():
            raise HTTPException(404, "File not found")
        log_activity(current_user["id"], "view_backup", f"Viewed {device}/{filename}", "backups")
        return file_path.read_text(encoding="utf-8", errors="ignore")

    @app.post("/backups/run")
    def run_backups_now(current_user: dict = Depends(require_privilege("view_backups"))):
        # Synchronous run: captures stdout/stderr from the runner and returns it.
        log_activity(current_user["id"], "run_backups", "Triggered backup capture", "backups")
        result = backup_service.run_all_backups()
        return result

    @app.get("/backups/schedule")
    def get_backup_schedule(current_user: dict = Depends(require_privilege("view_backups"))):
        log_activity(current_user["id"], "view_backup_schedule", "Viewed backup schedule", "backups")
        return load_backup_schedule(BACKUP_SCHEDULE_JSON_FILE)

    @app.put("/backups/schedule")
    def put_backup_schedule(payload: dict = Body(...), current_user: dict = Depends(require_privilege("view_backups"))):
        try:
            validated = validate_backup_schedule(payload)
        except (ValueError, TypeError) as e:
            raise HTTPException(400, str(e))
        save_backup_schedule(BACKUP_SCHEDULE_JSON_FILE, validated)
        log_activity(
            current_user["id"],
            "save_backup_schedule",
            f"Updated backup schedule: enabled={validated['enabled']} mode={validated['mode']}",
            "backups",
        )
        return {"status": "saved", "schedule": validated}

    @app.get("/backup/routers")
    def get_backup_routers(current_user: dict = Depends(require_privilege("view_backups"))):
        if not ROUTERS_FILE.exists():
            return {"content": ""}
        log_activity(current_user["id"], "view_backup_routers", "Viewed backup routers list", "backups")
        return {"content": ROUTERS_FILE.read_text(encoding="utf-8")}

    @app.post("/backup/routers")
    def save_backup_routers(payload: dict = Body(...), current_user: dict = Depends(require_privilege("view_backups"))):
        content = payload.get("content", "")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        ROUTERS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log_activity(current_user["id"], "save_backup_routers", f"Updated backup routers list ({len(lines)} routers)", "backups")
        return {"status": "ok"}

    # ================= Scheduled Report Runner =================
    report_scheduler_enabled = os.environ.get("WUG_REPORT_SCHEDULER_ENABLED", "true").lower() == "true"
    report_scheduler_interval_seconds = int(os.environ.get("WUG_REPORT_SCHEDULER_INTERVAL_SECONDS", "300"))
    report_scheduler_task = {"task": None}

    async def _report_scheduler_loop():
        while True:
            try:
                await asyncio.to_thread(run_scheduled_reports)
            except Exception as e:
                print(f"[REPORT SCHEDULER] Error while running scheduled reports: {e}")
            await asyncio.sleep(report_scheduler_interval_seconds)

    @app.on_event("startup")
    async def _start_report_scheduler():
        if not report_scheduler_enabled:
            print("[REPORT SCHEDULER] Disabled via WUG_REPORT_SCHEDULER_ENABLED")
            return
        report_scheduler_task["task"] = asyncio.create_task(_report_scheduler_loop())
        print(f"[REPORT SCHEDULER] Started (interval={report_scheduler_interval_seconds}s)")

    @app.on_event("shutdown")
    async def _stop_report_scheduler():
        t = report_scheduler_task.get("task")
        if t is None:
            return
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
        report_scheduler_task["task"] = None
        print("[REPORT SCHEDULER] Stopped")

    # ================= Reporting =================
    @app.get("/reports/schedule")
    def get_report_schedule(current_user: dict = Depends(require_privilege("manage_reports"))):
        if REPORT_SCHEDULE_JSON_FILE.exists():
            try:
                raw = REPORT_SCHEDULE_JSON_FILE.read_text(encoding="utf-8")
                data = json.loads(raw)
                columns = data.get("columns")
                rows = data.get("rows")
                if not columns and rows:
                    columns = sorted({k for r in rows for k in r.keys()})
                log_activity(current_user["id"], "view_report_schedule", "Viewed report schedule (JSON)", "reports")
                return {"columns": columns or [], "rows": rows or []}
            except Exception as e:
                raise HTTPException(500, f"Failed to read JSON schedule: {e}")

        log_activity(current_user["id"], "view_report_schedule", "Viewed empty report schedule", "reports")
        default_columns = [
            "group",
            "availability_period",
            "availability_window_start",
            "availability_window_end",
            "uptime_period",
            "uptime_window_start",
            "uptime_window_end",
        ]
        return {"columns": default_columns, "rows": []}

    @app.post("/reports/schedule")
    def save_report_schedule(payload: dict, current_user: dict = Depends(require_privilege("manage_reports"))):
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            raise HTTPException(400, "rows must be a list")

        normalized_rows = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            rr = dict(r)
            if not rr.get("id"):
                rr["id"] = uuid.uuid4().hex
            normalized_rows.append(rr)

        columns = payload.get("columns")
        if not columns and normalized_rows:
            columns = sorted({k for r in normalized_rows for k in r.keys()})

        try:
            REPORT_SCHEDULE_JSON_FILE.write_text(
                json.dumps({"columns": columns or [], "rows": normalized_rows}, indent=2),
                encoding="utf-8",
            )
            log_activity(
                current_user["id"],
                "save_report_schedule",
                f"Updated report schedule with {len(normalized_rows)} entries (JSON)",
                "reports",
            )
            return {"status": "saved"}
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/reports/groups")
    def list_groups(current_user: dict = Depends(require_privilege("manage_reports"))):
        groups = availability_service.get_device_groups()
        log_activity(current_user["id"], "list_report_groups", "Viewed device groups for reports", "reports")
        return [{"id": gid, "name": name} for gid, name in groups]

    @app.post("/reports/manual")
    def generate_manual_report(
        group_id: int,
        group_name: str,
        start: str,
        end: str,
        current_user: dict = Depends(require_privilege("manage_reports")),
    ):
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            path = availability_service.write_excel_for_group(
                device_group_id=group_id, start_date=start_dt, end_date=end_dt, group_name=group_name
            )
            log_activity(current_user["id"], "manual_report", f"Generated report for {group_name} from {start} to {end}", "reports")
            import os
            return {"path": path, "filename": os.path.basename(path)}
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/reports/download")
    def download_report(path: str, current_user: dict = Depends(require_privilege("manage_reports"))):
        import os

        real_path = os.path.realpath(path)
        base_dir = os.path.realpath(str(OUTPUT_FOLDER))
        if not real_path.startswith(base_dir + os.sep):
            raise HTTPException(status_code=403, detail="Forbidden")
        if not os.path.exists(path):
            raise HTTPException(404, "File not found")
        log_activity(current_user["id"], "download_report", f"Downloaded report: {os.path.basename(path)}", "reports")
        return FileResponse(path, filename=os.path.basename(path))

    @app.post("/reports/uptime")
    def generate_uptime_report(
        group_id: int,
        group_name: str,
        start: str,
        end: str,
        current_user: dict = Depends(require_privilege("manage_reports")),
    ):
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            rows = uptime_service.run_sp_group_device_uptime(group_id, start_dt, end_dt)
            if not rows:
                raise HTTPException(400, f"No data found for group {group_id}")
            path = uptime_service.write_excel(group_name, rows, start_dt, end_dt)
            log_activity(current_user["id"], "uptime_report", f"Generated uptime report for {group_name} from {start} to {end}", "reports")
            import os
            return {"path": path, "filename": os.path.basename(path)}
        except Exception as e:
            raise HTTPException(500, str(e))

    return app

