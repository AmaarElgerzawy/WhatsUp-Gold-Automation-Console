import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from netmiko import ConnectHandler
from datetime import datetime
import os
from constants import SSH_USERNAME, SSH_PASSWORD, SSH_ENABLE_PASSWORD

# ---------- SETTINGS ----------
# ⬇️ CHANGE 1: paths come from API
ROUTER_LIST_FILE = os.environ.get("WUG_ROUTERS_FILE")
CONFIG_FILE = os.environ.get("WUG_CONFIG_FILE")
DEVICE_TYPE_DEFAULT = (os.environ.get("WUG_DEVICE_TYPE_DEFAULT") or "cisco_ios").strip() or "cisco_ios"

if not ROUTER_LIST_FILE or not CONFIG_FILE:
    sys.stderr.write("Missing input file paths from API\n")
    raise SystemExit(1)

base_dir = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = Path(os.path.join(base_dir, "bulk_sequence_logs"))
LOG_DIR.mkdir(exist_ok=True)

# ---------- LOAD ROUTER IPs ----------
routers = []

def parse_router_line(line: str, default_device_type: str):
    """
    Accepts:
      - "1.2.3.4"
      - "1.2.3.4, juniper"
      - "1.2.3.4 | arista_eos"
      - "1.2.3.4 juniper"

    Returns: {"ip": "...", "device_type": "..."} or None
    """
    if not line:
        return None
    raw = line.strip()
    if not raw or raw.startswith("#"):
        return None

    normalized = raw.replace("|", ",").replace("\t", ",")
    parts = [p.strip() for p in normalized.split(",") if p.strip()]

    if len(parts) == 1:
        space_parts = [p for p in parts[0].split(" ") if p.strip()]
        if len(space_parts) >= 2:
            return {"ip": space_parts[0].strip(), "device_type": space_parts[1].strip()}
        return {"ip": parts[0], "device_type": default_device_type}

    ip = parts[0]
    dev = parts[1] if len(parts) >= 2 else default_device_type
    return {"ip": ip, "device_type": dev or default_device_type}

for line in Path(ROUTER_LIST_FILE).read_text().splitlines():
    parsed = parse_router_line(line, DEVICE_TYPE_DEFAULT)
    if parsed:
        routers.append(parsed)

if not routers:
    print("ERROR: No router IPs found", file=sys.stderr)
    sys.exit(1)

print(f"Found {len(routers)} router(s)")
# ---------- MAIN LOOP ----------
timestamp_global = datetime.now().strftime("%Y%m%d-%H%M%S")

for r in routers:
    ip = r["ip"]
    device_type = (r.get("device_type") or DEVICE_TYPE_DEFAULT).strip() or DEVICE_TYPE_DEFAULT
    print(f"\n=== Connecting to {ip} ({device_type}) ===")

    device = {
        "device_type": device_type,
        "ip": ip,
        "username": SSH_USERNAME,
        "password": SSH_PASSWORD,
        "secret": SSH_ENABLE_PASSWORD,
    }

    log_file = LOG_DIR / f"{ip}_push_{timestamp_global}.log"

    try:
        conn = ConnectHandler(**device)
        conn.enable()

        # ⬇️ SAME LOGIC, SAME FUNCTION
        output = conn.send_config_from_file(CONFIG_FILE)

        conn.disconnect()

        # ⬇️ CHANGE 3: make output visible to API/UI
        print(output, flush=True)

        # log_file.write_text(output, encoding="utf-8")

    except Exception as e:
        err_msg = f"ERROR on {ip}: {e}"
        print(err_msg, file=sys.stderr)
        # log_file.write_text(err_msg, encoding="utf-8")
