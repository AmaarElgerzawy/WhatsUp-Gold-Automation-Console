from __future__ import annotations

import json
import os
import sys
from datetime import datetime

from wug_backend.routers.interactive import InteractiveCommandRunner
from wug_backend.routers.simple import RouterListParser


def main() -> None:
    router_list_text = os.environ.get("WUG_ROUTERS")
    tasks_text = os.environ.get("WUG_TASKS")
    device_type_default = (os.environ.get("WUG_DEVICE_TYPE_DEFAULT") or "cisco_ios").strip() or "cisco_ios"

    if not router_list_text:
        print("ERROR: No routers data provided", file=sys.stderr)
        raise SystemExit(1)

    parser = RouterListParser()
    routers = parser.parse_from_text(router_list_text, device_type_default)
    if not routers:
        print("ERROR: No router IPs found", file=sys.stderr)
        raise SystemExit(1)

    print(f"Found {len(routers)} router(s)")

    if not tasks_text:
        print("ERROR: No tasks data provided", file=sys.stderr)
        raise SystemExit(1)

    try:
        tasks = json.loads(tasks_text)
    except Exception as e:
        print(f"ERROR: Could not parse tasks JSON: {e}", file=sys.stderr)
        raise SystemExit(1)

    if not isinstance(tasks, list):
        print("ERROR: Tasks must contain a JSON list.", file=sys.stderr)
        raise SystemExit(1)

    print(f"Loaded {len(tasks)} task(s)")

    timestamp_global = datetime.now().strftime("%Y%m%d-%H%M%S")
    runner = InteractiveCommandRunner()

    for r in routers:
        log_output = ""
        try:
            log_output = runner.execute_tasks(r, tasks=tasks, device_type_default=device_type_default, timestamp_global=timestamp_global)
            print(log_output, end="")
            print(f"Done with {r.ip} ({r.ip})")
        except Exception as e:
            err_msg = f"ERROR on {r.ip}: {e}"
            print(err_msg, file=sys.stderr)
            log_output += "\n" + err_msg + "\n"
            print(log_output, end="")


if __name__ == "__main__":
    main()

