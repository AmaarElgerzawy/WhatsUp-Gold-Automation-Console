from __future__ import annotations

import sys

from wug_backend.bulk.add import run_bulk_add_cli


def main() -> None:
    raise SystemExit(run_bulk_add_cli(sys.argv))


if __name__ == "__main__":
    main()

