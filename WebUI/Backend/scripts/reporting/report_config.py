import os
from pathlib import Path

# Shared config for Reporting / ReportExcel

CONN_STR = os.environ.get(
    "WUG_DB_CONN",
    r"Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=WhatsUp;Trusted_Connection=yes;",
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FOLDER = os.environ.get("WUG_REPORT_OUTPUT", r"C:\\WUG_Exports")
CONFIG_FILE = os.environ.get("WUG_REPORT_SCHEDULE", str(BASE_DIR / "report_schedule.xlsx"))
STATE_FILE = os.environ.get("WUG_REPORT_STATE", str(BASE_DIR / "state.json"))

SMTP_SERVER = os.environ.get("WUG_SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT = int(os.environ.get("WUG_SMTP_PORT", "587"))
BREVO_USERNAME = os.environ.get("WUG_SMTP_USER", "9c44f9001@smtp-brevo.com")
BREVO_SMTP_KEY = os.environ.get("WUG_SMTP_KEY", "CHANGE_ME")
SENDER = os.environ.get("WUG_REPORT_SENDER", "snipergolden1234@gmail.com")
RECEIVER = os.environ.get("WUG_REPORT_RECEIVER", "snipergolden1234@gmail.com")
