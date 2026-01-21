# bulk_delete_wug.py
# Usage: python bulk_delete_wug.py devices_to_delete.csv

import csv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pyodbc
import traceback
from constants import CONNECTION_STRING

# ------------- CONFIG (edit) -------------
CSV_PATH = sys.argv[1]
# -----------------------------------------

def debug(msg): 
    print(msg, flush=True)

def connect():
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    conn.autocommit = False
    return conn

def find_device_by_both(cursor, name, addr):
    cursor.execute("""
        SELECT d.nDeviceID 
        FROM Device d
        JOIN NetworkInterface ni ON ni.nDeviceID = d.nDeviceID
        WHERE d.sDisplayName = ? AND ni.sNetworkAddress = ?
    """, name, addr)
    row = cursor.fetchone()
    return row[0] if row else None

def find_device_by_display(cursor, name):
    cursor.execute("SELECT nDeviceID FROM Device WHERE sDisplayName = ?", name)
    row = cursor.fetchone()
    return row[0] if row else None

def find_device_by_address(cursor, addr):
    cursor.execute("""
        SELECT d.nDeviceID 
        FROM Device d
        JOIN NetworkInterface ni ON ni.nDeviceID = d.nDeviceID
        WHERE ni.sNetworkAddress = ?
    """, addr)
    row = cursor.fetchone()
    return row[0] if row else None

def delete_device(cursor, device_id):
    # Order matters! Must delete dependencies first.

    cursor.execute("DELETE FROM PivotDeviceToGroup WHERE nDeviceID = ?", device_id)
    cursor.execute("DELETE FROM PivotActiveMonitorTypeToDevice WHERE nDeviceID = ?", device_id)
    cursor.execute("DELETE FROM DeviceAttribute WHERE nDeviceID = ?", device_id)
    cursor.execute("DELETE FROM Annotation WHERE nDeviceID = ?", device_id)
    cursor.execute("DELETE FROM NetworkInterface WHERE nDeviceID = ?", device_id)
    cursor.execute("DELETE FROM Device WHERE nDeviceID = ?", device_id)

def main():
    conn = connect()
    cur = conn.cursor()

    successes = 0
    failures = []

    with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
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
            sys.exit(1)

        for i, row in enumerate(reader, start=1):
            try:
                name = row.get("sDisplayName") or row.get("sdisplayname")
                addr = row.get("sNetworkAddress") or row.get("snetworkaddress")

                device_id = None
                if mode == "both":
                    device_id = find_device_by_both(cur, name, addr)
                elif mode == "display":
                    device_id = find_device_by_display(cur, name)
                else:
                    device_id = find_device_by_address(cur, addr)

                if not device_id:
                    failures.append((i, name or addr, "Not found"))
                    continue

                delete_device(cur, device_id)
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

if __name__ == "__main__":
    main()
