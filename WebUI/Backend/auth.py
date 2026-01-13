from datetime import datetime, timedelta
from typing import Optional, List, Dict
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
import json
import os

# Import constants
from constants import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    USERS_FILE,
    ACTIVITY_LOG_FILE,
    PAGE_PRIVILEGES,
    ROLE_PRIVILEGES,
    AVAILABLE_PRIVILEGES,
    DEFAULT_ENCODING,
)

# Password hashing - using bcrypt directly for better compatibility
security = HTTPBearer()


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
        with open(USERS_FILE, "w", encoding=DEFAULT_ENCODING) as f:
            json.dump(default_users, f, indent=2, ensure_ascii=False)
    return USERS_FILE


def load_users() -> List[Dict]:
    """Load users from JSON file."""
    try:
        users_file = get_users_file()
        with open(users_file, "r", encoding=DEFAULT_ENCODING) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_users(users: List[Dict]):
    """Save users to JSON file."""
    # Ensure directory exists, but don't create default users here
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding=DEFAULT_ENCODING) as f:
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
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
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
