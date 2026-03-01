from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer
from typing import Optional
import pandas as pd
import subprocess
import tempfile
import pyodbc
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import json
import io

# Import auth module
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
)

# Import constants
from constants import (
    ALLOWED_ORIGINS,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    BASEDIR,
    SCRIPTS_DIR,
    BULK_SCRIPTS_DIR,
    ROUTER_SCRIPTS_DIR,
    BACKUP_SCRIPTS_DIR,
    REPORTING_SCRIPTS_DIR,
    DATA_DIR,
    CONFIG_DIR,
    LOG_DIR,
    BACKUP_BASE_DIR,
    CONFIG_BULK_ADD_DIR,
    CONFIG_BULK_UPDATE_DIR,
    CONFIG_BULK_DELETE_DIR,
    CONFIG_ROUTER_SIMPLE_DIR,
    CONFIG_ROUTER_INTERACTIVE_DIR,
    TEMPLATE_FILE,
    ROUTERS_FILE,
    REPORT_SCHEDULE_FILE,
    SCRIPTS,
    CSV_NAMES,
    ENV_WUG_ROUTERS,
    ENV_WUG_TASKS,
    ENV_WUG_SSH_USER,
    ENV_WUG_SSH_PASS,
    ENV_WUG_SSH_ENABLE,
    CONTENT_TYPE_JSON,
    CONTENT_TYPE_FORM_URLENCODED,
    MEDIA_TYPE_EXCEL,
    DEFAULT_ENCODING,
    ENCODING_UTF8_SIG,
    QUERY_DEVICE_TYPES,
    QUERY_DEVICE_GROUPS,
    ERROR_INVALID_OPERATION,
    ERROR_UNKNOWN_TEMPLATE,
    LOG_FILE_PREFIX_BULK,
    LOG_FILE_PREFIX_INTERACTIVE,
    LOG_FILE_PREFIX_SIMPLE,
    ACTIVITY_BULK_OPERATION,
    ACTIVITY_INTERACTIVE_COMMANDS,
    ACTIVITY_INTERACTIVE_COMMANDS_ERROR,
    ACTIVITY_SIMPLE_COMMANDS,
    ACTIVITY_SIMPLE_COMMANDS_ERROR,
    CONFIG_PREFIX_BULK,
    CONFIG_PREFIX_INTERACTIVE,
    CONFIG_PREFIX_SIMPLE,
    WORKDIR_PLACEHOLDER,
    LOG_PREFIX_EXIT_CODE,
    LOG_PREFIX_STDOUT,
    LOG_PREFIX_STDERR,
    get_connection_string,
)

from scripts.reporting.ReportExcel import get_device_groups, write_excel_for_group, run_scheduled_reports
from scripts.reporting.DeviceUpTimeReport import run_sp_group_device_uptime, write_excel

# ================= INITIALIZATION =================
# Ensure data directories exist
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

# Security for optional auth endpoints
security = HTTPBearer(auto_error=False)

# ================= HELPERS =================
def collect_logs(src_dir: Path, dest_dir: Path):
    if not src_dir.exists():
        return

    for file in src_dir.glob("*.log"):
        shutil.copy(file, dest_dir / file.name)

def timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def sanitize_filename(name: str) -> str:
    """Sanitize a filename by removing/replacing invalid characters."""
    if not name:
        return ""
    # Remove invalid filename characters
    invalid_chars = '<>:"/\\|?*'
    sanitized = name.strip()
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized

def generate_filename(base_name: str, extension: str, custom_name: str = None) -> str:
    """Generate a filename with custom name or timestamp fallback."""
    if custom_name and custom_name.strip():
        sanitized = sanitize_filename(custom_name.strip())
        if sanitized:
            return f"{sanitized}.{extension}"
    # Fallback to timestamp
    return f"{timestamp()}.{extension}"

def save_file(path: Path, content: str):
    with open(path, "w", encoding=DEFAULT_ENCODING) as f:
        f.write(content)

