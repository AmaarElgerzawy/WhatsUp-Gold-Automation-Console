/**
 * Centralized configuration and constants for WhatsUp Automation Frontend
 * Reduces code duplication and makes it easy to change values globally
 */

// ================= API CONFIGURATION =================
export const API_BASE_URL = "http://wug.automation:8000";

// API endpoint paths
export const ENDPOINTS = {
  // Authentication
  AUTH_LOGIN: "auth/login",
  AUTH_ME: "auth/me",
  AUTH_CHECK_PAGE_ACCESS: "auth/check-page-access",

  // Bulk operations
  RUN_BULK: "run",
  BULK_TEMPLATE: "bulk/template",

  // Router commands
  ROUTERS_RUN_INTERACTIVE: "routers/run-interactive",
  ROUTERS_RUN_SIMPLE: "routers/run-simple",

  // Configuration files
  CONFIGS: "configs",

  // Backups
  BACKUPS_DEVICES: "backups/devices",
  BACKUPS_DEVICE: "backups",
  BACKUP_ROUTERS: "backup/routers",

  // Reports
  REPORTS_SCHEDULE: "reports/schedule",
  REPORTS_RUN_NOW: "reports/run-now",
};

// ================= STORAGE KEYS =================
export const STORAGE_KEYS = {
  AUTH_TOKEN: "wug_auth_token",
  USER: "wug_user",
};

// ================= PRIVILEGE DEFINITIONS =================
export const PRIVILEGES = {
  BULK_OPERATIONS: "bulk_operations",
  ROUTER_COMMANDS: "router_commands",
  VIEW_HISTORY: "view_history",
  VIEW_BACKUPS: "view_backups",
  MANAGE_REPORTS: "manage_reports",
  MANAGE_CREDENTIALS: "manage_credentials",
  ADMIN_ACCESS: "admin_access",
};

// Page-to-privilege mapping
export const PAGE_PRIVILEGE_MAP = {
  bulk: PRIVILEGES.BULK_OPERATIONS,
  routers: PRIVILEGES.ROUTER_COMMANDS,
  history: PRIVILEGES.VIEW_HISTORY,
  backups: PRIVILEGES.VIEW_BACKUPS,
  reports: PRIVILEGES.MANAGE_REPORTS,
  credentials: PRIVILEGES.MANAGE_CREDENTIALS,
  admin: PRIVILEGES.ADMIN_ACCESS,
};

// ================= OPERATION TYPES =================
export const OPERATIONS = {
  ADD: "add",
  UPDATE: "update",
  DELETE: "delete",
  INTERACTIVE: "interactive",
  SIMPLE: "simple",
};

// ================= FORM FIELD NAMES =================
export const FORM_FIELDS = {
  USERNAME: "username",
  PASSWORD: "password",
  OPERATION: "operation",
  FILE: "file",
  CONFIG_NAME: "config_name",
  LOG_NAME: "log_name",
  ROUTERS: "routers",
  TASKS_JSON: "tasks_json",
  ENABLE_PASSWORD: "enable_password",
};

// ================= CONTENT TYPES =================
export const CONTENT_TYPES = {
  JSON: "application/json",
  FORM_URLENCODED: "application/x-www-form-urlencoded",
  EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

// ================= HTTP METHODS =================
export const HTTP_METHODS = {
  GET: "GET",
  POST: "POST",
  PUT: "PUT",
  DELETE: "DELETE",
};

// ================= HTTP STATUS CODES =================
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500,
};

// ================= THEME & STYLE CONSTANTS =================
export const COLORS = {
  BG_GRADIENT_START: "#1f2937",
  BG_GRADIENT_END: "#020617",
  TEXT_SECONDARY: "#9ca3af",
  ERROR_BG: "rgba(248, 113, 113, 0.1)",
  ERROR_BORDER: "rgba(248, 113, 113, 0.5)",
  ERROR_TEXT: "#fecaca",
};

export const SPACING = {
  SM: 8,
  MD: 12,
  LG: 16,
  XL: 20,
  XXL: 24,
};

// ================= FILE EXTENSIONS =================
export const FILE_EXTENSIONS = {
  EXCEL: ".xlsx",
  CSV: ".csv",
  TXT: ".txt",
  JSON: ".json",
  LOG: ".log",
};

// ================= TEMPLATE FILENAMES =================
export const TEMPLATE_NAMES = {
  BULK_ADD: "bulk_add_template.xlsx",
  BULK_UPDATE: "bulk_update_template.xlsx",
  BULK_DELETE: "bulk_delete_template.xlsx",
};

// ================= ERROR MESSAGES =================
export const ERROR_MESSAGES = {
  NO_FILE_SELECTED: "Select an Excel file",
  NO_USERNAME_PASSWORD: "Please enter both username and password",
  LOGIN_FAILED: "Login failed",
  NETWORK_ERROR: "Network error",
  TEMPLATE_DOWNLOAD_FAILED: "Failed to download template",
  TEMPLATE_DOWNLOAD_ERROR: "Error downloading template",
  SERVER_ERROR: "Server error",
  UNAUTHORIZED: "Unauthorized access",
};

// ================= LOADING & STATUS MESSAGES =================
export const STATUS_MESSAGES = {
  LOADING: "Loading...",
  SIGNING_IN: "Signing in...",
  SIGNING_IN_LABEL: "Signing in...",
  SIGN_IN_LABEL: "Sign In",
  UPLOADING: "Uploading...",
  PROCESSING: "Processing...",
};

// ================= PAGE LABELS & TITLES =================
export const PAGE_TITLES = {
  BULK: "Bulk device operations",
  ROUTERS: "Router commands",
  HISTORY: "History",
  BACKUPS: "Configuration Backups",
  REPORTS: "Reports",
  CREDENTIALS: "Credentials Manager",
  ADMIN: "Admin Panel",
};

// ================= UTILITY STRINGS =================
export const UI_LABELS = {
  UPLOAD_AND_RUN: "Upload & run",
  DOWNLOAD_TEMPLATE: "Download template",
  OPERATION: "Operation",
  FILE: "Excel file (.xlsx)",
  CONFIG_NAME: "Config name (optional)",
  LOG_NAME: "Log name (optional)",
  EXCEL_DRIVEN: "Excel driven",
  SIGN_IN_TO_CONTINUE: "Please sign in to continue",
  CONSOLE_TITLE: "WhatsUp Automation Console",
  NETWORK_CONSOLE_TITLE: "Network Automation Console",
};

// ================= ICON STRINGS =================
export const ICONS = {
  DOCUMENT: "📄",
  CHECK: "✓",
  ERROR: "✕",
};

// ================= DATE & TIME FORMAT =================
export const DATE_FORMAT = "YYYY-MM-DD";
export const TIME_FORMAT = "HH:MM:SS";
export const DATETIME_FORMAT = "YYYY-MM-DD HH:MM:SS";

// ================= AUTHORIZATION HEADER =================
export const AUTH_HEADER_KEY = "Authorization";
export const AUTH_HEADER_PREFIX = "Bearer";

/**
 * Helper function to build full API URLs
 * @param {string} path - API endpoint path
 * @returns {string} Full API URL
 */
export function apiUrl(path) {
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${API_BASE_URL}/${cleanPath}`;
}

/**
 * Helper function to get authorization headers
 * @param {string} token - JWT token
 * @returns {object} Authorization headers object
 */
export function getAuthorizationHeader(token) {
  return {
    [AUTH_HEADER_KEY]: `${AUTH_HEADER_PREFIX} ${token}`,
  };
}
