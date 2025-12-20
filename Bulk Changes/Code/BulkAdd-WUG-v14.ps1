# Import-WhatsUpDevices.ps1
# Run on a client/server that can access the CSV and the SQL Server.
# Update these variables:
[string]$CsvPath = "C:\WhatsUP Automatons\Bulk Changes\Code\Add.csv"
# Defaults (change if you know correct values)
$DefaultWorstStateID = 1
$DefaultBestStateID  = 1
$TempDefaultNetIfID  = 0   # temporary non-NULL placeholder; change if your DB forbids 0
# ------------------------
# Defaults (adjust if you know correct values)
$DefaultWorstStateID = 1
$DefaultBestStateID  = 1
$TempDefaultNetIfID  = 0   # temporary placeholder; change if your DB forbids 0
# ------------------------

# Load CSV
$rows = Import-Csv -Path $CsvPath
if ($rows.Count -eq 0) { Write-Error "CSV empty or headers mismatch: $CsvPath"; exit 1 }

# Build connection
Add-Type -AssemblyName System.Data
$connectionString = "Server=localhost;Database=WhatsUp;Integrated Security=True;"
$connection = New-Object System.Data.SqlClient.SqlConnection $connectionString
$connection.Open()

# T-SQL template: Insert Device, then create ActionPolicy and set Device.nActionPolicyID,
# then insert NetworkInterface, update Device.nDefaultNetworkInterfaceID, attributes, active monitor, group.
$sqlTemplate = @"
SET NOCOUNT ON;
BEGIN TRY
    BEGIN TRAN;

    -- Insert Device with temporary nDefaultNetworkInterfaceID (updated later)
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
        @displayName, @devicetype, NULL, NULL,
        0, NULL, 0, __WORST__,
        __BEST__, NULL, @notes, NULL,
        NULL, NULL, 0,
        0, 0, NULL,
        0, 0,
        0, NULL, __TEMP_NETIF__
    );

    DECLARE @NewDeviceID INT;
    SET @NewDeviceID = SCOPE_IDENTITY();

    -- Create ActionPolicy for this device and set Device.nActionPolicyID
    INSERT INTO ActionPolicy (sPolicyName, bExecuteAll, bGlobalActionPolicy)
    VALUES (NULL, 1, 0);

    DECLARE @NewActionPolicyID INT;
    SET @NewActionPolicyID = SCOPE_IDENTITY();

    UPDATE Device
    SET nActionPolicyID = @NewActionPolicyID
    WHERE nDeviceID = @NewDeviceID;

    -- Insert NetworkInterface for the device
    INSERT INTO NetworkInterface (
        nDeviceID, nPhysicalInterfaceID, nAddressType, bPollUsingNetworkName, sNetworkAddress, sNetworkName
    )
    VALUES (
        @NewDeviceID, NULL, 1, 0, @networkAddress, @networkName
    );

    DECLARE @NewNetworkInterfaceID INT;
    SET @NewNetworkInterfaceID = SCOPE_IDENTITY();

    -- Update Device to set correct default network interface id
    UPDATE Device
    SET nDefaultNetworkInterfaceID = @NewNetworkInterfaceID
    WHERE nDeviceID = @NewDeviceID;

    -- Device Attributes (non-NULL sValue -> empty string)
    INSERT INTO DeviceAttribute (nDeviceID, sName, sValue) VALUES (@NewDeviceID, 'Contact', '');
    INSERT INTO DeviceAttribute (nDeviceID, sName, sValue) VALUES (@NewDeviceID, 'Location', '');
    INSERT INTO DeviceAttribute (nDeviceID, sName, sValue) VALUES (@NewDeviceID, 'Description', '');

    -- Active Monitor pivot row: use the created ActionPolicy and NetworkInterface IDs
    INSERT INTO PivotActiveMonitorTypeToDevice (
        nDeviceID, nActiveMonitorTypeID, nNetworkInterfaceID, bAssumedState,
        nMonitorStateID, dLastInternalStateTime, nActionPolicyID, nPollInterval,
        bGatherPerformanceData, bFireActions, bDisabled, bRemoved, sArgument,
        sComment, nCriticalPollingOrder
    )
    VALUES (
        @NewDeviceID, 2, @NewNetworkInterfaceID, 0,
        41, GETDATE(), @NewActionPolicyID, NULL,
        NULL, 0, 0, 0, '',
        '', NULL
    );

    -- Device -> Group
    INSERT INTO PivotDeviceToGroup (nDeviceID, nDeviceGroupID) VALUES (@NewDeviceID, @devicegroup);

    COMMIT TRAN;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRAN;

    DECLARE @ErrMsg NVARCHAR(4000);
    DECLARE @ErrNo INT;

    SET @ErrMsg = ERROR_MESSAGE();
    SET @ErrNo  = ERROR_NUMBER();

    RAISERROR('Error (%d): %s', 16, 1, @ErrNo, @ErrMsg);
END CATCH;
"@

# Replace placeholders with chosen defaults
$sql = $sqlTemplate -replace '__WORST__', $DefaultWorstStateID.ToString() `
                   -replace '__BEST__',  $DefaultBestStateID.ToString() `
                   -replace '__TEMP_NETIF__', $TempDefaultNetIfID.ToString()

try {
    $cmd = $connection.CreateCommand()
    $cmd.CommandText = $sql
    $cmd.CommandType  = [System.Data.CommandType]::Text
    $cmd.CommandTimeout = 240

    # Define parameters once and reuse
    $cmd.Parameters.Add("@displayName",[System.Data.SqlDbType]::NVarChar,255) | Out-Null
    $cmd.Parameters.Add("@networkAddress",[System.Data.SqlDbType]::NVarChar,255) | Out-Null
    $cmd.Parameters.Add("@networkName",[System.Data.SqlDbType]::NVarChar,255) | Out-Null
    $cmd.Parameters.Add("@notes",[System.Data.SqlDbType]::NVarChar,255) | Out-Null
    $cmd.Parameters.Add("@devicetype",[System.Data.SqlDbType]::INT) | Out-Null
    $cmd.Parameters.Add("@devicegroup",[System.Data.SqlDbType]::INT) | Out-Null

    $rowNum = 0
    foreach ($r in $rows) {
        $rowNum++
        $cmd.Parameters["@displayName"].Value  = $r.DisplayName
        $cmd.Parameters["@networkAddress"].Value = $r.NetworkAddress
        $cmd.Parameters["@networkName"].Value = $r.NetworkName
        $cmd.Parameters["@notes"].Value       = $r.Notes
        $cmd.Parameters["@devicetype"].Value  = [int]$r.DeviceType
        $cmd.Parameters["@devicegroup"].Value  = [int]$r.DeviceGroup


        try {
            $cmd.ExecuteNonQuery() | Out-Null
            Write-Host "Inserted row $rowNum $($r.DisplayName)"
        } catch {
            Write-Warning "Failed to insert row $rowNum ($($r.DisplayName)): $($_.Exception.Message)"
        }
    }
} finally {
    $connection.Close()
}