def sanitize_output(text: str) -> str:
    if not text:
        return ""
    # Remove sensitive paths from output
    text = text.replace(str(ROUTER_SCRIPTS_DIR), WORKDIR_PLACEHOLDER)
    text = text.replace(str(BULK_SCRIPTS_DIR), WORKDIR_PLACEHOLDER)
    text = text.replace(str(BACKUP_SCRIPTS_DIR), WORKDIR_PLACEHOLDER)
    text = text.replace(str(REPORTING_SCRIPTS_DIR), WORKDIR_PLACEHOLDER)
    return text

def save_log(name, stdout, stderr, code, log_name: str = None):
    """Save log file with optional custom name."""
    if log_name and log_name.strip():
        filename = generate_filename("log", "log", log_name)
    else:
        filename = f"{timestamp()}_{name}.log"
    path = LOG_DIR / filename
    save_file(path, f"{LOG_PREFIX_EXIT_CODE} {code}\n\n{LOG_PREFIX_STDOUT}\n{stdout}\n\n{LOG_PREFIX_STDERR}\n{stderr}")

def load_templates():
    return json.loads(TEMPLATE_FILE.read_text(encoding=DEFAULT_ENCODING))

def save_templates(data):
    TEMPLATE_FILE.write_text(
        json.dumps(data, indent=2),
        encoding=DEFAULT_ENCODING
    )
# ================= DB HELPERS =================
def get_conn():
    return pyodbc.connect(get_connection_string())

def load_device_types():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(QUERY_DEVICE_TYPES)
    data = {r.sDisplayName.strip(): r.nDeviceTypeID for r in cur.fetchall()}
    conn.close()
    return data

def load_device_groups():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(QUERY_DEVICE_GROUPS)
    data = {r.sGroupName.strip(): r.nDeviceGroupID for r in cur.fetchall()}
    conn.close()
    return data

# ================= BULK RUN =================
@app.post("/run")
def run_bulk(
    operation: str = Form(...),
    file: UploadFile = File(...),
    config_name: str = Form(""),
    log_name: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    if operation not in SCRIPTS:
        raise HTTPException(400, ERROR_INVALID_OPERATION)

    df = pd.read_excel(file.file)
    device_types = load_device_types()
    device_groups = load_device_groups()

    if operation == "add":
        df["DeviceType"] = df["DeviceType"].apply(lambda v: device_types.get(str(v).strip()))
        df["DeviceGroup"] = df["DeviceGroup"].apply(lambda v: device_groups.get(str(v).strip()))
    elif operation == "update":
        if "DeviceType" in df:
            df["DeviceType"] = df["DeviceType"].apply(
                lambda v: device_types.get(str(v).strip()) if pd.notna(v) else v
            )
        if "GroupName" in df:
            df["GroupName"] = df["GroupName"].apply(
                lambda v: device_groups.get(str(v).strip()) if pd.notna(v) else v
            )
        if "NewDeviceGroup" in df:
            df["NewDeviceGroup"] = df["NewDeviceGroup"].apply(
                lambda v: device_groups.get(str(v).strip()) if pd.notna(v) else v
            )

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / CSV_NAMES[operation]
        df.to_csv(csv_path, index=False, encoding=ENCODING_UTF8_SIG)

        # SAVE CONFIG with custom name or timestamp
        config_filename = generate_filename(CONFIG_PREFIX_BULK, "csv", config_name)
        saved_cfg = CONFIG_DIR / f"bulk_{operation}" / config_filename
        df.to_csv(saved_cfg, index=False, encoding=ENCODING_UTF8_SIG)

        proc = subprocess.run(
            ["python", SCRIPTS[operation], str(csv_path)],
            capture_output=True,
            text=True
        )

        clean_stdout = sanitize_output(proc.stdout)
        clean_stderr = sanitize_output(proc.stderr)

        save_log("bulk_operation", clean_stdout, clean_stderr, proc.returncode, log_name)
        
        # Log activity
        log_activity(
            current_user["id"],
            ACTIVITY_BULK_OPERATION,
            f"Executed {operation} operation with {len(df)} devices",
            "bulk"
        )

        return {
            "returncode": proc.returncode,
            "stdout": clean_stdout,
            "stderr": clean_stderr,
        }

@app.get("/bulk/template/{operation}")
def download_bulk_template(operation: str):
    templates = load_templates()

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
    tasks_json: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    enable_password: str = Form(""),
    config_name: str = Form(""),
    log_name: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    script_path = str(ROUTER_SCRIPTS_DIR / "Interactive_Commands.py")

    # Prepare environment for the script
    env = os.environ.copy()
    env[ENV_WUG_ROUTERS] = routers
    env[ENV_WUG_TASKS] = tasks_json
    env[ENV_WUG_SSH_USER] = username
    env[ENV_WUG_SSH_PASS] = password
    env[ENV_WUG_SSH_ENABLE] = enable_password or password

    try:
        proc = subprocess.run(
            ["python", script_path],
            cwd=str(ROUTER_SCRIPTS_DIR),
            capture_output=True,
            text=True,
            env=env
        )
        
        SCRIPT_LOG_DIR = ROUTER_SCRIPTS_DIR / "bulk_sequence_logs"
        collect_logs(SCRIPT_LOG_DIR, LOG_DIR)
        
        # Save config with custom name or timestamp
        config_filename = generate_filename(CONFIG_PREFIX_INTERACTIVE, "txt", config_name)
        saved_cfg = CONFIG_ROUTER_INTERACTIVE_DIR / config_filename
        with open(saved_cfg, 'w') as file:
            json.dump(tasks_json, file, indent=2)
        
        # Save log with custom name or timestamp
        save_log(LOG_FILE_PREFIX_INTERACTIVE, proc.stdout, proc.stderr, proc.returncode, log_name)
        
        # Log activity
        router_count = len([r for r in routers.splitlines() if r.strip()])
        log_activity(
            current_user["id"],
            ACTIVITY_INTERACTIVE_COMMANDS,
            f"Ran Tasks on {router_count} router(s)",
            "routers"
        )
        
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    except Exception as e:
        log_activity(
            current_user["id"],
            ACTIVITY_INTERACTIVE_COMMANDS_ERROR,
            f"Error: {str(e)}",
            "routers"
        )
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }

