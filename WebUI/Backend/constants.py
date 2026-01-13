"""
Centralized configuration and constants for WhatsUp Automation Backend
Reduces code duplication and makes it easy to change values globally
"""

import os
from pathlib import Path
from datetime import timedelta

# ================= DATABASE CONFIGURATION =================
# Database connection string - can be overridden via environment variable
CONNECTION_STRING = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=localhost;"
    "Database=WhatsUp;"
    "UID=maxor;"
    "PWD=MAXOR321;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)

# ================= API & SECURITY CONFIGURATION =================
# CORS allowed origins
ALLOWED_ORIGINS = ["http://api:3000", "http://wug.automation:3000"]

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("WUG_JWT_SECRET", "your-secret-key-change-in-production-min-32-chars")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ================= DIRECTORY PATHS =================
BASEDIR = Path(__file__).resolve().parent

# Scripts directories
SCRIPTS_DIR = BASEDIR / "scripts"
BULK_SCRIPTS_DIR = SCRIPTS_DIR / "bulk"
ROUTER_SCRIPTS_DIR = SCRIPTS_DIR / "routers"
BACKUP_SCRIPTS_DIR = SCRIPTS_DIR / "backup"
REPORTING_SCRIPTS_DIR = SCRIPTS_DIR / "reporting"

# Data directories
DATA_DIR = BASEDIR / "data"
CONFIG_DIR = DATA_DIR / "configs"
LOG_DIR = DATA_DIR / "logs"
BACKUP_BASE_DIR = BACKUP_SCRIPTS_DIR / "backups"

# Configuration subdirectories
CONFIG_BULK_ADD_DIR = CONFIG_DIR / "bulk_add"
CONFIG_BULK_UPDATE_DIR = CONFIG_DIR / "bulk_update"
CONFIG_BULK_DELETE_DIR = CONFIG_DIR / "bulk_delete"
CONFIG_ROUTER_SIMPLE_DIR = CONFIG_DIR / "router_simple"
CONFIG_ROUTER_INTERACTIVE_DIR = CONFIG_DIR / "router_interactive"

# Data files
TEMPLATE_FILE = DATA_DIR / "bulk_templates.json"
ROUTERS_FILE = BACKUP_SCRIPTS_DIR / "routers.txt"
REPORT_SCHEDULE_FILE = REPORTING_SCRIPTS_DIR / "report_schedule.xlsx"
USERS_FILE = DATA_DIR / "users.json"
ACTIVITY_LOG_FILE = DATA_DIR / "activity_log.json"

# ================= BULK OPERATION CONSTANTS =================
# Bulk operation scripts
SCRIPTS = {
    "add": str(BULK_SCRIPTS_DIR / "BulkAdd-WUGv14.py"),
    "update": str(BULK_SCRIPTS_DIR / "BulkUpdate-WUGv14.py"),
    "delete": str(BULK_SCRIPTS_DIR / "BulkDelete-WUGv14.py"),
}

# CSV filenames for bulk operations
CSV_NAMES = {
    "add": "Add.csv",
    "update": "Update.csv",
    "delete": "Delete.csv",
}

# ================= ENVIRONMENT VARIABLES =================
# Environment variable names for router commands
ENV_WUG_ROUTERS = "WUG_ROUTERS"
ENV_WUG_TASKS = "WUG_TASKS"
ENV_WUG_SSH_USER = "WUG_SSH_USER"
ENV_WUG_SSH_PASS = "WUG_SSH_PASS"
ENV_WUG_SSH_ENABLE = "WUG_SSH_ENABLE"

# ================= PRIVILEGE & ROLE DEFINITIONS =================
# Page-to-privilege mapping
PAGE_PRIVILEGES = {
    "bulk": "bulk_operations",
    "routers": "router_commands",
    "history": "view_history",
    "backups": "view_backups",
    "reports": "manage_reports",
    "generatereports": "manage_reports",
    "credentials": "manage_credentials",
    "admin": "admin_access",
}

