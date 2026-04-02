from __future__ import annotations

import csv
import sys
import traceback

import pyodbc

from constants import get_connection_string


class BulkDeleteUseCase:
    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string

    def _connect(self):
        conn = pyodbc.connect(self._connection_string, autocommit=False)
        conn.autocommit = False
        return conn

    def _find_device_by_both(self, cursor, name, addr):
        cursor.execute(
            """
        SELECT d.nDeviceID 
        FROM Device d
        JOIN NetworkInterface ni ON ni.nDeviceID = d.nDeviceID
        WHERE d.sDisplayName = ? AND ni.sNetworkAddress = ?
    """,
            name,
            addr,
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _find_device_by_display(self, cursor, name):
        cursor.execute("SELECT nDeviceID FROM Device WHERE sDisplayName = ?", name)
        row = cursor.fetchone()
        return row[0] if row else None

    def _find_device_by_address(self, cursor, addr):
        cursor.execute(
            """
        SELECT d.nDeviceID 
        FROM Device d
        JOIN NetworkInterface ni ON ni.nDeviceID = d.nDeviceID
        WHERE ni.sNetworkAddress = ?
    """,
            addr,
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _delete_device(self, cursor, device_id):
        cursor.execute("DELETE FROM PivotDeviceToGroup WHERE nDeviceID = ?", device_id)
        cursor.execute("DELETE FROM PivotActiveMonitorTypeToDevice WHERE nDeviceID = ?", device_id)
        cursor.execute("DELETE FROM DeviceAttribute WHERE nDeviceID = ?", device_id)
        cursor.execute("DELETE FROM Annotation WHERE nDeviceID = ?", device_id)
        cursor.execute("DELETE FROM NetworkInterface WHERE nDeviceID = ?", device_id)
        cursor.execute("DELETE FROM Device WHERE nDeviceID = ?", device_id)

    def execute_from_csv_path(self, csv_path: str) -> int:
        def debug(msg):
            print(msg, flush=True)

        conn = self._connect()
        cur = conn.cursor()

        successes = 0
        failures = []

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = [h.lower() for h in reader.fieldnames]

            mode = None
            if "sdisplayname" in headers and "snetworkaddress" in headers:
                mode = "both"
            elif "sdisplayname" in headers:
                mode = "display"
            elif "snetworkaddress" in headers:
                mode = "address"
            else:
                print("ERROR: CSV must contain sDisplayName OR sNetworkAddress.", file=sys.stderr)
                return 1

            for i, row in enumerate(reader, start=1):
                try:
                    name = row.get("sDisplayName") or row.get("sdisplayname")
                    addr = row.get("sNetworkAddress") or row.get("snetworkaddress")

                    device_id = None
                    if mode == "both":
                        device_id = self._find_device_by_both(cur, name, addr)
                    elif mode == "display":
                        device_id = self._find_device_by_display(cur, name)
                    else:
                        device_id = self._find_device_by_address(cur, addr)

                    if not device_id:
                        failures.append((i, name or addr, "Not found"))
                        continue

                    self._delete_device(cur, device_id)
                    conn.commit()
                    successes += 1
                    debug(f"Deleted device {device_id} ({name or addr})")

                except Exception as e:
                    conn.rollback()
                    failures.append((i, name or addr, str(e)))
                    print("ERROR: Error traceback:", file=sys.stderr)
                    print(traceback.format_exc(), file=sys.stderr, flush=True)

        cur.close()
        conn.close()

        print("Done.", flush=True)
        print(f"Successes: {successes}; Failures: {len(failures)}", flush=True)
        if failures:
            print("Failures:", file=sys.stderr)
            for f in failures:
                print(f, file=sys.stderr, flush=True)

        return 0


def run_bulk_delete_cli(argv: list[str]) -> int:
    csv_path = argv[1]
    uc = BulkDeleteUseCase(connection_string=get_connection_string())
    return uc.execute_from_csv_path(csv_path)