@app.post("/routers/run-simple")
def run_simple(
    routers: str = Form(...),
    config: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    enable_password: str = Form(""),
    config_name: str = Form(""),
    log_name: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    script_path = str(ROUTER_SCRIPTS_DIR / "Simple_Config.py")

    with tempfile.TemporaryDirectory() as tmp:
        routers_file = os.path.join(tmp, "routers.txt")
        config_file = os.path.join(tmp, "config.txt")

        with open(routers_file, "w", encoding=DEFAULT_ENCODING) as f:
            f.write(routers)

        with open(config_file, "w", encoding=DEFAULT_ENCODING) as f:
            f.write(config)

        env = os.environ.copy()
        env["WUG_ROUTERS_FILE"] = routers_file
        env["WUG_CONFIG_FILE"] = config_file
        env["WUG_SSH_USER"] = username
        env["WUG_SSH_PASS"] = password
        env["WUG_SSH_ENABLE"] = enable_password or password

        proc = subprocess.run(
            ["python", script_path],
            cwd=str(ROUTER_SCRIPTS_DIR),
            capture_output=True,
            text=True,
            env=env
        )

        SCRIPT_LOG_DIR = ROUTER_SCRIPTS_DIR / "bulk_sequence_logs"
        collect_logs(SCRIPT_LOG_DIR, LOG_DIR)
        
        # Save config with custom name or timestamp
        config_filename = generate_filename(CONFIG_PREFIX_SIMPLE, "txt", config_name)
        saved_cfg = CONFIG_ROUTER_SIMPLE_DIR / config_filename
        shutil.copy(config_file, saved_cfg)

        # Save log with custom name or timestamp
        save_log(LOG_FILE_PREFIX_SIMPLE, proc.stdout, proc.stderr, proc.returncode, log_name)
        
        # Log activity
        router_count = len([r for r in routers.splitlines() if r.strip()])
        log_activity(
            current_user["id"],
            ACTIVITY_SIMPLE_COMMANDS,
            f"Ran simple config on {router_count} router(s)",
            "routers"
        )

        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

# ================= AUTHENTICATION =================
@app.post("/auth/login")
def login(username: str = Form(...), password: str = Form(...)):
    """Login endpoint."""
    user = get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    # Log login activity
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
        }
    }

