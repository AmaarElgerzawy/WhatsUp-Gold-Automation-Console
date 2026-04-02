from __future__ import annotations

import sys

from wug_backend.bulk.delete import run_bulk_delete_cli


def main() -> None:
    raise SystemExit(run_bulk_delete_cli(sys.argv))


if __name__ == "__main__":
    main()

