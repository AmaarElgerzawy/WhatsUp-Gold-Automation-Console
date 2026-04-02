from __future__ import annotations

import sys

from wug_backend.backup.backup_collector import run_running_cli


def main() -> None:
    raise SystemExit(run_running_cli(sys.argv))


if __name__ == "__main__":
    main()