@app.get("/auth/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user.get("email", ""),
        "role": current_user["role"],
        "privileges": current_user.get("privileges", []),
    }

@app.get("/auth/check-page-access")
def check_page_access(page: str, current_user: dict = Depends(get_current_user)):
    """Check if user has access to a page."""
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
def list_users(current_user: dict = Depends(require_privilege("admin_access"))):
    """List all users (admin only)."""
    log_activity(current_user["id"], "list_users", "Viewed user list", "admin")
    users = load_users()
    # Remove password hashes from response
    return [
        {
            "id": u["id"],
            "username": u["username"],
            "email": u.get("email", ""),
            "role": u["role"],
            "privileges": u.get("privileges", []),
            "active": u.get("active", True),
            "created_at": u.get("created_at", ""),
        }
        for u in users
    ]

@app.post("/admin/users")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(""),
    role: str = Form("operator"),
    privileges_json: str = Form(""),  # JSON array of privilege strings
    current_user: dict = Depends(require_privilege("admin_access")),
):
    """Create a new user (admin only)."""
    users = load_users()
    
    # Check if username already exists
    if any(u["username"] == username for u in users):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Parse privileges from JSON, or use role defaults
    # Always prioritize privileges_json if provided
    if privileges_json and privileges_json.strip():
        try:
            privileges = json.loads(privileges_json)
            if not isinstance(privileges, list):
                raise ValueError("Privileges must be a list")
            if len(privileges) == 0:
                raise HTTPException(status_code=400, detail="At least one privilege must be selected")
            # Validate privileges
            all_privileges = [p["id"] for p in AVAILABLE_PRIVILEGES]
            invalid = [p for p in privileges if p not in all_privileges]
            if invalid:
                raise HTTPException(status_code=400, detail=f"Invalid privileges: {invalid}")
            # When custom privileges are provided, always use them regardless of role
            # Set role to "custom" if it's not a standard role
            if role not in ROLE_PRIVILEGES:
                role = "custom"
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid privileges JSON: {str(e)}")
    else:
        # Use role defaults only if no custom privileges provided
        if role not in ROLE_PRIVILEGES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(list(ROLE_PRIVILEGES.keys()) + ['custom'])}")
        privileges = ROLE_PRIVILEGES.get(role, [])
    
    new_user = {
        "id": username.lower().replace(" ", "_"),
        "username": username,
        "email": email,
        "password_hash": get_password_hash(password),
        "role": role,  # Keep role for backward compatibility
        "privileges": privileges,
        "active": True,
        "created_at": datetime.now().isoformat(),
    }
    
    users.append(new_user)
    save_users(users)
    
    log_activity(
        current_user["id"],
        "create_user",
        f"Created user: {username} with privileges: {', '.join(privileges)}",
        "admin"
    )
    
    return {
        "id": new_user["id"],
        "username": new_user["username"],
        "email": new_user["email"],
        "role": new_user["role"],
        "privileges": new_user["privileges"],
    }

