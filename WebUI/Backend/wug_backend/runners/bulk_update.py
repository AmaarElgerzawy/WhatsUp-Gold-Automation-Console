from __future__ import annotations

import sys

from wug_backend.bulk.update import run_bulk_update_cli


def main() -> None:
    raise SystemExit(run_bulk_update_cli(sys.argv))


if __name__ == "__main__":
    main()

