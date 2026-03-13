import pyodbc
import json
import os
from datetime import datetime, timedelta
from openpyxl.utils import get_column_letter
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import resend
from constants import (
    get_connection_string,
    REPORT_SCHEDULE_JSON_FILE,
)
try:
    # When imported as part of the FastAPI app (scripts.reporting package)
    from scripts.reporting.DeviceUpTimeReport import run_sp_group_device_uptime, write_excel as write_uptime_excel
except ImportError:
    # Fallback for running this file directly
    from DeviceUpTimeReport import run_sp_group_device_uptime, write_excel as write_uptime_excel


# This should match your report folder from the other script
OUTPUT_FOLDER = r"C:\WUG_Exports"
# Preferred JSON-based schedule shared with the FastAPI API
SCHEDULE_JSON_FILE = str(REPORT_SCHEDULE_JSON_FILE)

# Resend configuration (provided by user)
RESEND_API_KEY = "re_j4PGF4Ev_Jr1M8fDaaARvJS7WocdFACDt"
RESEND_FROM = "onboarding@resend.dev"
RESEND_TO = "snipergolden1234@gmail.com"

resend.api_key = RESEND_API_KEY
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
# =================================
def send_all_reports_via_email(start_date, end_date):
    """
    Attach all XLSX reports from OUTPUT_FOLDER and send in one email
    using Resend.
    """
    folder = Path(OUTPUT_FOLDER)
    if not folder.exists():
        print(f"Report folder does not exist: {folder}")
        return

    # Pick all Excel reports we generated, e.g. ActiveMonitorAvailability_*.xlsx
    report_files = sorted(folder.glob("ActiveMonitorAvailability_*.xlsx"))

    if not report_files:
        print("No report files found to send.")
        return

    subject = f"WUG Monthly Reports: {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}"
    html_body = (
        f"<p>Attached are the Active Monitor Availability reports for all groups<br>"
        f"from {start_date:%Y-%m-%d %H:%M} to {end_date:%Y-%m-%d %H:%M}.</p>"
        f"<p>Total reports: {len(report_files)}</p>"
    )

    attachments = []
    for report_path in report_files:
        try:
            with open(report_path, "rb") as f:
                content_bytes = f.read()
            attachment: resend.Attachment = {
                "content": list(content_bytes),
                "filename": os.path.basename(report_path),
            }
            attachments.append(attachment)
        except Exception as e:
            print(f"[EMAIL] Failed to read attachment {report_path}: {e}")

    params: resend.Emails.SendParams = {
        "from": RESEND_FROM,
        "to": [RESEND_TO],
        "subject": subject,
        "html": html_body,
    }
    if attachments:
        params["attachments"] = attachments

    try:
        resend.Emails.send(params)
        print(f"[EMAIL] Resend monthly email sent with {len(attachments)} attachment(s).")
    except Exception as e:
        print(f"[EMAIL] ERROR sending monthly email via Resend: {e}")

# ========== CONFIG ==========
WEB_USER_ID = 1  # same web user as in WUG (nWebUserID)
OUTPUT_FOLDER = r"C:\WUG_Exports"
SQL_PERCENT_MULTIPLIER = 1000000000.0
REPORT_PERCENT_DIVISOR = 10000000.0
ROUND_TO_PLACES_EXPORT = 7
# ============================
def send_single_report_email(group_name, report_path, start_date, end_date):
    """
    Send a single report as an attachment using Resend.
    """
    subject = f"WUG Report for {group_name}: {start_date:%Y-%m-%d %H:%M} → {end_date:%Y-%m-%d %H:%M}"
    html_body = (
        f"<p>Attached is the report for group '<strong>{group_name}</strong>'.</p>"
        f"<p>Period: {start_date:%Y-%m-%d %H:%M} to {end_date:%Y-%m-%d %H:%M}.</p>"
    )

    attachments = []
    try:
        with open(report_path, "rb") as f:
            content_bytes = f.read()
        attachment: resend.Attachment = {
            "content": list(content_bytes),
            "filename": os.path.basename(report_path),
        }
        attachments.append(attachment)
    except Exception as e:
        print(f"[EMAIL] Failed to read attachment {report_path}: {e}")

    params: resend.Emails.SendParams = {
        "from": RESEND_FROM,
        "to": [RESEND_TO],
        "subject": subject,
        "html": html_body,
    }
    if attachments:
        params["attachments"] = attachments

    try:
        resend.Emails.send(params)
        print(f"[EMAIL] Resend email sent for group {group_name} with attachment {report_path}")
    except Exception as e:
        print(f"[EMAIL] ERROR sending email via Resend for group {group_name}: {e}")

