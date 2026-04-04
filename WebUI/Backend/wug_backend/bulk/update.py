from __future__ import annotations

import csv
import sys
import traceback

import pyodbc

from constants import get_connection_string


class BulkUpdateUseCase:
    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string

    def _connect(self):
        conn = pyodbc.connect(self._connection_string, autocommit=False)
        conn.autocommit = False
        return conn

    def _safe_str(self, v):
        if v is None:
            return None
        v = str(v).strip()
        return v if v != "" else None

    def _safe_int(self, v):
        v = self._safe_str(v)
        if not v:
            return None
        try:
            return int(v)
        except ValueError:
            return None

    def _find_device_id_by_name_group_ip(self, cursor, display_name, device_group, network_address):
        cursor.execute(
            """
        SELECT Device.nDeviceID
        FROM Device
        JOIN PivotDeviceToGroup
            ON Device.nDeviceID = PivotDeviceToGroup.nDeviceID
        JOIN DeviceGroup
            ON DeviceGroup.nDeviceGroupID = PivotDeviceToGroup.nDeviceGroupID
        JOIN NetworkInterface
            ON Device.nDeviceID = NetworkInterface.nDeviceID
        WHERE Device.sDisplayName = ?
          AND DeviceGroup.sGroupName = ?
          AND NetworkInterface.sNetworkAddress = ?;
    """,
            (display_name, device_group, network_address),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _update_device(self, cursor, device_id, new_display_name, note, device_type):
        set_parts = []
        params = []

        if new_display_name is not None:
            set_parts.append("sDisplayName = ?")
            params.append(new_display_name)
        if note is not None:
            set_parts.append("sNote = ?")
            params.append(note)
        if device_type is not None:
            set_parts.append("nDeviceTypeID = ?")
            params.append(device_type)
        if not set_parts:
            return 0

        params.append(device_id)
        sql = f"UPDATE Device SET {', '.join(set_parts)} WHERE nDeviceID = ?"
        cursor.execute(sql, params)
        return cursor.rowcount

    def _upsert_network_interface(self, cursor, device_id, ip_addr, net_name):
        if ip_addr is None and net_name is None:
            return 0

        set_parts = []
        params = []

        if ip_addr is not None:
            set_parts.append("sNetworkAddress = ?")
            params.append(ip_addr)
        if net_name is not None:
            set_parts.append("sNetworkName = ?")
            params.append(net_name)

        if set_parts:
            params.append(device_id)
            sql = f"UPDATE NetworkInterface SET {', '.join(set_parts)} WHERE nDeviceID = ?"
            cursor.execute(sql, params)

        if cursor.rowcount > 0:
            return cursor.rowcount

        insert_ip = ip_addr if ip_addr is not None else ""
        insert_name = net_name if net_name is not None else ""

        cursor.execute(
            """
        INSERT INTO NetworkInterface
            (nDeviceID, nPhysicalInterfaceID, nAddressType, bPollUsingNetworkName,
             sNetworkAddress, sNetworkName)
        VALUES (?, NULL, 1, 0, ?, ?);
    """,
            (device_id, insert_ip, insert_name),
        )
        return 1

    def _update_device_group(self, cursor, device_id, new_group_id):
        if new_group_id is None:
            return 0
        cursor.execute(
            """
        UPDATE PivotDeviceToGroup
        SET nDeviceGroupID = ?
        WHERE nDeviceID = ?;
    """,
            (new_group_id, device_id),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                """
            INSERT INTO PivotDeviceToGroup (nDeviceID, nDeviceGroupID)
            VALUES (?, ?);
        """,
                (device_id, new_group_id),
            )
            return 1
        return cursor.rowcount

    def _process_row(self, cursor, row_dict):
        device_id = self._find_device_id_by_name_group_ip(cursor, row_dict["sDisplayName"], row_dict["sDeviceGroup"], row_dict["sNetworkAddress"])

        if not device_id:
            return False, "Device not found by sDisplayName, sDeviceGroup, and sNetworkAddress"

        new_disp = row_dict.get("NewDisplayName")
        new_net_addr = row_dict.get("NewNetworkAddress")
        net_name = row_dict.get("NewNetworkName")
        note = row_dict.get("NewNotes")
        dev_type = self._safe_int(row_dict.get("NewDeviceType"))
        new_group = self._safe_int(row_dict.get("NewDeviceGroup"))

        dev_count = self._update_device(cursor, device_id, new_disp, note, dev_type)
        ni_count = self._upsert_network_interface(cursor, device_id, new_net_addr, net_name)
        grp_count = self._update_device_group(cursor, device_id, new_group)

        info = {
            "device_updated": dev_count,
            "network_if_updated_or_inserted": ni_count,
            "group_updated_or_inserted": grp_count,
        }
        return True, info

    def execute_from_csv_path(self, csv_path: str) -> int:
        def debug(msg):
            print(msg, flush=True)

        conn = self._connect()
        cur = conn.cursor()
        successes = 0
        failures = []

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            debug(f"CSV headers: {headers}")

            for i, row in enumerate(reader, start=1):
                debug(f"Processing row {i}: {row.get('sDisplayName', '')}")

                try:
                    ok, info = self._process_row(cur, row)
                    if ok:
                        conn.commit()
                        successes += 1
                    else:
                        conn.rollback()
                        failures.append((i, row.get("sDisplayName"), info))
                except Exception as e:
                    conn.rollback()
                    failures.append((i, row.get("sDisplayName"), str(e)))
                    print("ERROR: Error traceback:", file=sys.stderr)
                    print(traceback.format_exc(), file=sys.stderr, flush=True)

        cur.close()
        conn.close()

        print("Done.", flush=True)
        print(f"Successes: {successes}; Failures: {len(failures)}", flush=True)
        if failures:
            print("Failures detail:", file=sys.stderr)
            for f in failures:
                print(f, file=sys.stderr, flush=True)

        return 0


def run_bulk_update_cli(argv: list[str]) -> int:
    csv_path = argv[1]
    uc = BulkUpdateUseCase(connection_string=get_connection_string())
    return uc.execute_from_csv_path(csv_path)

