from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import subprocess
import tempfile
import pyodbc
import os
from pathlib import Path
from datetime import datetime
import shutil
import json

# ================= CONFIG =================
BASEDIR = Path(__file__).resolve().parent

BulkChangesBASE_DIR = BASEDIR / ".." / ".." / "Bulk Changes" / "code"
BulkCommandsBASEDIR = BASEDIR / ".." / ".." / "Many Routers Config"
CONFIG_BACKUP_DIR = BASEDIR / ".." / ".." / "CONFIG BACKUP"
BACKUP_BASE_DIR = CONFIG_BACKUP_DIR / "backups"
ROUTERS_FILE = CONFIG_BACKUP_DIR / "routers.txt"

DATA_DIR = BASEDIR / "data"
CONFIG_DIR = DATA_DIR / "configs"
LOG_DIR = DATA_DIR / "logs"

REPORT_SCHEDULE_FILE = BASEDIR / ".." / ".." / "Reporting" /"report_schedule.xlsx"


for d in [
    CONFIG_DIR / "bulk_add",
    CONFIG_DIR / "bulk_update",
    CONFIG_DIR / "bulk_delete",
    CONFIG_DIR / "router_simple",
    CONFIG_DIR / "router_interactive",
    LOG_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)

SCRIPTS = {
    "add": os.path.join(BulkChangesBASE_DIR, "BulkAdd-WUGv14.py"),
    "update": os.path.join(BulkChangesBASE_DIR, "BulkUpdate-WUGv14.py"),
    "delete": os.path.join(BulkChangesBASE_DIR, "BulkDelete-WUGv14.py"),
}

CSV_NAMES = {
    "add": "Add.csv",
    "update": "Update.csv",
    "delete": "Delete.csv",
}

CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=WhatsUp;"
    "Trusted_Connection=yes;"
)
# =========================================

app = FastAPI(title="WhatsUp Gold WebUI Wrapper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
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
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def sanitize_output(text: str) -> str:
    if not text:
        return ""
    return text.replace(str(BulkCommandsBASEDIR), "[WORKDIR]")

def save_log(name, stdout, stderr, code, log_name: str = None):
    """Save log file with optional custom name."""
    if log_name and log_name.strip():
        filename = generate_filename("log", "log", log_name)
    else:
        filename = f"{timestamp()}_{name}.log"
    path = LOG_DIR / filename
    save_file(path, f"EXIT CODE: {code}\n\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")

# ================= DB HELPERS =================
def get_conn():
    return pyodbc.connect(CONNECTION_STRING)

def load_device_types():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT nDeviceTypeID, sDisplayName FROM DeviceType")
    data = {r.sDisplayName.strip(): r.nDeviceTypeID for r in cur.fetchall()}
    conn.close()
    return data

def load_device_groups():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT nDeviceGroupID, sGroupName FROM DeviceGroup")
    data = {r.sGroupName.strip(): r.nDeviceGroupID for r in cur.fetchall()}
    conn.close()
    return data

# ================= BULK RUN =================
@app.post("/run")
def run_bulk(
    operation: str = Form(...),
    file: UploadFile = File(...),
    config_name: str = Form(""),
    log_name: str = Form("")
):
    if operation not in SCRIPTS:
        raise HTTPException(400, "Invalid operation")

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
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        # SAVE CONFIG with custom name or timestamp
        config_filename = generate_filename("bulk_config", "csv", config_name)
        saved_cfg = CONFIG_DIR / f"bulk_{operation}" / config_filename
        df.to_csv(saved_cfg, index=False, encoding="utf-8-sig")

        proc = subprocess.run(
            ["python", SCRIPTS[operation], str(csv_path)],
            capture_output=True,
            text=True
        )

        clean_stdout = sanitize_output(proc.stdout)
        clean_stderr = sanitize_output(proc.stderr)

        save_log("bulk_operation", clean_stdout, clean_stderr, proc.returncode, log_name)

        return {
            "returncode": proc.returncode,
            "stdout": clean_stdout,
            "stderr": clean_stderr,
        }

# ================= ROUTER Config =================
@app.post("/routers/run-interactive")
def run_interactive(
    routers: str = Form(...),
    tasks_json: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    enable_password: str = Form(""),
    config_name: str = Form(""),
    log_name: str = Form("")
):
    script_path = os.path.join(BulkCommandsBASEDIR, "Interactive_Commands.py")

    # Prepare environment for the script
    env = os.environ.copy()
    env["WUG_ROUTERS"] = routers
    env["WUG_TASKS"] = tasks_json
    env["WUG_SSH_USER"] = username
    env["WUG_SSH_PASS"] = password
    env["WUG_SSH_ENABLE"] = enable_password or password

    try:
        proc = subprocess.run(
            ["python", script_path],
            cwd=BulkCommandsBASEDIR,
            capture_output=True,
            text=True,
            env=env
        )
        
        SCRIPT_LOG_DIR = Path(BulkCommandsBASEDIR) / "bulk_sequence_logs"
        collect_logs(SCRIPT_LOG_DIR, LOG_DIR)
        
        # Save config with custom name or timestamp
        config_filename = generate_filename("interactive_config", "txt", config_name)
        saved_cfg = CONFIG_DIR / "router_interactive" / config_filename
        with open(saved_cfg, 'w') as file:
            json.dump(tasks_json, file, indent=2)
        
        # Save log with custom name or timestamp
        save_log("interactive_commands", proc.stdout, proc.stderr, proc.returncode, log_name)
        
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    except Exception as e:
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
    log_name: str = Form("")
):
    script_path = os.path.join(BulkCommandsBASEDIR, "Simple_Config.py")

    with tempfile.TemporaryDirectory() as tmp:
        routers_file = os.path.join(tmp, "routers.txt")
        config_file = os.path.join(tmp, "config.txt")

        with open(routers_file, "w", encoding="utf-8") as f:
            f.write(routers)

        with open(config_file, "w", encoding="utf-8") as f:
            f.write(config)

        env = os.environ.copy()
        env["WUG_ROUTERS_FILE"] = routers_file
        env["WUG_CONFIG_FILE"] = config_file
        env["WUG_SSH_USER"] = username
        env["WUG_SSH_PASS"] = password
        env["WUG_SSH_ENABLE"] = enable_password or password

        proc = subprocess.run(
            ["python", script_path],
            cwd=BulkCommandsBASEDIR,
            capture_output=True,
            text=True,
            env=env
        )

        SCRIPT_LOG_DIR = Path(BulkCommandsBASEDIR) / "bulk_sequence_logs"
        collect_logs(SCRIPT_LOG_DIR, LOG_DIR)
        
        # Save config with custom name or timestamp
        config_filename = generate_filename("simple_config", "txt", config_name)
        saved_cfg = CONFIG_DIR / "router_simple" / config_filename
        shutil.copy(config_file, saved_cfg)

        # Save log with custom name or timestamp
        save_log("simple_commands", proc.stdout, proc.stderr, proc.returncode, log_name)

        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

