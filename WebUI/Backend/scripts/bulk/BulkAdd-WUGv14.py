import csv
import pyodbc
import sys

# ------------------------
# Configuration
CSV_PATH = sys.argv[1]

DEFAULT_WORST_STATE_ID = 1
DEFAULT_BEST_STATE_ID = 1
TEMP_DEFAULT_NETIF_ID = 0   # Change if your DB forbids 0

CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=WhatsUp;"
    "Trusted_Connection=yes;"
)
# ------------------------

# Load CSV
rows = []
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

if not rows:
    print(f"ERROR: CSV empty or headers mismatch: {CSV_PATH}", file=sys.stderr)
    sys.exit(1)

# SQL template
sql_template = """
SET NOCOUNT ON;
BEGIN TRY
    BEGIN TRAN;

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
        0, 41, GETDATE(),
        @NewActionPolicyID, NULL,
        NULL, 0,
        0, 0, '', '', NULL
    );

    INSERT INTO PivotDeviceToGroup (nDeviceID, nDeviceGroupID)
        VALUES (@NewDeviceID, ?);

    COMMIT TRAN;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRAN;
    THROW;
END CATCH;
"""

sql = sql_template.format(
    WORST=DEFAULT_WORST_STATE_ID,
    BEST=DEFAULT_BEST_STATE_ID,
    TEMP_NETIF=TEMP_DEFAULT_NETIF_ID
)

# Connect to SQL Server
conn = pyodbc.connect(CONNECTION_STRING)
cursor = conn.cursor()
cursor.fast_executemany = False

row_num = 0

for r in rows:
    row_num += 1
    try:
        cursor.execute(
            sql,
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
