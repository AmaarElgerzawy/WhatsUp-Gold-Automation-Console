import csv, sys, pyodbc, traceback
from ....Backend.constants import CONNECTION_STRING

# ----------------- CONFIG --------------------
CSV_PATH = sys.argv[1]
# ---------------------------------------------

def debug(msg):
    print(msg, flush=True)

def connect():
    conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
    conn.autocommit = False
    return conn

def safe_str(v):
    if v is None:
        return None
    v = str(v).strip()
    return v if v != "" else None

def safe_int(v):
    v = safe_str(v)
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None

def find_device_id(cursor, display_name, group_name):
    """
    Find device by DisplayName + GroupName.
    """
    cursor.execute("""
        SELECT Device.nDeviceID
        FROM Device
        JOIN PivotDeviceToGroup
            ON Device.nDeviceID = PivotDeviceToGroup.nDeviceID
        JOIN DeviceGroup
            ON DeviceGroup.nDeviceGroupID = PivotDeviceToGroup.nDeviceGroupID
        WHERE Device.sDisplayName = ?
          AND DeviceGroup.sGroupName = ?;
    """, (display_name, group_name))
    row = cursor.fetchone()
    return row[0] if row else None

def update_device(cursor, device_id, note, device_type):
    """
    Update Device: sNote, nDeviceTypeID.
    Only updates columns that are not None.
    """
    set_parts = []
    params = []

    if note is not None:
        set_parts.append("sNote = ?")
        params.append(note)

    if device_type is not None:
        set_parts.append("nDeviceTypeID = ?")
        params.append(device_type)

    if not set_parts:
        return 0  # nothing to update

    params.append(device_id)
    sql = f"UPDATE Device SET {', '.join(set_parts)} WHERE nDeviceID = ?"
    cursor.execute(sql, params)
    return cursor.rowcount

def upsert_network_interface(cursor, device_id, ip_addr, net_name):
    """
    Update or insert NetworkInterface for the device.
    - Updates sNetworkAddress and sNetworkName.
    - If no interface exists for that device, inserts one.
    """
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

    # No interface existed: insert one
    insert_ip = ip_addr if ip_addr is not None else ""
    insert_name = net_name if net_name is not None else ""

    cursor.execute("""
        INSERT INTO NetworkInterface
            (nDeviceID, nPhysicalInterfaceID, nAddressType, bPollUsingNetworkName,
             sNetworkAddress, sNetworkName)
        VALUES (?, NULL, 1, 0, ?, ?);
    """, (device_id, insert_ip, insert_name))

    return 1

def update_device_group(cursor, device_id, new_group_id):
    """
    Update PivotDeviceToGroup.nDeviceGroupID for the device.
    If no record exists, insert one.
    """
    if new_group_id is None:
        return 0

    cursor.execute("""
        UPDATE PivotDeviceToGroup
        SET nDeviceGroupID = ?
        WHERE nDeviceID = ?;
    """, (new_group_id, device_id))

    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO PivotDeviceToGroup (nDeviceID, nDeviceGroupID)
            VALUES (?, ?);
        """, (device_id, new_group_id))
        return 1

    return cursor.rowcount

def process_row(cursor, row_dict):
    """
    row_dict keys (normalized):
      sDisplayName, sGroupName,
      NetworkAddress, NetworkName, Notes, DeviceType, NewDeviceGroup
    """
    disp = safe_str(row_dict.get("sDisplayName"))
    group_name = safe_str(row_dict.get("sGroupName"))

    if not disp or not group_name:
        return False, "sDisplayName or sGroupName missing"

    device_id = find_device_id(cursor, disp, group_name)
    if not device_id:
        return False, "Device not found (name+group)"

    ip_addr   = safe_str(row_dict.get("NetworkAddress"))
    net_name  = safe_str(row_dict.get("NetworkName"))
    note      = safe_str(row_dict.get("Notes"))
    dev_type  = safe_int(row_dict.get("DeviceType"))
    new_group = safe_int(row_dict.get("NewDeviceGroup"))

    dev_count = update_device(cursor, device_id, note, dev_type)
    ni_count  = upsert_network_interface(cursor, device_id, ip_addr, net_name)
    grp_count = update_device_group(cursor, device_id, new_group)

    info = {
        "device_updated": dev_count,
        "network_if_updated_or_inserted": ni_count,
        "group_updated_or_inserted": grp_count
    }
    return True, info

def main():
    conn = connect()
    cur = conn.cursor()
    successes = 0
    failures = []

    with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        debug(f"CSV headers: {headers}")

        for i, row in enumerate(reader, start=1):
            # normalize keys: handle sDisplayName/DisplayName, sGroupName/GroupName
            normalized = {}
            for k, v in row.items():
                key = (k or "").strip()
                kl = key.lower()

                if kl == "displayname":
                    key = "sDisplayName"
                elif kl == "sdisplayname":
                    key = "sDisplayName"
                elif kl in ("groupname", "sgroupname", "devicegroup", "devicegroupname"):
                    key = "sGroupName"
                else:
                    # keep other headers as-is:
                    # NetworkAddress, NetworkName, Notes, DeviceType, NewDeviceGroup
                    pass

                normalized[key] = v

            disp = normalized.get("sDisplayName") or ""
            debug(f"Processing row {i}: {disp}")

            try:
                ok, info = process_row(cur, normalized)
                if ok:
                    conn.commit()
                    successes += 1
                else:
                    conn.rollback()
                    failures.append((i, normalized.get("sDisplayName"), info))
            except Exception as e:
                conn.rollback()
                failures.append((i, normalized.get("sDisplayName"), str(e)))
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

if __name__ == "__main__":
    main()
