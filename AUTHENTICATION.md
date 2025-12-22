# Authentication & Authorization System

## Overview

The WhatsUp Gold Automation Console now includes a comprehensive authentication and authorization system with role-based access control and activity logging.

## Features

- **User Authentication**: JWT token-based login system
- **Role-Based Access Control (RBAC)**: Three roles with different privileges
- **Page-Level Protection**: Routes are protected based on user privileges
- **Activity Logging**: All user actions are logged for audit purposes
- **Admin Interface**: Full user management and activity monitoring

## Default Credentials

When the system first runs, a default admin user is created:

- **Username**: `admin`
- **Password**: `admin`
- **Role**: `admin`

⚠️ **Important**: Change the default admin password immediately after first login!

## User Roles & Privileges

### Admin

- Full access to all pages and features
- User management (create, edit, delete users)
- View activity logs and statistics
- All privileges listed below

**Privileges:**

- `bulk_operations`
- `router_commands`
- `view_history`
- `view_backups`
- `manage_reports`
- `manage_credentials`
- `admin_access`

### Operator

- Can perform bulk operations and router commands
- Can view history and backups
- Cannot manage reports or credentials
- Cannot access admin functions

**Privileges:**

- `bulk_operations`
- `router_commands`
- `view_history`
- `view_backups`

### Viewer

- Read-only access
- Can view history and backups
- Cannot perform any operations

**Privileges:**

- `view_history`
- `view_backups`

## Page Access Mapping

| Page            | Required Privilege   |
| --------------- | -------------------- |
| Bulk Operations | `bulk_operations`    |
| Router Commands | `router_commands`    |
| History         | `view_history`       |
| Config Backups  | `view_backups`       |
| Report Schedule | `manage_reports`     |
| Credentials     | `manage_credentials` |
| Admin           | `admin_access`       |

## Storage

### Users

- **Location**: `WebUI/Backend/data/users.json`
- **Format**: JSON array of user objects
- **Fields**:
  - `id`: Unique user identifier
  - `username`: Login username
  - `email`: User email (optional)
  - `password_hash`: Bcrypt hashed password
  - `role`: User role (admin, operator, viewer)
  - `privileges`: Array of privilege strings
  - `active`: Boolean indicating if user is active
  - `created_at`: ISO timestamp

### Activity Logs

- **Location**: `WebUI/Backend/data/activity_log.json`
- **Format**: JSON array of log entries
- **Fields**:
  - `timestamp`: ISO timestamp
  - `user_id`: User who performed the action
  - `action`: Action name (e.g., "login", "bulk_operation")
  - `details`: Additional details about the action
  - `page`: Page/context where action occurred

## API Endpoints

### Authentication

- `POST /auth/login` - Login (public)
- `GET /auth/me` - Get current user info (authenticated)
- `GET /auth/check-page-access?page={page}` - Check if user can access a page

### Admin (requires `admin_access`)

- `GET /admin/users` - List all users
- `POST /admin/users` - Create new user
- `PUT /admin/users/{user_id}` - Update user
- `DELETE /admin/users/{user_id}` - Delete user
- `GET /admin/activity` - Get activity log
- `GET /admin/stats` - Get statistics

## Security Notes

### Production Recommendations

1. **JWT Secret**: Change `WUG_JWT_SECRET` environment variable to a strong random string (min 32 characters)

2. **Password Policy**: Consider adding:

   - Minimum password length
   - Password complexity requirements
   - Password expiration

3. **User Storage**: For production, consider migrating to a database instead of JSON files for:

   - Better performance
   - Concurrent access
   - ACID transactions

4. **Session Management**:

   - Current token expiration: 24 hours
   - Consider shorter expiration for sensitive operations
   - Implement refresh tokens for better security

5. **HTTPS**: Always use HTTPS in production to protect tokens in transit

6. **Rate Limiting**: Consider adding rate limiting to login endpoint

## Activity Logging

All user actions are automatically logged, including:

- Login/logout
- Bulk operations
- Router command executions
- File operations (view, delete, rename, download)
- Config/backup viewing
- Report schedule updates
- User management operations (admin only)

Logs are kept in `activity_log.json` with a maximum of 10,000 entries (oldest entries are removed when limit is reached).

## Frontend Implementation

### Login Flow

1. User enters credentials on login page
2. Backend validates and returns JWT token
3. Token stored in localStorage
4. User data stored in localStorage
5. Navigation items filtered based on privileges
6. Protected routes check access before rendering

### API Calls

All API calls use the `apiCall` helper function which:

- Automatically includes Authorization header with JWT token
- Handles 401 errors by clearing auth and redirecting to login
- Properly handles FormData for file uploads

## Example: Creating a New User

Via Admin Page:

1. Navigate to Admin → Users
2. Click "New User"
3. Enter username, password, email (optional), and role
4. Click "Create User"

Via API:

```bash
curl -X POST http://localhost:8000/admin/users \
  -H "Authorization: Bearer <token>" \
  -F "username=newuser" \
  -F "password=securepass123" \
  -F "email=newuser@example.com" \
  -F "role=operator"
```

## Troubleshooting

### "Invalid authentication credentials"

- Token may have expired (24 hours)
- Token may be invalid
- User may have been deactivated
- Solution: Log out and log back in

### "Insufficient privileges"

- User doesn't have the required privilege for the action
- Solution: Contact an admin to grant the required privilege

### Cannot login with default admin

- Ensure backend has started and created the users.json file
- Check that `WebUI/Backend/data/` directory exists
- Verify the default admin user exists in users.json
