import pyodbc
import json
import os
from datetime import datetime, timedelta
from openpyxl.utils import get_column_letter
import os
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
from constants import get_connection_string, SMTP_SERVER, SMTP_PORT, BREVO_USERNAME, BREVO_SMTP_KEY, SENDER, RECEIVER


# This should match your report folder from the other script
OUTPUT_FOLDER = r"C:\WUG_Exports"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_schedule.xlsx")
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
# =================================
def send_all_reports_via_email(start_date, end_date):
    """
    Attach all XLSX reports from OUTPUT_FOLDER and send in one email.
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

    # Email subject & body
    subject = f"WUG Monthly Reports: {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}"
    body = (
        f"Attached are the Active Monitor Availability reports for all groups\n"
        f"from {start_date:%Y-%m-%d %H:%M} to {end_date:%Y-%m-%d %H:%M}.\n\n"
        f"Total reports: {len(report_files)}"
    )

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = RECEIVER

    msg.attach(MIMEText(body, "plain"))

    # Attach each Excel file
    for report_path in report_files:
        with open(report_path, "rb") as f:
            part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(report_path)}"'
        )
        msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(BREVO_USERNAME, BREVO_SMTP_KEY)
        server.sendmail(SENDER, [RECEIVER], msg.as_string())
        server.quit()
        print(f"Email sent successfully with {len(report_files)} attachments!")
    except Exception as e:
        print("ERROR sending email:", e)

# ========== CONFIG ==========
WEB_USER_ID = 1  # same web user as in WUG (nWebUserID)
OUTPUT_FOLDER = r"C:\WUG_Exports"
SQL_PERCENT_MULTIPLIER = 1000000000.0
REPORT_PERCENT_DIVISOR = 10000000.0
ROUND_TO_PLACES_EXPORT = 7
# ============================
def send_single_report_email(group_name, report_path, start_date, end_date):
    subject = f"WUG Report for {group_name}: {start_date:%Y-%m-%d %H:%M} → {end_date:%Y-%m-%d %H:%M}"
    body = (
        f"Attached is the Active Monitor Availability report for group '{group_name}'.\n\n"
        f"Period: {start_date:%Y-%m-%d %H:%M} to {end_date:%Y-%m-%d %H:%M}."
    )

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = RECEIVER
    msg.attach(MIMEText(body, "plain"))

    with open(report_path, "rb") as f:
        part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(report_path)}"')
    msg.attach(part)

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(BREVO_USERNAME, BREVO_SMTP_KEY)
    server.sendmail(SENDER, [RECEIVER], msg.as_string())
    server.quit()
    print(f"Email sent for group {group_name} with {report_path}")

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

def parse_period(period):
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
    df = pd.read_excel(CONFIG_FILE)
    schedule = {}

    for _, row in df.iterrows():
        schedule[str(row["group"]).strip()] = str(row["period"]).strip()

    return schedule

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
    ActiveMonitorType.sMonitorTypeName
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

        monitor_name = sMonitorTypeName
        if sArgument:
            monitor_name += f" ({sArgument})"
        if sComment:
            monitor_name += f" - {sComment}"

        results.append({
            "Device": rec["sDisplayName"],
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

        # Monitor
        c = ws.cell(row=row_idx, column=2, value=r["Monitor"])
        c.border = thin_border

        # Up %
        up_cell = ws.cell(row=row_idx, column=3, value=up_fraction)
        up_cell.number_format = "0.0000000%"
        up_cell.alignment = right_align
        up_cell.border = thin_border

        # Up Duration
        c = ws.cell(row=row_idx, column=4, value=r["UpDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Maintenance %
        maint_cell = ws.cell(row=row_idx, column=5, value=maint_fraction)
        maint_cell.number_format = "0.0000000%"
        maint_cell.alignment = right_align
        maint_cell.border = thin_border

        # Maintenance Duration
        c = ws.cell(row=row_idx, column=6, value=r["MaintenanceDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Unknown %
        unknown_cell = ws.cell(row=row_idx, column=7, value=unknown_fraction)
        unknown_cell.number_format = "0.0000000%"
        unknown_cell.alignment = right_align
        unknown_cell.border = thin_border

        # Unknown Duration
        c = ws.cell(row=row_idx, column=8, value=r["UnknownDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Down %
        down_cell = ws.cell(row=row_idx, column=9, value=down_fraction)
        down_cell.number_format = "0.0000000%"
        down_cell.alignment = right_align
        down_cell.border = thin_border

        # Down Duration
        c = ws.cell(row=row_idx, column=10, value=r["DownDuration"])
        c.alignment = right_align
        c.border = thin_border

        # Total Duration
        c = ws.cell(row=row_idx, column=11, value=r["TotalDuration"])
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


if __name__ == "__main__":
    # 1) Load config (Excel) and state (JSON)
    schedule = load_schedule_config()   # group name -> period string like "2d"
    state = load_state()                # group name -> last_run ISO string
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

    # 3) Loop on each row in the Excel schedule
    for group_name, period_str in schedule.items():
        group_name_stripped = group_name.strip()

        if group_name_stripped not in name_to_id:
            print(f"[SKIP] Config group '{group_name_stripped}' not found in DeviceGroup table")
            continue

        try:
            period_td = parse_period(period_str)
        except Exception as e:
            print(f"[SKIP] Invalid period '{period_str}' for group '{group_name_stripped}': {e}")
            continue

        last_run_str = state.get(group_name_stripped)

        if not should_run(last_run_str, period_td):
            print(f"[SKIP] {group_name_stripped}: not due yet")
            continue

        # 4) Compute date range based on the period (e.g. last 2d / 1w / 6h)
        start_date, end_date = get_date_range_from_period(period_td)
        device_group_id = name_to_id[group_name_stripped]

        print(f"[RUN] {group_name_stripped}: {start_date} -> {end_date}")

        try:
            # Generate the Excel report for this group
            report_path  = write_excel_for_group(
                device_group_id=device_group_id,
                start_date=start_date,
                end_date=end_date,
                group_name=group_name_stripped,
            )

            # TODO: here you can call your email function if you want per-group emails
            # e.g. send_single_report_email(group_name_stripped, generated_file_path)
            send_single_report_email(
                group_name=group_name_stripped,
                report_path=report_path,
                start_date=start_date,
                end_date=end_date,
            )
            # Update last_run in state
            state[group_name_stripped] = datetime.now().replace(minute=0, second=0, microsecond=0).isoformat()

        except Exception as e:
            print(f"[ERROR] while generating report for '{group_name_stripped}': {e}")

    # 5) Save updated state
    save_state(state)

