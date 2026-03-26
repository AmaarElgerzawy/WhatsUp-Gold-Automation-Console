"""
Report scheduling: load schedule config, check triggers, run availability/uptime reports and send email.
Uses AvailabilityReport and DeviceUpTimeReport for actual report generation.
"""
import calendar
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import resend

from constants import REPORT_SCHEDULE_JSON_FILE
from scripts.reporting.AvailabilityReport import (
    OUTPUT_FOLDER as AVAILABILITY_OUTPUT_FOLDER,
    get_device_groups,
    write_excel_for_group,
)
from scripts.reporting.DeviceUpTimeReport import (
    run_sp_group_device_uptime,
    write_excel as write_uptime_excel,
)

RESEND_API_KEY = "re_j4PGF4Ev_Jr1M8fDaaARvJS7WocdFACDt"
RESEND_FROM = "onboarding@resend.dev"
RESEND_TO = "snipergolden1234@gmail.com"
resend.api_key = RESEND_API_KEY

SCHEDULE_JSON_FILE = str(REPORT_SCHEDULE_JSON_FILE)
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


def send_all_reports_via_email(start_date, end_date):
    """Attach all ActiveMonitorAvailability_*.xlsx from output folder and send via Resend."""
    folder = Path(AVAILABILITY_OUTPUT_FOLDER)
    if not folder.exists():
        print(f"Report folder does not exist: {folder}")
        return
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
            attachments.append({
                "content": list(content_bytes),
                "filename": os.path.basename(report_path),
            })
        except Exception as e:
            print(f"[EMAIL] Failed to read attachment {report_path}: {e}")

    params = {
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


def send_single_report_email(group_name, report_path, start_date, end_date):
    """Send a single report as attachment via Resend."""
    subject = f"WUG Report for {group_name}: {start_date:%Y-%m-%d %H:%M} → {end_date:%Y-%m-%d %H:%M}"
    html_body = (
        f"<p>Attached is the report for group '<strong>{group_name}</strong>'.</p>"
        f"<p>Period: {start_date:%Y-%m-%d %H:%M} to {end_date:%Y-%m-%d %H:%M}.</p>"
    )
    attachments = []
    try:
        with open(report_path, "rb") as f:
            content_bytes = f.read()
        attachments.append({
            "content": list(content_bytes),
            "filename": os.path.basename(report_path),
        })
    except Exception as e:
        print(f"[EMAIL] Failed to read attachment {report_path}: {e}")

    params = {
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


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def _scheduler_now() -> datetime:
    return datetime.now()


def _parse_time(s: str):
    s = (s or "00:00").strip()
    parts = s.split(":")
    h = int(parts[0]) if parts else 0
    m = int(parts[1]) if len(parts) > 1 else 0
    return h, m


def _weekday_index(day_code: str) -> int:
    code = (day_code or "").strip().lower()
    mapping = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
    return mapping.get(code, 0)


def _trigger_fires(job: dict, now: datetime, last_run_iso: str) -> tuple[bool, datetime | None]:
    schedule_type = (job.get("type") or "weekly").strip().lower()
    run_time_str = job.get("run_time") or "00:00"
    h, m = _parse_time(run_time_str)
    anchor = now.replace(hour=h, minute=m, second=0, microsecond=0)

    if schedule_type == "monthly":
        try:
            day_of_month = int(job.get("run_day_of_month") or 0)
        except (ValueError, TypeError):
            return False, None
        if day_of_month < 1 or now.day != day_of_month:
            return False, None
        if now < anchor:
            return False, anchor
        if last_run_iso:
            try:
                last_run = datetime.fromisoformat(last_run_iso)
                if last_run >= anchor:
                    return False, anchor
            except Exception:
                pass
        return True, anchor

    run_day = job.get("run_day")
    if not run_day:
        return False, None
    wd = _weekday_index(str(run_day))
    if now.weekday() != wd:
        return False, None
    if now < anchor:
        return False, anchor
    if last_run_iso:
        try:
            last_run = datetime.fromisoformat(last_run_iso)
            if last_run >= anchor:
                return False, anchor
        except Exception:
            pass
    return True, anchor


def _compute_window_from_trigger(anchor_dt: datetime, job: dict) -> tuple[datetime, datetime]:
    schedule_type = (job.get("type") or "weekly").strip().lower()
    run_date = anchor_dt.date()

    if schedule_type == "monthly":
        if run_date.month == 1:
            prev_first = run_date.replace(year=run_date.year - 1, month=12, day=1)
        else:
            prev_first = run_date.replace(month=run_date.month - 1, day=1)
        _, last_day = calendar.monthrange(prev_first.year, prev_first.month)
        start_d = min(int(job.get("period_start_day") or 1), last_day)
        end_d = min(int(job.get("period_end_day") or last_day), last_day)
        start_d = max(1, start_d)
        end_d = max(start_d, end_d)
        sh, sm = _parse_time(job.get("period_start_time") or "00:00")
        eh, em = _parse_time(job.get("period_end_time") or "23:59")
        start_dt = datetime(prev_first.year, prev_first.month, start_d, sh, sm, 0, 0)
        end_dt = datetime(prev_first.year, prev_first.month, end_d, eh, em, 59, 999999)
        return start_dt, end_dt

    week_start = run_date - timedelta(days=run_date.weekday())
    start_wd = _weekday_index(str(job.get("period_start_day") or "mon"))
    end_wd = _weekday_index(str(job.get("period_end_day") or "sun"))
    start_date = week_start + timedelta(days=start_wd)
    end_date = week_start + timedelta(days=end_wd)
    sh, sm = _parse_time(job.get("period_start_time") or "00:00")
    eh, em = _parse_time(job.get("period_end_time") or "23:59")
    start_dt = datetime(start_date.year, start_date.month, start_date.day, sh, sm, 0, 0)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, eh, em, 59, 999999)
    return start_dt, end_dt


def get_previous_month_range():
    now = datetime.now()
    first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if first_this_month.month == 1:
        first_prev_month = first_this_month.replace(year=first_this_month.year - 1, month=12)
    else:
        first_prev_month = first_this_month.replace(month=first_this_month.month - 1)
    return first_prev_month, first_this_month


def load_schedule_config():
    """Load schedule from report_schedule.json. Returns list of job dicts."""
    if not os.path.exists(SCHEDULE_JSON_FILE):
        return []
    with open(SCHEDULE_JSON_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    rows = raw.get("rows", [])
    if not isinstance(rows, list) or not rows:
        return []

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
        schedule_type = _clean(row.get("type")) or "weekly"
        report_type = _clean(row.get("report_type")) or "both"
        entry = {
            "id": job_id,
            "group": group_name,
            "type": schedule_type,
            "report_type": report_type,
            "run_day": _clean(row.get("run_day")),
            "run_time": _clean(row.get("run_time")),
            "period_start_day": row.get("period_start_day"),
            "period_start_time": _clean(row.get("period_start_time")),
            "period_end_day": row.get("period_end_day"),
            "period_end_time": _clean(row.get("period_end_time")),
            "run_day_of_month": row.get("run_day_of_month"),
        }
        if schedule_type == "monthly":
            try:
                entry["run_day_of_month"] = int(entry.get("run_day_of_month") or 1)
            except (ValueError, TypeError):
                entry["run_day_of_month"] = 1
            for k in ("period_start_day", "period_end_day"):
                try:
                    entry[k] = int(entry.get(k) or 1)
                except (ValueError, TypeError):
                    entry[k] = 1
        entry = {k: v for k, v in entry.items() if v is not None}
        if "id" not in entry:
            entry["id"] = None
        jobs.append(entry)
    return jobs


def run_scheduled_reports():
    """Execute all due scheduled reports; safe to call repeatedly from a background scheduler."""
    jobs = load_schedule_config()
    state = load_state()

    valid_job_ids = set()
    for idx, job in enumerate(jobs):
        group_name = (job.get("group") or "").strip()
        jid = (job.get("id") or "").strip() or f"{group_name}::__idx_{idx}"
        if jid:
            valid_job_ids.add(jid)

    if isinstance(state, dict):
        keys_to_delete = [k for k in state if "::__" in k and k != "__MONTHLY_ALL__"
                          and k.split("::__", 1)[0] not in valid_job_ids]
        for k in keys_to_delete:
            del state[k]

    now = _scheduler_now()

    # Monthly all-groups run
    last_monthly_str = state.get("__MONTHLY_ALL__")
    do_monthly = False
    if last_monthly_str is None:
        do_monthly = True
    else:
        try:
            last_monthly = datetime.fromisoformat(last_monthly_str)
            if last_monthly.year != now.year or last_monthly.month != now.month:
                do_monthly = True
        except Exception:
            do_monthly = True
    if do_monthly:
        print("[MONTHLY] Generating all-group monthly reports...")
        start_m, end_m = get_previous_month_range()
        groups = get_device_groups()
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
        send_all_reports_via_email(start_m, end_m)
        state["__MONTHLY_ALL__"] = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    name_to_id = {name: gid for gid, name in get_device_groups()}

    for idx, job in enumerate(jobs):
        group_name_stripped = (job.get("group") or "").strip()
        job_id = (job.get("id") or "").strip() or f"{group_name_stripped}::__idx_{idx}"

        if group_name_stripped not in name_to_id:
            print(f"[SKIP] Config group '{group_name_stripped}' not found in DeviceGroup table")
            continue
        st = (job.get("type") or "weekly").strip().lower()
        if st == "monthly" and job.get("run_day_of_month") is None:
            print(f"[SKIP] Job '{group_name_stripped}' (monthly) missing run_day_of_month")
            continue
        if st == "weekly" and not job.get("run_day"):
            print(f"[SKIP] Job '{group_name_stripped}' (weekly) missing run_day")
            continue
        if not job.get("run_time"):
            print(f"[SKIP] Job '{group_name_stripped}' missing run_time")
            continue

        state_key = f"{job_id}::__last_run"
        last_run_iso = state.get(state_key)
        should_run, anchor_dt = _trigger_fires(job, now, last_run_iso)
        if not should_run or anchor_dt is None:
            continue

        try:
            start_date, end_date = _compute_window_from_trigger(anchor_dt, job)
        except Exception as e:
            print(f"[SKIP] Window computation for '{group_name_stripped}': {e}")
            continue
        if start_date >= end_date:
            print(f"[SKIP] Invalid window for '{group_name_stripped}': start >= end")
            continue

        device_group_id = name_to_id[group_name_stripped]
        run_reports = (job.get("report_type") or "both").strip().lower()

        if run_reports in ("availability", "both"):
            try:
                print(f"[RUN] Availability for {group_name_stripped}: {start_date} -> {end_date}")
                availability_report_path = write_excel_for_group(
                    device_group_id=device_group_id,
                    start_date=start_date,
                    end_date=end_date,
                    group_name=group_name_stripped,
                )
                if availability_report_path:
                    send_single_report_email(
                        group_name=group_name_stripped,
                        report_path=availability_report_path,
                        start_date=start_date,
                        end_date=end_date,
                    )
            except Exception as e:
                print(f"[ERROR] Availability report for '{group_name_stripped}': {e}")

        if run_reports in ("uptime", "both"):
            try:
                print(f"[RUN] DeviceUpTime for {group_name_stripped}: {start_date} -> {end_date}")
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
                else:
                    print(f"[RUN] No uptime data for '{group_name_stripped}' in window")
            except Exception as e:
                print(f"[ERROR] DeviceUpTime report for '{group_name_stripped}': {e}")

        state[state_key] = anchor_dt.replace(second=0, microsecond=0).isoformat()

    save_state(state)