def get_date_range_from_period(period_td):
    end = datetime.now()
    start = end - period_td
    return start, end

def should_run(last_run_str, period_td):
    if last_run_str is None:
        return True

    last_run = datetime.fromisoformat(last_run_str)
    return datetime.now() - last_run >= period_td

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def parse_period(period: str) -> timedelta:
    """
    Parse a simple duration string like:
      "1d" (days), "2w" (weeks), "6h" (hours), "30m" (minutes)
    Used both for:
      - schedule intervals (how often to run)
      - window offsets (relative to run time) when negative values are used.
    """
    period = str(period).strip()
    if not period:
        raise ValueError("Empty period")

    num = int(period[:-1])
    unit = period[-1]

    if unit == "d":
        return timedelta(days=num)
    if unit == "w":
        return timedelta(weeks=num)
    if unit == "h":
        return timedelta(hours=num)
    if unit == "m":
        return timedelta(minutes=num)

    raise ValueError("Invalid period: " + period)

def load_schedule_config():
    """
    Load scheduling configuration from the JSON file produced by the API.

    Shape in JSON (report_schedule.json):
      {
        "columns": [...],
        "rows": [
          {
            "group": "...",
            "availability_period": "1w",
            "availability_window_start": "-73h",
            "availability_window_end": "-25h",
            "uptime_period": "1w",
            "uptime_window_start": "-73h",
            "uptime_window_end": "-25h",
            ...
          },
          ...
        ]
      }

    This function no longer reads from the legacy Excel sheet; all
    scheduling is driven by JSON so frontend and backend stay in sync.
    """
    if not os.path.exists(SCHEDULE_JSON_FILE):
        return {}

    with open(SCHEDULE_JSON_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    rows = raw.get("rows", [])
    if not isinstance(rows, list) or not rows:
        return {}

    def _clean(v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    jobs = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        job_id = _clean(row.get("id"))
        group_name = _clean(row.get("group"))
        if not group_name:
            continue

        entry = {
            "id": job_id,
            "group": group_name,
            "run_day": _clean(row.get("run_day")),
            "run_time": _clean(row.get("run_time")),
            "availability_period": _clean(row.get("availability_period") or row.get("availability")),
            "uptime_period": _clean(row.get("uptime_period") or row.get("uptime")),
            "availability_window_start": _clean(row.get("availability_window_start")),
            "availability_window_end": _clean(row.get("availability_window_end")),
            "uptime_window_start": _clean(row.get("uptime_window_start")),
            "uptime_window_end": _clean(row.get("uptime_window_end")),
        }

        # Legacy single period (if someone still sends it)
        legacy_period = _clean(row.get("period"))
        if legacy_period:
            entry["availability_period"] = entry["availability_period"] or legacy_period
            entry["uptime_period"] = entry["uptime_period"] or legacy_period

        # Drop empty keys
        entry = {k: v for k, v in entry.items() if v is not None}

        if "id" not in entry:
            # Stable ids are generated by the API on save; if missing we still
            # run the job, but state tracking will fall back to group+index.
            entry["id"] = None

        jobs.append(entry)

    return jobs

def get_duration_from_seconds(total_seconds: int) -> str:
    """Approximate of GetDurationFromSeconds from ASP code."""
    if total_seconds is None or total_seconds < 0:
        total_seconds = 0

    total_seconds = int(total_seconds)
    minutes, _ = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")

    return " ".join(parts)

def get_active_monitor_availability(device_group_id: int,
                                    start_date: datetime,
                                    end_date: datetime):
    """
    Runs the same SQL you just tested in SSMS (dynamic LoadDeviceGroup + main aggregation),
    and returns list of rows ready to export.
    """

    # Format dates like '2025-11-23T00:00:00'
    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")

    # This is basically your working SSMS script,
    # but with {group_id}, {web_user_id}, {start}, {end} filled in by Python.
    sql_template = f"""
DECLARE @DeviceGroupID INT;
DECLARE @WebUserID INT;
DECLARE @StartDate DATETIME;
DECLARE @EndDate DATETIME;

SET @DeviceGroupID = {device_group_id};
SET @WebUserID = {WEB_USER_ID};
SET @StartDate = '{start_str}';
SET @EndDate = '{end_str}';

DECLARE @PivotTableName SYSNAME;
SET @PivotTableName = 'PivotDeviceToGroupTemp';

IF OBJECT_ID(@PivotTableName) IS NOT NULL
BEGIN
    DECLARE @dropSql NVARCHAR(4000);
    SET @dropSql = N'DROP TABLE ' + QUOTENAME(@PivotTableName) + N';';
    EXEC (@dropSql);
END;

EXEC LoadDeviceGroup @DeviceGroupID, @WebUserID, @PivotTableName;

DECLARE @sql NVARCHAR(MAX);

SET @sql = N'
SELECT
    Device.nDeviceID,
    Device.sDisplayName,
    NetworkInterface.nNetworkInterfaceID,
    NetworkInterface.sNetworkName,
    NetworkInterface.sNetworkAddress,
    Device.nWorstStateID,
    Device.nBestStateID,
    ActiveMonitorType.sMonitorTypeName,
    PivotActiveMonitorTypeToDevice.sArgument,
    PivotActiveMonitorTypeToDevice.nPivotActiveMonitorTypeToDeviceID,
    PivotActiveMonitorTypeToDevice.sComment,
    CAST(Device.sNote AS NVARCHAR(MAX)) AS sNote,

    -- seconds in each state
    SUM(
        CASE MonitorState.nInternalMonitorState WHEN 1 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) AS nDownSeconds,

    SUM(
        CASE MonitorState.nInternalMonitorState WHEN 2 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) AS nMaintenanceSeconds,

    SUM(
        CASE MonitorState.nInternalMonitorState WHEN 3 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) AS nUpSeconds,

    SUM(
        CASE MonitorState.nInternalMonitorState WHEN -1 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) AS nUnknownSeconds,

    -- total seconds (any state)
    SUM(
        DATEDIFF(
            SECOND,
            CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
            ISNULL(
                CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
            )
        )
    ) AS nTotalSeconds,

    -- Percentages scaled like WUG: * 1000000000
    (1.0 * SUM(
        CASE MonitorState.nInternalMonitorState WHEN 1 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) / NULLIF(
        SUM(
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ), 0)
    ) * 1000000000.0 AS nDownPercent,

    (1.0 * SUM(
        CASE MonitorState.nInternalMonitorState WHEN 2 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) / NULLIF(
        SUM(
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ), 0)
    ) * 1000000000.0 AS nMaintenancePercent,

    (1.0 * SUM(
        CASE MonitorState.nInternalMonitorState WHEN 3 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) / NULLIF(
        SUM(
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ), 0)
    ) * 1000000000.0 AS nUpPercent,

    (1.0 * SUM(
        CASE MonitorState.nInternalMonitorState WHEN -1 THEN
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ELSE 0 END
    ) / NULLIF(
        SUM(
            DATEDIFF(
                SECOND,
                CASE WHEN dStartTime < @StartDate THEN @StartDate ELSE dStartTime END,
                ISNULL(
                    CASE WHEN dEndTime > @EndDate THEN @EndDate ELSE dEndTime END,
                    CASE WHEN @EndDate < GETDATE() THEN @EndDate ELSE GETDATE() END
                )
            )
        ), 0)
    ) * 1000000000.0 AS nUnknownPercent

FROM ActiveMonitorStateChangeLog
INNER JOIN MonitorState
    ON MonitorState.nMonitorStateID = ActiveMonitorStateChangeLog.nMonitorStateID
INNER JOIN PivotActiveMonitorTypeToDevice
    ON PivotActiveMonitorTypeToDevice.nPivotActiveMonitorTypeToDeviceID = ActiveMonitorStateChangeLog.nPivotActiveMonitorTypeToDeviceID
INNER JOIN Device
    ON Device.nDeviceID = PivotActiveMonitorTypeToDevice.nDeviceID
INNER JOIN NetworkInterface
    ON NetworkInterface.nNetworkInterfaceID = Device.nDefaultNetworkInterfaceID
INNER JOIN ActiveMonitorType
    ON ActiveMonitorType.nActiveMonitorTypeID = PivotActiveMonitorTypeToDevice.nActiveMonitorTypeID
INNER JOIN ' + QUOTENAME(@PivotTableName) + N'
    ON Device.nDeviceID = ' + QUOTENAME(@PivotTableName) + N'.nDeviceID
WHERE
    ISNULL(ActiveMonitorType.bRemoved,0) <> 1
    AND ISNULL(Device.bRemoved,0)      <> 1
    AND (
        (dStartTime >= @StartDate AND ISNULL(dEndTime, GETDATE()) <= @EndDate)
        OR (dStartTime <= @EndDate   AND ISNULL(dEndTime, GETDATE()) >= @StartDate)
        OR (dStartTime <= @EndDate   AND ISNULL(dEndTime, GETDATE()) >= @EndDate)
        OR (dStartTime <= @StartDate AND ISNULL(dEndTime, GETDATE()) >= @EndDate)
    )
GROUP BY
    Device.nDeviceID,
    Device.sDisplayName,
    NetworkInterface.nNetworkInterfaceID,
    NetworkInterface.sNetworkName,
    NetworkInterface.sNetworkAddress,
    Device.nWorstStateID,
    Device.nBestStateID,
    PivotActiveMonitorTypeToDevice.nPivotActiveMonitorTypeToDeviceID,
    PivotActiveMonitorTypeToDevice.sArgument,
    PivotActiveMonitorTypeToDevice.sComment,
    ActiveMonitorType.sMonitorTypeName,
    CAST(Device.sNote AS NVARCHAR(MAX))
ORDER BY
    Device.sDisplayName ASC,
    ActiveMonitorType.sMonitorTypeName ASC;
';

EXEC sp_executesql
    @sql,
    N'@StartDate datetime, @EndDate datetime',
    @StartDate = @StartDate,
    @EndDate   = @EndDate;

IF OBJECT_ID(@PivotTableName) IS NOT NULL
BEGIN
    DECLARE @dropSql2 NVARCHAR(4000);
    SET @dropSql2 = N'DROP TABLE ' + QUOTENAME(@PivotTableName) + N';';
    EXEC (@dropSql2);
END;
"""

    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()

    cursor.execute(sql_template)

    rows = cursor.fetchall()
    cols = [c[0] for c in cursor.description]

    results = []

    for row in rows:
        rec = dict(zip(cols, row))

        def scaled(p):
            if p is None:
                return 0.0
            return float(p) / REPORT_PERCENT_DIVISOR

        up_pct = scaled(rec["nUpPercent"])
        down_pct = scaled(rec["nDownPercent"])
        maint_pct = scaled(rec["nMaintenancePercent"])
        unknown_pct = scaled(rec["nUnknownPercent"])

        up_dur = get_duration_from_seconds(rec["nUpSeconds"])
        down_dur = get_duration_from_seconds(rec["nDownSeconds"])
        maint_dur = get_duration_from_seconds(rec["nMaintenanceSeconds"])
        unknown_dur = get_duration_from_seconds(rec["nUnknownSeconds"])
        total_dur = get_duration_from_seconds(rec["nTotalSeconds"])

        sMonitorTypeName = rec["sMonitorTypeName"]
        sArgument = rec["sArgument"] or ""
        sComment = rec["sComment"] or ""
        
        sIPAddress = rec["sNetworkAddress"]
        sNote = rec["sNote"]

        monitor_name = sMonitorTypeName
        if sArgument:
            monitor_name += f" ({sArgument})"
        if sComment:
            monitor_name += f" - {sComment}"

        results.append({
            "Device": rec["sDisplayName"],
            "IPAddress": sIPAddress,
            "Note": sNote,
            "Monitor": monitor_name,
            "UpPercent": round(up_pct, ROUND_TO_PLACES_EXPORT),
            "UpDuration": up_dur,
            "MaintenancePercent": round(maint_pct, ROUND_TO_PLACES_EXPORT),
            "MaintenanceDuration": maint_dur,
            "UnknownPercent": round(unknown_pct, ROUND_TO_PLACES_EXPORT),
            "UnknownDuration": unknown_dur,
            "DownPercent": round(down_pct, ROUND_TO_PLACES_EXPORT),
            "DownDuration": down_dur,
            "TotalDuration": total_dur,
        })

    cursor.close()
    conn.close()
    return results

def write_excel_for_group(device_group_id: int,
                          start_date: datetime,
                          end_date: datetime,
                          group_name: str = None):
    rows = get_active_monitor_availability(device_group_id, start_date, end_date)
    if not rows:
        print(f"No data for group {device_group_id}")
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    if not group_name:
        group_name = f"group_{device_group_id}"

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in group_name)
    filename = f"ActiveMonitorAvailability_{safe_name}.xlsx"
    path = os.path.join(OUTPUT_FOLDER, filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "Active Monitor Availability"

    # Columns exactly like the WUG export
    headers = [
        "Device",
        "Network Address (IP)",
        "Monitor",
        "Up",
        "Up Duration",
        "Maintenance",
        "Maintenance Duration",
        "Unknown",
        "Unknown Duration",
        "Down",
        "Down Duration",
        "Total Duration",
        "Note",
    ]
    last_col_letter = get_column_letter(len(headers))

    # Common styles
    title_font = Font(size=14, bold=True)
    subtitle_font = Font(size=11)
    header_font = Font(bold=True)
    center_align = Alignment(horizontal="center")
    right_align = Alignment(horizontal="right")
    header_fill = PatternFill("solid", fgColor="C0C0C0")  # light grey like your screenshot
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # ----- Row 1: Title -----
    ws["A1"].value = "Active Monitor Availability"
    ws["A1"].font = title_font
    ws["A1"].alignment = center_align
    ws.merge_cells(f"A1:{last_col_letter}1")

    # ----- Row 2: Subtitle (Group - start - end) -----
    start_long = start_date.strftime("%A, %B %d, %Y %I:%M:%S %p")
    end_long = end_date.strftime("%A, %B %d, %Y %I:%M:%S %p")
    ws["A2"].value = f"{group_name} - {start_long} - {end_long}"
    ws["A2"].font = subtitle_font
    ws["A2"].alignment = center_align
    ws.merge_cells(f"A2:{last_col_letter}2")

    # ----- Row 3: Headers -----
    header_row_idx = 3
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=header_row_idx, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    # ----- Data rows -----
    row_idx = header_row_idx + 1

    for r in rows:
        up_fraction = (r["UpPercent"] or 0.0) / 100.0
        maint_fraction = (r["MaintenancePercent"] or 0.0) / 100.0
        unknown_fraction = (r["UnknownPercent"] or 0.0) / 100.0
        down_fraction = (r["DownPercent"] or 0.0) / 100.0

        # Device
        c = ws.cell(row=row_idx, column=1, value=r["Device"])
        c.border = thin_border
        
        c = ws.cell(row=row_idx, column=2, value=r["IPAddress"])
        c.border = thin_border
        
        c = ws.cell(row=row_idx, column=3, value=r["Note"])
        c.border = thin_border

        # Monitor
        c = ws.cell(row=row_idx, column=4, value=r["Monitor"])
        c.border = thin_border

        # Up %
        up_cell = ws.cell(row=row_idx, column=5, value=up_fraction)
        up_cell.number_format = "0.0000000%"
        up_cell.alignment = right_align
        up_cell.border = thin_border

        # Up Duration
        c = ws.cell(row=row_idx, column=6, value=r["UpDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Maintenance %
        maint_cell = ws.cell(row=row_idx, column=7, value=maint_fraction)
        maint_cell.number_format = "0.0000000%"
        maint_cell.alignment = right_align
        maint_cell.border = thin_border

        # Maintenance Duration
        c = ws.cell(row=row_idx, column=8, value=r["MaintenanceDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Unknown %
        unknown_cell = ws.cell(row=row_idx, column=9, value=unknown_fraction)
        unknown_cell.number_format = "0.0000000%"
        unknown_cell.alignment = right_align
        unknown_cell.border = thin_border

        # Unknown Duration
        c = ws.cell(row=row_idx, column=10, value=r["UnknownDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Down %
        down_cell = ws.cell(row=row_idx, column=11, value=down_fraction)
        down_cell.number_format = "0.0000000%"
        down_cell.alignment = right_align
        down_cell.border = thin_border

        # Down Duration
        c = ws.cell(row=row_idx, column=12, value=r["DownDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Total Duration
        c = ws.cell(row=row_idx, column=13, value=r["TotalDuration"])
        c.alignment = right_align
        c.border = thin_border

        row_idx += 1

    # ----- Auto-size columns (avoid merged-cell issue) -----
    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[col_letter]:
            val = "" if cell.value is None else str(cell.value)
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = min(max_len + 2, 50)

    wb.save(path)
    print(f"Wrote Excel report to {path}")
    return path

def get_device_groups():
    """
    Returns list of (group_id, group_name) from DeviceGroup.
    Uses exactly: SELECT nDeviceGroupID, sGroupName FROM DeviceGroup;
    """
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    cursor.execute("SELECT nDeviceGroupID, sGroupName FROM DeviceGroup")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [(int(row[0]), row[1]) for row in rows]

def get_previous_month_range():
    now = datetime.now()
    first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if first_this_month.month == 1:
        first_prev_month = first_this_month.replace(year=first_this_month.year - 1, month=12)
    else:
        first_prev_month = first_this_month.replace(month=first_this_month.month - 1)

    # start = first day of previous month, end = first day of this month
    return first_prev_month, first_this_month


def _weekday_index(day_code: str) -> int:
    """
    Map a short day code like 'mon', 'tue', ... to Python weekday index (Mon=0).
    """
    code = (day_code or "").strip().lower()
    mapping = {
        "mon": 0,
        "tue": 1,
        "wed": 2,
        "thu": 3,
        "fri": 4,
        "sat": 5,
        "sun": 6,
    }
    return mapping.get(code, 0)


def _get_weekly_target(run_day: str, run_time: str, now: datetime) -> datetime:
    """
    Given a run day code (mon..sun) and HH:MM time, return the scheduled
    datetime for the current week. Jobs will execute once when 'now' passes
    this target and when the last_run stored in state is older than it.
    """
    wd_target = _weekday_index(run_day)
    try:
        hour, minute = map(int, (run_time or "00:00").split(":", 1))
    except ValueError:
        hour, minute = 0, 0

    days_ahead = wd_target - now.weekday()
    target_date = (now + timedelta(days=days_ahead)).date()
    return datetime(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def _compute_window(now_run: datetime, period_td: timedelta, win_start_raw, win_end_raw):
    """
    Compute [start_date, end_date] for a job given the base run time and window
    offsets. Supports special 'full_last_month' preset.
    """
    if win_start_raw and win_end_raw:
        win_start_str = str(win_start_raw).strip()
        win_end_str = str(win_end_raw).strip()

        if win_start_str == "full_last_month" and win_end_str == "full_last_month":
            return get_previous_month_range()

        # Treat as relative offsets from the run time
        win_start_td = parse_period(win_start_raw)
        win_end_td = parse_period(win_end_raw)
        start_date = now_run + win_start_td
        end_date = now_run + win_end_td
        return start_date, end_date

    # Default rolling window: [run_time - period, run_time]
    end = now_run
    start = end - period_td
    return start, end

def run_scheduled_reports():
    """
    Execute all due scheduled reports based on the Excel configuration
    and persisted state. This is safe to call repeatedly (e.g. from a
    background scheduler); it will only generate reports that are due.
    """
    # 1) Load config (JSON schedule) and state (JSON)
    # jobs: list of schedule rows (each row is independent, even if group repeats)
    jobs = load_schedule_config()
    state = load_state()

    # Prune state entries for deleted jobs.
    # If a schedule row is removed, its job id won't exist anymore,
    # so we delete its last-run markers from state.json.
    valid_job_ids = set()
    for idx, job in enumerate(jobs):
        group_name = (job.get("group") or "").strip()
        jid = (job.get("id") or "").strip() or f"{group_name}::__idx_{idx}"
        if jid:
            valid_job_ids.add(jid)

    if isinstance(state, dict):
        keys_to_delete = []
        for k in state.keys():
            if k == "__MONTHLY_ALL__":
                continue
            if "::__" not in k:
                continue
            prefix = k.split("::__", 1)[0]
            if prefix not in valid_job_ids:
                keys_to_delete.append(k)

        for k in keys_to_delete:
            del state[k]
    # --- Monthly all-groups run (once per month) ---
    last_monthly_str = state.get("__MONTHLY_ALL__")
    now = datetime.now()
    do_monthly = False

    if last_monthly_str is None:
        # never ran before -> run now
        do_monthly = True
    else:
        last_monthly = datetime.fromisoformat(last_monthly_str)
        if last_monthly.year != now.year or last_monthly.month != now.month:
            # last run was in a previous month -> run now
            do_monthly = True

    if do_monthly:
        print("[MONTHLY] Generating all-group monthly reports...")
        start_m, end_m = get_previous_month_range()

        # generate reports for ALL groups for last month
        groups = get_device_groups()  # (id, name)
        for gid, gname in groups:
            print(f"[MONTHLY RUN] {gname}: {start_m} -> {end_m}")
            try:
                write_excel_for_group(
                    device_group_id=gid,
                    start_date=start_m,
                    end_date=end_m,
                    group_name=gname,
                )
            except Exception as e:
                print(f"[MONTHLY ERROR] {gname}: {e}")

        # send everything as one big mail
        send_all_reports_via_email(start_m, end_m)

        # update monthly marker
        state["__MONTHLY_ALL__"] = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    # 2) Get groups from DB and build name -> id map
    groups = get_device_groups()        # returns list of (id, name)
    name_to_id = {name: gid for gid, name in groups}

    # 3) Loop on each schedule row (job)
    for idx, job in enumerate(jobs):
        group_name_stripped = (job.get("group") or "").strip()
        job_id = (job.get("id") or "").strip() or f"{group_name_stripped}::__idx_{idx}"
        periods = job

        if group_name_stripped not in name_to_id:
            print(f"[SKIP] Config group '{group_name_stripped}' not found in DeviceGroup table")
            continue

        # Per‑report scheduling; each report type has its own period
        # and last‑run marker so they can be configured independently.

        # ===== Report 1: Active Monitor Availability =====
        availability_period = periods.get("availability_period")
        if availability_period:
            try:
                period_td = parse_period(availability_period)
            except Exception as e:
                print(f"[SKIP] Invalid availability_period '{availability_period}' for group '{group_name_stripped}': {e}")
            else:
                state_key = f"{job_id}::__availability"
                last_run_str = state.get(state_key)
                run_day = periods.get("run_day")
                run_time = periods.get("run_time")

                use_weekly_anchor = bool(run_day and run_time and period_td >= timedelta(days=7))
                now_run = None

                if use_weekly_anchor:
                    target_dt = _get_weekly_target(run_day, run_time, now)
                    last_run = datetime.fromisoformat(last_run_str) if last_run_str else None
                    if now >= target_dt and (last_run is None or last_run < target_dt):
                        now_run = target_dt
                else:
                    if should_run(last_run_str, period_td):
                        now_run = datetime.now()

                if now_run is not None:
                    win_start_raw = periods.get("availability_window_start")
                    win_end_raw = periods.get("availability_window_end")
                    try:
                        start_date, end_date = _compute_window(now_run, period_td, win_start_raw, win_end_raw)
                    except Exception as e:
                        print(f"[SKIP] Invalid availability window for '{group_name_stripped}': {e}")
                        start_date = end_date = None

                    if start_date and end_date and start_date < end_date:
                        device_group_id = name_to_id[group_name_stripped]
                        print(f"[RUN] Availability for {group_name_stripped}: {start_date} -> {end_date}")
                        try:
                            availability_report_path = write_excel_for_group(
                                device_group_id=device_group_id,
                                start_date=start_date,
                                end_date=end_date,
                                group_name=group_name_stripped,
                            )

                            send_single_report_email(
                                group_name=group_name_stripped,
                                report_path=availability_report_path,
                                start_date=start_date,
                                end_date=end_date,
                            )

                            state[state_key] = now_run.replace(second=0, microsecond=0).isoformat()
                        except Exception as e:
                            print(f"[ERROR] while generating availability report for '{group_name_stripped}': {e}")

        # ===== Report 2: Device Uptime (DeviceUpTimeReport) =====
        uptime_period = periods.get("uptime_period")
        if uptime_period:
            try:
                period_td = parse_period(uptime_period)
            except Exception as e:
                print(f"[SKIP] Invalid uptime_period '{uptime_period}' for group '{group_name_stripped}': {e}")
            else:
                state_key = f"{job_id}::__uptime"
                last_run_str = state.get(state_key)
                run_day = periods.get("run_day")
                run_time = periods.get("run_time")

                use_weekly_anchor = bool(run_day and run_time and period_td >= timedelta(days=7))
                now_run = None

                if use_weekly_anchor:
                    target_dt = _get_weekly_target(run_day, run_time, now)
                    last_run = datetime.fromisoformat(last_run_str) if last_run_str else None
                    if now >= target_dt and (last_run is None or last_run < target_dt):
                        now_run = target_dt
                else:
                    if should_run(last_run_str, period_td):
                        now_run = datetime.now()

                if now_run is not None:
                    win_start_raw = periods.get("uptime_window_start")
                    win_end_raw = periods.get("uptime_window_end")
                    try:
                        start_date, end_date = _compute_window(now_run, period_td, win_start_raw, win_end_raw)
                    except Exception as e:
                        print(f"[SKIP] Invalid uptime window for '{group_name_stripped}': {e}")
                        start_date = end_date = None

                    if start_date and end_date and start_date < end_date:
                        device_group_id = name_to_id[group_name_stripped]
                        print(f"[RUN] DeviceUpTime for {group_name_stripped}: {start_date} -> {end_date}")
                        try:
                            uptime_rows = run_sp_group_device_uptime(
                                device_group_id=device_group_id,
                                start_date=start_date,
                                end_date=end_date,
                            )

                            if uptime_rows:
                                uptime_report_path = write_uptime_excel(
                                    group_name_stripped,
                                    uptime_rows,
                                    start_date,
                                    end_date,
                                )

                                send_single_report_email(
                                    group_name=group_name_stripped,
                                    report_path=uptime_report_path,
                                    start_date=start_date,
                                    end_date=end_date,
                                )
                                state[state_key] = now_run.replace(second=0, microsecond=0).isoformat()
                            else:
                                print(f"[RUN] No uptime data for '{group_name_stripped}' in scheduled window (will retry next run)")
                                # Do not update state so the job runs again next period
                        except Exception as e:
                            print(f"[ERROR] while generating DeviceUpTime report for '{group_name_stripped}': {e}")
                            # Do not update state on error so it retries

    # 5) Save updated state
    save_state(state)
