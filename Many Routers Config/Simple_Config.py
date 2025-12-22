from netmiko import ConnectHandler
from pathlib import Path
from datetime import datetime
import os
import sys

# ---------- SETTINGS ----------
# ⬇️ CHANGE 1: paths come from API
ROUTER_LIST_FILE = os.environ.get("WUG_ROUTERS_FILE")
CONFIG_FILE = os.environ.get("WUG_CONFIG_FILE")

if not ROUTER_LIST_FILE or not CONFIG_FILE:
    sys.stderr.write("Missing input file paths from API\n")
    raise SystemExit(1)

base_dir = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = Path(os.path.join(base_dir, "bulk_sequence_logs"))
LOG_DIR.mkdir(exist_ok=True)

# ---------- LOAD ROUTER IPs ----------
ips = []

for line in Path(ROUTER_LIST_FILE).read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#"):
        ips.append(line)

if not ips:
    sys.stderr.write("No router IPs found\n")
    raise SystemExit(1)

sys.stderr.write(f"Found {len(ips)} router(s)\n")

# ---------- CREDENTIALS ----------
# ⬇️ CHANGE 2: creds from API
username = os.environ.get("WUG_SSH_USER")
password = os.environ.get("WUG_SSH_PASS")
enable_password = os.environ.get("WUG_SSH_ENABLE", password)

if not username or not password:
    sys.stderr.write("Missing SSH credentials\n")
    raise SystemExit(1)

# ---------- MAIN LOOP ----------
timestamp_global = datetime.now().strftime("%Y%m%d-%H%M%S")

for ip in ips:
    sys.stderr.write(f"\n=== Connecting to {ip} ===\n")

    device = {
        "device_type": "cisco_ios",
        "ip": ip,
        "username": username,
        "password": password,
        "secret": enable_password,
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
        sys.stderr.write(err_msg + "\n")
        log_file.write_text(err_msg, encoding="utf-8")