@app.put("/admin/users/{user_id}")
def update_user(
    user_id: str,
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    active: Optional[bool] = Form(None),
    privileges_json: Optional[str] = Form(None),
    current_user: dict = Depends(require_privilege("admin_access")),
):
    """Update a user (admin only)."""
    users = load_users()
    user_index = None
    
    for i, u in enumerate(users):
        if u["id"] == user_id:
            user_index = i
            break
    
    if user_index is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users[user_index]
    
    # Prevent deleting the last admin
    if user.get("privileges", []).count("admin_access") > 0 and active is False:
        admin_count = sum(1 for u in users if "admin_access" in u.get("privileges", []) and u.get("active", True))
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last admin user")
    
    if username is not None:
        # Check if new username conflicts
        if any(u["username"] == username and u["id"] != user_id for u in users):
            raise HTTPException(status_code=400, detail="Username already exists")
        user["username"] = username
    
    if email is not None:
        user["email"] = email
    
    if role is not None:
        # Allow "custom" role and any standard role
        if role != "custom" and role not in ROLE_PRIVILEGES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(list(ROLE_PRIVILEGES.keys()) + ['custom'])}")
        user["role"] = role
        # Only update privileges from role if custom privileges not provided
        if privileges_json is None or privileges_json.strip() == "":
            if role in ROLE_PRIVILEGES:
                user["privileges"] = ROLE_PRIVILEGES[role]
            # If role is "custom" and no privileges provided, keep existing privileges
    
    # Update privileges if provided (takes precedence over role)
    if privileges_json is not None and privileges_json.strip():
        try:
            privileges = json.loads(privileges_json)
            if not isinstance(privileges, list):
                raise ValueError("Privileges must be a list")
            if len(privileges) == 0:
                raise HTTPException(status_code=400, detail="At least one privilege must be selected")
            # Validate privileges
            all_privileges = [p["id"] for p in AVAILABLE_PRIVILEGES]
            invalid = [p for p in privileges if p not in all_privileges]
            if invalid:
                raise HTTPException(status_code=400, detail=f"Invalid privileges: {invalid}")
            user["privileges"] = privileges
            # If custom privileges provided, update role to "custom" if it's not a standard role
            if role is not None and role not in ROLE_PRIVILEGES:
                user["role"] = "custom"
            elif role is None and user.get("role") not in ROLE_PRIVILEGES:
                # If no role specified but user has custom privileges, set role to custom
                user["role"] = "custom"
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid privileges JSON: {str(e)}")
    
    if password is not None and password.strip():
        user["password_hash"] = get_password_hash(password)
    
    if active is not None:
        user["active"] = active
    
    users[user_index] = user
    save_users(users)
    
    log_activity(
        current_user["id"],
        "update_user",
        f"Updated user: {user_id} ({user.get('username', 'unknown')}) with privileges: {', '.join(user.get('privileges', []))}",
        "admin"
    )
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email", ""),
        "role": user["role"],
        "privileges": user["privileges"],
        "active": user.get("active", True),
    }

@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: dict = Depends(require_privilege("admin_access")),
):
    """Delete a user (admin only)."""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    users = load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting the last admin (user with admin_access privilege)
    if "admin_access" in user.get("privileges", []):
        admin_count = sum(1 for u in users if "admin_access" in u.get("privileges", []) and u.get("active", True))
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin user")
    
    users = [u for u in users if u["id"] != user_id]
    save_users(users)
    
    log_activity(
        current_user["id"],
        "delete_user",
        f"Deleted user: {user_id} ({user['username']})",
        "admin"
    )
    
    return {"status": "deleted"}

@app.get("/admin/activity")
def get_activity_log(
    limit: int = 500,
    user_id: Optional[str] = None,
    current_user: dict = Depends(require_privilege("admin_access")),
):
    """Get activity log (admin only)."""
    from auth import ACTIVITY_LOG_FILE
    
    if not ACTIVITY_LOG_FILE.exists():
        log_activity(current_user["id"], "view_activity_log", "Viewed activity log (empty)", "admin")
        return []
    
    try:
        with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        if not isinstance(logs, list):
            logs = []
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logs = []
    
    # Filter by user if specified
    if user_id:
        logs = [log for log in logs if log.get("user_id") == user_id]
    
    # Sort by timestamp (most recent first) and return limited results
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    result = logs[:limit]
    
    log_activity(current_user["id"], "view_activity_log", f"Viewed {len(result)} activity log entries", "admin")
    return result

@app.get("/admin/stats")
def get_admin_stats(current_user: dict = Depends(require_privilege("admin_access"))):
    """Get admin statistics."""
    users = load_users()
    from auth import ACTIVITY_LOG_FILE
    
    active_users = sum(1 for u in users if u.get("active", True))
    total_users = len(users)
    
    # Count activities in last 24 hours
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
def get_admin_privileges_list(current_user: dict = Depends(require_privilege("admin_access"))):
    """Get list of available privileges with their descriptions."""
    from auth import AVAILABLE_PRIVILEGES
    return {
        "privileges": AVAILABLE_PRIVILEGES,
        "page_privileges": PAGE_PRIVILEGES,
    }