# Default privileges for roles
ROLE_PRIVILEGES = {
    "admin": [
        "bulk_operations",
        "router_commands",
        "view_history",
        "view_backups",
        "manage_reports",
        "manage_credentials",
        "admin_access",
    ],
    "operator": [
        "bulk_operations",
        "router_commands",
        "view_history",
        "view_backups",
    ],
    "viewer": [
        "view_history",
        "view_backups",
    ],
}

# Available privileges list (for admin UI)
AVAILABLE_PRIVILEGES = [
    {"id": "bulk_operations", "name": "Bulk Operations", "description": "Execute bulk device add/update/delete operations"},
    {"id": "router_commands", "name": "Router Commands", "description": "Execute simple and interactive router commands"},
    {"id": "view_history", "name": "View History", "description": "View saved configs and execution logs"},
    {"id": "view_backups", "name": "View Backups", "description": "View configuration backups"},
    {"id": "manage_reports", "name": "Manage Reports", "description": "Manage report schedules"},
    {"id": "manage_credentials", "name": "Manage Credentials", "description": "Manage SSH and device credentials"},
    {"id": "admin_access", "name": "Admin Access", "description": "Access admin panel and user management"},
]

# ================= CONTENT TYPE & MEDIA TYPES =================
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_FORM_URLENCODED = "application/x-www-form-urlencoded"
MEDIA_TYPE_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ================= ENCODING =================
DEFAULT_ENCODING = "utf-8"
ENCODING_UTF8_SIG = "utf-8-sig"

# ================= DATABASE QUERIES =================
# Common SQL queries
QUERY_DEVICE_TYPES = "SELECT nDeviceTypeID, sDisplayName FROM DeviceType"
QUERY_DEVICE_GROUPS = "SELECT nDeviceGroupID, sGroupName FROM DeviceGroup"

# ================= LOG PATTERNS & CONSTANTS =================
# Log-related constants
LOG_SEPARATOR = "="
LOG_PREFIX_EXIT_CODE = "EXIT CODE:"
LOG_PREFIX_STDOUT = "STDOUT:"
LOG_PREFIX_STDERR = "STDERR:"
WORKDIR_PLACEHOLDER = "[WORKDIR]"

# ================= FORM FIELD NAMES =================
# Form field names used in POST requests
FORM_OPERATION = "operation"
FORM_FILE = "file"
FORM_CONFIG_NAME = "config_name"
FORM_LOG_NAME = "log_name"
FORM_USERNAME = "username"
FORM_PASSWORD = "password"
FORM_ROUTERS = "routers"
FORM_TASKS_JSON = "tasks_json"
FORM_ENABLE_PASSWORD = "enable_password"

# ================= ERROR MESSAGES =================
ERROR_INVALID_OPERATION = "Invalid operation"
ERROR_UNKNOWN_TEMPLATE = "Unknown template"
ERROR_CSV_EMPTY = "CSV empty or headers mismatch"
ERROR_OPERATION_NOT_FOUND = "Operation not found"

# ================= LOG FILE NAMES =================
LOG_FILE_PREFIX_BULK = "bulk_operation"
LOG_FILE_PREFIX_INTERACTIVE = "interactive_commands"
LOG_FILE_PREFIX_SIMPLE = "simple_commands"
LOG_FILE_PREFIX_BACKUP = "backup"

# ================= ACTIVITY LOG ACTIONS =================
ACTIVITY_BULK_OPERATION = "bulk_operation"
ACTIVITY_INTERACTIVE_COMMANDS = "interactive_commands"
ACTIVITY_INTERACTIVE_COMMANDS_ERROR = "interactive_commands_error"
ACTIVITY_SIMPLE_COMMANDS = "simple_commands"
ACTIVITY_SIMPLE_COMMANDS_ERROR = "simple_commands_error"
ACTIVITY_BACKUP = "backup"

# ================= CONFIG FILE PREFIXES =================
CONFIG_PREFIX_BULK = "bulk_config"
CONFIG_PREFIX_INTERACTIVE = "interactive_config"
CONFIG_PREFIX_SIMPLE = "simple_config"

# ================= DEFAULT DATABASE VALUES =================
# Default values for database operations
DEFAULT_WORST_STATE_ID = 1
DEFAULT_BEST_STATE_ID = 1
TEMP_DEFAULT_NETIF_ID = 0
