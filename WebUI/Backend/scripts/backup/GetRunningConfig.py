from netmiko import ConnectHandler
from getpass import getpass
from pathlib import Path
from datetime import datetime
from ...constants import SSH_USERNAME, SSH_PASSWORD, SSH_ENABLE_PASSWORD
# ---------- SETTINGS ----------
ROUTER_LIST_FILE = "routers.txt"
OUTPUT_DIR = Path("backups")   # folder to store configs
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------- LOAD ROUTER IPs ----------
ips = []
for line in Path(ROUTER_LIST_FILE).read_text().splitlines():
   line = line.strip()
   if line and not line.startswith("#"):
       ips.append(line)

if not ips:
    print("No router IPs found in routers.txt")
    raise SystemExit(1)

print(f"Found {len(ips)} router(s) in {ROUTER_LIST_FILE}")

# ---------- CREDENTIALS ----------


# ---------- MAIN LOOP ----------
for ip in ips:
    print(f"\n=== Connecting to {ip} ===")

    device = {
        "device_type": "cisco_ios",
        "ip": ip,
        "username": SSH_USERNAME,
        "password": SSH_PASSWORD,
        "secret": SSH_ENABLE_PASSWORD,
    }

    folder = Path(f"./backups/{ip}")
    folder.mkdir(parents=True, exist_ok=True)
    try:
        conn = ConnectHandler(**device)
        conn.enable()  # enter enable mode if needed

        print(f"Getting running-config from {ip} ...")
        running_config = conn.send_command("show running-config", expect_string=r"#")

        conn.disconnect()

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = folder / f"running-config_{timestamp}.txt"

        filename.write_text(running_config, encoding="utf-8")
        print(f"Saved config to {filename}")

    except Exception as e:
        print(f"ERROR on {ip}: {e}")
