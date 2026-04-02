from __future__ import annotations

import csv
import sys

import pyodbc

from constants import (
    DEFAULT_BEST_STATE_ID,
    DEFAULT_WORST_STATE_ID,
    TEMP_DEFAULT_NETIF_ID,
    get_connection_string,
)


class BulkAddUseCase:
    def __init__(
        self,
        connection_string: str,
        worst_state_id: int = DEFAULT_WORST_STATE_ID,
        best_state_id: int = DEFAULT_BEST_STATE_ID,
        temp_default_netif_id: int = TEMP_DEFAULT_NETIF_ID,
    ) -> None:
        self._connection_string = connection_string
        self._worst_state_id = worst_state_id
        self._best_state_id = best_state_id
        self._temp_default_netif_id = temp_default_netif_id

        sql_template = """
SET NOCOUNT ON;

    INSERT INTO Device (
        sDisplayName, nDeviceTypeID, nDeviceMenuSetID, nDeviceWebMenuSetID,
        bSnmpManageable, sSnmpOID, bAssumedState, nWorstStateID,
        nBestStateID, nPollInterval, sNote, sStatus,
        sL2MainIPAddress, nActionPolicyID, bGatherPerformanceData,
        bFireActions, bRemoved, sMaintenanceSchedule,
        bManualMaintenanceMode, nUnAcknowledgedPassiveMonitors,
        nUnAcknowledgedActiveMonitors, bPollingOrder, nDefaultNetworkInterfaceID
    )
    VALUES (
        ?, ?, NULL, NULL,
        0, NULL, 0, {WORST},
        {BEST}, NULL, ?, NULL,
        NULL, NULL, 0,
        0, 0, NULL,
        0, 0,
        0, NULL, {TEMP_NETIF}
    );

    DECLARE @NewDeviceID INT = SCOPE_IDENTITY();

    INSERT INTO ActionPolicy (sPolicyName, bExecuteAll, bGlobalActionPolicy)
    VALUES (NULL, 1, 0);

    DECLARE @NewActionPolicyID INT = SCOPE_IDENTITY();

    UPDATE Device
    SET nActionPolicyID = @NewActionPolicyID
    WHERE nDeviceID = @NewDeviceID;

    INSERT INTO NetworkInterface (
        nDeviceID, nPhysicalInterfaceID, nAddressType,
        bPollUsingNetworkName, sNetworkAddress, sNetworkName
    )
    VALUES (
        @NewDeviceID, NULL, 1, 0, ?, ?
    );

    DECLARE @NewNetworkInterfaceID INT = SCOPE_IDENTITY();

    UPDATE Device
    SET nDefaultNetworkInterfaceID = @NewNetworkInterfaceID
    WHERE nDeviceID = @NewDeviceID;

    INSERT INTO DeviceAttribute (nDeviceID, sName, sValue)
        VALUES (@NewDeviceID, 'Contact', '');
    INSERT INTO DeviceAttribute (nDeviceID, sName, sValue)
        VALUES (@NewDeviceID, 'Location', '');
    INSERT INTO DeviceAttribute (nDeviceID, sName, sValue)
        VALUES (@NewDeviceID, 'Description', '');

    INSERT INTO PivotActiveMonitorTypeToDevice (
        nDeviceID, nActiveMonitorTypeID, nNetworkInterfaceID,
        bAssumedState, nMonitorStateID, dLastInternalStateTime,
        nActionPolicyID, nPollInterval,
        bGatherPerformanceData, bFireActions,
        bDisabled, bRemoved, sArgument, sComment, nCriticalPollingOrder
    )
    VALUES (
        @NewDeviceID, 2, @NewNetworkInterfaceID,
        0, 0, GETDATE(),
        @NewActionPolicyID, NULL,
        NULL, 0,
        0, 0, '', '', NULL
    );

    INSERT INTO PivotDeviceToGroup (nDeviceID, nDeviceGroupID)
        VALUES (@NewDeviceID, ?);

"""
        self._sql = sql_template.format(
            WORST=self._worst_state_id,
            BEST=self._best_state_id,
            TEMP_NETIF=self._temp_default_netif_id,
        )

    def execute_from_csv_path(self, csv_path: str) -> int:
        rows = []
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            print(f"ERROR: CSV empty or headers mismatch: {csv_path}", file=sys.stderr)
            return 1

        conn = pyodbc.connect(self._connection_string)
        cursor = conn.cursor()
        cursor.fast_executemany = False

        row_num = 0
        for r in rows:
            row_num += 1
            try:
                cursor.execute(
                    self._sql,
                    r["DisplayName"],
                    int(r["DeviceType"]),
                    r.get("Notes", ""),
                    r["NetworkAddress"],
                    r["NetworkName"],
                    int(r["DeviceGroup"]),
                )
                conn.commit()
                print(f"SUCCESS: Inserted row {row_num} - {r['DisplayName']}", flush=True)
            except Exception as e:
                conn.rollback()
                print(f"WARNING: Failed row {row_num} ({r['DisplayName']}): {e}", file=sys.stderr, flush=True)

        conn.close()
        return 0


def run_bulk_add_cli(argv: list[str]) -> int:
    csv_path = argv[1]
    uc = BulkAddUseCase(connection_string=get_connection_string())
    return uc.execute_from_csv_path(csv_path)

