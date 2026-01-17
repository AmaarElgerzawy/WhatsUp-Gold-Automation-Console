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
    print("ERROR: No router IPs found", file=sys.stderr)
    sys.exit(1)

print(f"Found {len(ips)} router(s)")
# ---------- MAIN LOOP ----------
timestamp_global = datetime.now().strftime("%Y%m%d-%H%M%S")

for ip in ips:
    print(f"\n=== Connecting to {ip} ===")

    device = {
        "device_type": "cisco_ios",
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
