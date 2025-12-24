from pathlib import Path
import os

# Central config for backup scripts
BACKUP_OUTPUT_DIR = Path(os.environ.get("WUG_BACKUP_DIR", "backups"))

# Comma-separated list of router IPs or hostnames
ROUTER_LIST = [
    ip.strip() for ip in os.environ.get("WUG_BACKUP_ROUTERS", "10.216.191.213,12.100.7.92").split(",") if ip.strip()
]

USERNAME = os.environ.get("WUG_BACKUP_USER", "admin")
PASSWORD = os.environ.get("WUG_BACKUP_PASS", "maxor")
ENABLE_PASSWORD = os.environ.get("WUG_BACKUP_ENABLE", "MAXOR321")
