from __future__ import annotations

import os
import sys

from wug_backend.routers.simple import RouterListParser, SimpleConfigPusher


def main() -> None:
    router_list_file = os.environ.get("WUG_ROUTERS_FILE")
    config_file = os.environ.get("WUG_CONFIG_FILE")
    device_type_default = (os.environ.get("WUG_DEVICE_TYPE_DEFAULT") or "cisco_ios").strip() or "cisco_ios"

    if not router_list_file or not config_file:
        sys.stderr.write("Missing input file paths from API\n")
        raise SystemExit(1)

    routers_text = open(router_list_file, "r", encoding="utf-8").read()
    parser = RouterListParser()
    routers = parser.parse_from_text(routers_text, device_type_default)

    if not routers:
        print("ERROR: No router IPs found", file=sys.stderr)
        raise SystemExit(1)

    print(f"Found {len(routers)} router(s)")
    pusher = SimpleConfigPusher()
    for r in routers:
        try:
            pusher.push_from_file(r, config_file=config_file, device_type_default=device_type_default)
        except Exception as e:
            err_msg = f"ERROR on {r.ip}: {e}"
            print(err_msg, file=sys.stderr)


if __name__ == "__main__":
    main()

