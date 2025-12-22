from datetime import datetime, timedelta
from typing import Optional, List, Dict
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
import json
import os

# JWT Configuration
SECRET_KEY = os.environ.get("WUG_JWT_SECRET", "your-secret-key-change-in-production-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing - using bcrypt directly for better compatibility
security = HTTPBearer()

# User storage
USERS_FILE = Path(__file__).parent / "data" / "users.json"
ACTIVITY_LOG_FILE = Path(__file__).parent / "data" / "activity_log.json"

# Privileges/Pages mapping
PAGE_PRIVILEGES = {
    "bulk": "bulk_operations",
    "routers": "router_commands",
    "history": "view_history",
    "backups": "view_backups",
    "reports": "manage_reports",
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


def get_users_file():
    """Ensure users file exists with default admin user."""
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        # Create default admin user (password: admin) - write directly to avoid recursion
        password_hash = get_password_hash("admin")
        default_users = [
            {
                "id": "admin",
                "username": "admin",
                "email": "admin@example.com",
                "password_hash": password_hash,
                "role": "admin",
                "privileges": ROLE_PRIVILEGES["admin"],
                "active": True,
                "created_at": datetime.now().isoformat(),
            }
        ]
        # Write directly to file instead of calling save_users to avoid recursion
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_users, f, indent=2, ensure_ascii=False)
    return USERS_FILE


def load_users() -> List[Dict]:
    """Load users from JSON file."""
    try:
        users_file = get_users_file()
        with open(users_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_users(users: List[Dict]):
    """Save users to JSON file."""
    # Ensure directory exists, but don't create default users here
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user by username."""
    users = load_users()
    for user in users:
        if user["username"] == username and user.get("active", True):
            return user
    return None


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID."""
    users = load_users()
    for user in users:
        if user["id"] == user_id and user.get("active", True):
            return user
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        # Encode strings to bytes for bcrypt
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # Encode password to bytes, generate salt, and hash
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def check_privilege(user: Dict, required_privilege: str) -> bool:
    """Check if user has required privilege."""
    user_privileges = user.get("privileges", [])
    return required_privilege in user_privileges


def require_privilege(privilege: str):
    """Dependency to require a specific privilege."""
    def privilege_checker(current_user: Dict = Depends(get_current_user)) -> Dict:
        if not check_privilege(current_user, privilege):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required: {privilege}",
            )
        return current_user
    return privilege_checker


def log_activity(user_id: str, action: str, details: str = "", page: str = ""):
    """Log user activity."""
    try:
        ACTIVITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass  # Directory might already exist
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": action,
        "details": details,
        "page": page,
    }
    
    # Load existing logs
    logs = []
    if ACTIVITY_LOG_FILE.exists():
        try:
            with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []
    
    # Append new log (keep last 10000 entries)
    logs.append(log_entry)
    if len(logs) > 10000:
        logs = logs[-10000:]
    
    # Save logs
    with open(ACTIVITY_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