# ================= VIEW / DELETE =================
@app.get("/configs/{section}")
def list_configs(section: str):
    return os.listdir(CONFIG_DIR / section)

@app.get("/configs/{section}/{name}")
def get_config(section: str, name: str, download: bool = False):
    file_path = CONFIG_DIR / section / name
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    if download:
        return FileResponse(
            path=str(file_path),
            filename=name,
            media_type="application/octet-stream"
        )
    
    return file_path.read_text()

@app.delete("/configs/{section}/{name}")
def delete_config(section: str, name: str):
    os.remove(CONFIG_DIR / section / name)
    return {"status": "deleted"}

@app.put("/configs/{section}/{name}")
def rename_config(section: str, name: str, payload: dict = Body(...)):
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
    return {"status": "renamed", "new_name": f"{sanitized}{old_ext}"}

@app.get("/logs")
def list_logs():
    return os.listdir(LOG_DIR)

@app.get("/logs/{name}")
def get_log(name: str, download: bool = False):
    file_path = LOG_DIR / name
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    if download:
        return FileResponse(
            path=str(file_path),
            filename=name,
            media_type="text/plain"
        )
    
    return file_path.read_text()

@app.delete("/logs/{name}")
def delete_log(name: str):
    os.remove(LOG_DIR / name)
    return {"status": "deleted"}

@app.put("/logs/{name}")
def rename_log(name: str, payload: dict = Body(...)):
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
    return {"status": "renamed", "new_name": f"{sanitized}{old_ext}"}

# ================= Backup =================
@app.get("/backups/devices")
def list_backup_devices():
    if not BACKUP_BASE_DIR.exists():
        return []

    return [
        d.name for d in BACKUP_BASE_DIR.iterdir()
        if d.is_dir()
    ]

@app.get("/backups/{device}")
def list_device_configs(device: str):
    device_dir = BACKUP_BASE_DIR / device
    if not device_dir.exists():
        raise HTTPException(404, "Device not found")

    return [
        f.name for f in device_dir.iterdir()
        if f.is_file()
    ]

@app.get("/backups/{device}/{filename}")
def view_backup_file(device: str, filename: str):
    file_path = BACKUP_BASE_DIR / device / filename

    if not file_path.exists():
        raise HTTPException(404, "File not found")

    return file_path.read_text(encoding="utf-8", errors="ignore")

@app.get("/backup/routers")
def get_backup_routers():
    if not ROUTERS_FILE.exists():
        return {"content": ""}

    return {
        "content": ROUTERS_FILE.read_text(encoding="utf-8")
    }

@app.post("/backup/routers")
def save_backup_routers(payload: dict = Body(...)):
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

    return {"status": "ok"}
# ================= Reporting =================
@app.get("/reports/schedule")
def get_report_schedule():
    if not REPORT_SCHEDULE_FILE.exists():
        raise HTTPException(404, "report_schedule.xlsx not found")

    df = pd.read_excel(REPORT_SCHEDULE_FILE)

    return {
        "columns": list(df.columns),
        "rows": df.fillna("").to_dict(orient="records")
    }

@app.post("/reports/schedule")
def save_report_schedule(payload: dict):
    if not REPORT_SCHEDULE_FILE.exists():
        raise HTTPException(404, "report_schedule.xlsx not found")

    try:
        df = pd.DataFrame(payload["rows"])
        df.to_excel(REPORT_SCHEDULE_FILE, index=False)
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(500, str(e))