@app.get("/admin/db-connection")
def get_db_connection_settings(
    current_user: dict = Depends(require_privilege("admin_access")),
):
    """Get current database connection string (admin only)."""
    return {
        "connection_string": get_connection_string(),
    }


@app.put("/admin/db-connection")
def update_db_connection_settings(
    payload: dict = Body(...),
    current_user: dict = Depends(require_privilege("admin_access")),
):
    """Update database connection string and persist it (admin only)."""
    value = (payload.get("connection_string") or "").strip()
    if not value:
        raise HTTPException(400, "connection_string is required")

    config_path = DATA_DIR / "db_connection.json"
    try:
        config_path.write_text(
            json.dumps({"connection_string": value}, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to save connection string: {e}")

    log_activity(
        current_user["id"],
        "update_db_connection",
        "Updated database connection string",
        "admin",
    )

    return {"status": "saved"}

@app.get("/admin/bulk-templates")
def get_bulk_templates(current_user: dict = Depends(require_privilege("admin_access"))):
    return load_templates()

@app.put("/admin/bulk-templates")
def update_bulk_templates(
    payload: dict,
    current_user: dict = Depends(require_privilege("admin_access"))
):
    # Basic validation
    for op, cols in payload.items():
        if not isinstance(cols, list) or not all(isinstance(c, str) for c in cols):
            raise HTTPException(400, f"Invalid columns for {op}")

    save_templates(payload)
    return {"status": "ok"}

# ================= VIEW / DELETE =================
@app.get("/configs/{section}")
def list_configs(section: str, current_user: dict = Depends(get_current_user)):
    log_activity(current_user["id"], "list_configs", f"Listed configs in {section}", "history")
    return os.listdir(CONFIG_DIR / section)

@app.get("/configs/{section}/{name}")
def get_config(
    section: str, name: str, download: bool = False,
    current_user: dict = Depends(get_current_user)
):
    file_path = CONFIG_DIR / section / name
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    log_activity(current_user["id"], "view_config", f"Viewed {section}/{name}", "history")
    
    if download:
        return FileResponse(
            path=str(file_path),
            filename=name,
            media_type="application/octet-stream"
        )
    
    return file_path.read_text()

@app.delete("/configs/{section}/{name}")
def delete_config(section: str, name: str, current_user: dict = Depends(get_current_user)):
    os.remove(CONFIG_DIR / section / name)
    log_activity(current_user["id"], "delete_config", f"Deleted {section}/{name}", "history")
    return {"status": "deleted"}

@app.put("/configs/{section}/{name}")
def rename_config(
    section: str, name: str, payload: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    old_path = CONFIG_DIR / section / name
    new_name = payload.get("new_name", "").strip()
    
    if not new_name:
        raise HTTPException(400, "new_name is required")
    
    # Sanitize new name
    sanitized = sanitize_filename(new_name)
    if not sanitized:
        raise HTTPException(400, "Invalid filename")
    
    # Preserve extension
    old_ext = old_path.suffix
    new_path = CONFIG_DIR / section / f"{sanitized}{old_ext}"
    
    if new_path.exists():
        raise HTTPException(400, "File with this name already exists")
    
    if not old_path.exists():
        raise HTTPException(404, "File not found")
    
    old_path.rename(new_path)
    log_activity(
        current_user["id"],
        "rename_config",
        f"Renamed {section}/{name} to {sanitized}{old_ext}",
        "history"
    )
    return {"status": "renamed", "new_name": f"{sanitized}{old_ext}"}

@app.get("/logs")
def list_logs(current_user: dict = Depends(get_current_user)):
    log_activity(current_user["id"], "list_logs", "Listed log files", "history")
    return os.listdir(LOG_DIR)

@app.get("/logs/{name}")
def get_log(
    name: str, download: bool = False,
    current_user: dict = Depends(get_current_user)
):
    file_path = LOG_DIR / name
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    log_activity(current_user["id"], "view_log", f"Viewed log: {name}", "history")
    
    if download:
        return FileResponse(
            path=str(file_path),
            filename=name,
            media_type="text/plain"
        )
    
    return file_path.read_text()

@app.delete("/logs/{name}")
def delete_log(name: str, current_user: dict = Depends(get_current_user)):
    os.remove(LOG_DIR / name)
    log_activity(current_user["id"], "delete_log", f"Deleted log: {name}", "history")
    return {"status": "deleted"}

@app.put("/logs/{name}")
def rename_log(
    name: str, payload: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    old_path = LOG_DIR / name
    new_name = payload.get("new_name", "").strip()
    
    if not new_name:
        raise HTTPException(400, "new_name is required")
    
    # Sanitize new name
    sanitized = sanitize_filename(new_name)
    if not sanitized:
        raise HTTPException(400, "Invalid filename")
    
    # Preserve extension
    old_ext = old_path.suffix
    new_path = LOG_DIR / f"{sanitized}{old_ext}"
    
    if new_path.exists():
        raise HTTPException(400, "File with this name already exists")
    
    if not old_path.exists():
        raise HTTPException(404, "File not found")
    
    old_path.rename(new_path)
    log_activity(
        current_user["id"],
        "rename_log",
        f"Renamed log {name} to {sanitized}{old_ext}",
        "history"
    )
    return {"status": "renamed", "new_name": f"{sanitized}{old_ext}"}

# ================= Backup =================
@app.get("/backups/devices")
def list_backup_devices(current_user: dict = Depends(get_current_user)):
    if not BACKUP_BASE_DIR.exists():
        return []

    log_activity(current_user["id"], "list_backup_devices", "Listed backup devices", "backups")
    return [
        d.name for d in BACKUP_BASE_DIR.iterdir()
        if d.is_dir()
    ]

@app.get("/backups/{device}")
def list_device_configs(device: str, current_user: dict = Depends(get_current_user)):
    device_dir = BACKUP_BASE_DIR / device
    if not device_dir.exists():
        raise HTTPException(404, "Device not found")

    log_activity(current_user["id"], "list_device_configs", f"Listed configs for {device}", "backups")
    return [
        f.name for f in device_dir.iterdir()
        if f.is_file()
    ]

@app.get("/backups/{device}/{filename}")
def view_backup_file(
    device: str, filename: str,
    current_user: dict = Depends(get_current_user)
):
    file_path = BACKUP_BASE_DIR / device / filename

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    log_activity(current_user["id"], "view_backup", f"Viewed {device}/{filename}", "backups")
    return file_path.read_text(encoding="utf-8", errors="ignore")

@app.get("/backup/routers")
def get_backup_routers(current_user: dict = Depends(get_current_user)):
    if not ROUTERS_FILE.exists():
        return {"content": ""}

    log_activity(current_user["id"], "view_backup_routers", "Viewed backup routers list", "backups")
    return {
        "content": ROUTERS_FILE.read_text(encoding="utf-8")
    }

@app.post("/backup/routers")
def save_backup_routers(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    content = payload.get("content", "")

    # normalize newlines & strip junk
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]

    ROUTERS_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    log_activity(
        current_user["id"],
        "save_backup_routers",
        f"Updated backup routers list ({len(lines)} routers)",
        "backups"
    )
    return {"status": "ok"}

# ================= Scheduled Report Runner =================
# Controls for the background scheduler that executes due reports.
REPORT_SCHEDULER_ENABLED = os.environ.get("WUG_REPORT_SCHEDULER_ENABLED", "true").lower() == "true"
REPORT_SCHEDULER_INTERVAL_SECONDS = int(os.environ.get("WUG_REPORT_SCHEDULER_INTERVAL_SECONDS", "300"))

_report_scheduler_task = None


async def _report_scheduler_loop():
    """
    Background loop that periodically invokes run_scheduled_reports().
    This uses asyncio.to_thread so the FastAPI event loop stays responsive.
    """
    while True:
        try:
            await asyncio.to_thread(run_scheduled_reports)
        except Exception as e:
            # Basic logging to stderr; avoids needing a request-scoped user.
            print(f"[REPORT SCHEDULER] Error while running scheduled reports: {e}")
        await asyncio.sleep(REPORT_SCHEDULER_INTERVAL_SECONDS)


@app.on_event("startup")
async def _start_report_scheduler():
    global _report_scheduler_task

    if not REPORT_SCHEDULER_ENABLED:
        print("[REPORT SCHEDULER] Disabled via WUG_REPORT_SCHEDULER_ENABLED")
        return

    _report_scheduler_task = asyncio.create_task(_report_scheduler_loop())
    print(f"[REPORT SCHEDULER] Started (interval={REPORT_SCHEDULER_INTERVAL_SECONDS}s)")


@app.on_event("shutdown")
async def _stop_report_scheduler():
    global _report_scheduler_task

    if _report_scheduler_task is None:
        return

    _report_scheduler_task.cancel()
    try:
        await _report_scheduler_task
    except asyncio.CancelledError:
        pass
    _report_scheduler_task = None
    print("[REPORT SCHEDULER] Stopped")
# ================= Reporting =================
@app.get("/reports/schedule")
def get_report_schedule(current_user: dict = Depends(get_current_user)):
    if not REPORT_SCHEDULE_FILE.exists():
        raise HTTPException(404, "report_schedule.xlsx not found")

    df = pd.read_excel(REPORT_SCHEDULE_FILE)
    log_activity(current_user["id"], "view_report_schedule", "Viewed report schedule", "reports")

    return {
        "columns": list(df.columns),
        "rows": df.fillna("").to_dict(orient="records")
    }

@app.post("/reports/schedule")
def save_report_schedule(
    payload: dict,
    current_user: dict = Depends(require_privilege("manage_reports"))
):
    if not REPORT_SCHEDULE_FILE.exists():
        raise HTTPException(404, "report_schedule.xlsx not found")

    try:
        df = pd.DataFrame(payload["rows"])
        df.to_excel(REPORT_SCHEDULE_FILE, index=False)
        log_activity(
            current_user["id"],
            "save_report_schedule",
            f"Updated report schedule with {len(df)} entries",
            "reports"
        )
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/reports/groups")
def list_groups(current_user: dict = Depends(require_privilege("manage_reports"))):
    groups = get_device_groups()
    log_activity(
        current_user["id"],
        "list_report_groups",
        "Viewed device groups for reports",
        "reports"
    )
    return [{"id": gid, "name": name} for gid, name in groups]

@app.post("/reports/manual")
def generate_manual_report(
    group_id: int,
    group_name: str,
    start: str,
    end: str,
    current_user: dict = Depends(require_privilege("manage_reports"))
):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        path = write_excel_for_group(
            device_group_id=group_id,
            start_date=start_dt,
            end_date=end_dt,
            group_name=group_name
        )

        log_activity(
            current_user["id"],
            "manual_report",
            f"Generated report for {group_name} from {start} to {end}",
            "reports"
        )

        return {"path": path, "filename": os.path.basename(path)}

    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/reports/download")
def download_report(
    path: str,
):
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")

    return FileResponse(path, filename=os.path.basename(path))

@app.post("/reports/uptime")
def generate_uptime_report(
    group_id: int,
    group_name: str,
    start: str,
    end: str,
    current_user: dict = Depends(require_privilege("manage_reports"))
):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        # Get uptime data from DeviceUpTimeReport
        rows = run_sp_group_device_uptime(group_id, start_dt, end_dt)
        
        if not rows:
            raise HTTPException(400, f"No data found for group {group_id}")

        # Generate Excel file
        path = write_excel(group_name, rows, start_dt, end_dt)

        log_activity(
            current_user["id"],
            "uptime_report",
            f"Generated uptime report for {group_name} from {start} to {end}",
            "reports"
        )

        return {"path": path, "filename": os.path.basename(path)}

    except Exception as e:
        raise HTTPException(500, str(e))
