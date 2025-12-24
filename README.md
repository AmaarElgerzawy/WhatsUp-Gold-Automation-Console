# WhatsUp Gold Automation Console

A modern web-based automation platform for managing WhatsUp Gold network monitoring operations, including bulk device management, router configuration, config backups, and scheduled reporting.

## Features

- **Bulk Device Operations**: Import Excel files to add, update, or delete devices in bulk
- **Router Configuration**: Execute simple or interactive command sequences on multiple routers
- **Config Backups**: Browse and manage device configuration snapshots
- **Scheduled Reporting**: Manage automated report generation schedules
- **Credential Management**: Securely store and reuse SSH credentials across operations
- **History & Logs**: View saved configurations and execution logs with rename and download capabilities

## Tech Stack

### Backend

- **FastAPI** - Modern Python web framework
- **pandas** - Excel file processing
- **pyodbc** - SQL Server database connectivity
- **netmiko** - Network device automation (via Python scripts)

### Frontend

- **React 19** - UI framework
- **AG Grid** - Excel-like data grid for report scheduling
- **Modern CSS** - Dark theme with glassmorphism effects

## Project Structure

```
WhatsUP Automatons/
├── WebUI/
│   ├── Backend/          # FastAPI server
│   │   ├── scripts/      # All automation scripts
│   │   │   ├── bulk/     # Bulk operations
│   │   │   ├── routers/  # Router commands
│   │   │   ├── backup/   # Config backups
│   │   │   └── reporting/ # Report generation
│   │   ├── data/         # Runtime data (configs, logs, backups)
│   │   ├── main.py       # FastAPI application
│   │   └── auth.py       # Authentication module
│   └── Frontend/
│       └── wug-ui/       # React application
└── [Legacy directories - kept for reference]
    ├── Bulk Changes/      # (scripts moved to WebUI/Backend/scripts/bulk/)
    ├── Many Routers Config/ # (scripts moved to WebUI/Backend/scripts/routers/)
    ├── Config Backup/     # (scripts moved to WebUI/Backend/scripts/backup/)
    └── Reporting/         # (scripts moved to WebUI/Backend/scripts/reporting/)
```

## Prerequisites

- Python 3.8+ (tested with Python 3.13)
- Node.js 16+ and npm
- SQL Server with WhatsUp Gold database
- ODBC Driver 17 for SQL Server
- Network access to routers/devices

## Quick Start with Docker (Recommended)

The easiest way to run the application is using Docker Compose:

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The application will be available at:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

See [DOCKER.md](DOCKER.md) for detailed Docker instructions.

## Installation (Manual) Setup

1. Navigate to the project root:

```bash
cd "WhatsUP Automatons"
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Configure database connection in `WebUI/Backend/main.py`:

   - Update `CONNECTION_STRING` if needed (defaults to localhost with Windows Authentication)

5. Start the FastAPI server:

```bash
cd WebUI/Backend
uvicorn main:app --reload --port 8000
```

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd WebUI/Frontend/wug-ui
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm start
```

The application will open at `http://localhost:3000` (or the next available port).

## Configuration

### Database Connection

The backend uses Windows Authentication by default. To change the connection string, edit `WebUI/Backend/main.py`:

```python
CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=WhatsUp;"
    "Trusted_Connection=yes;"
)
```

### Credentials Storage

SSH credentials are stored in browser localStorage. For production, consider:

- Backend API for credential storage
- Encryption at rest
- User authentication/authorization

### File Paths

The backend uses the following structure (all within `WebUI/Backend/`):

- `scripts/bulk/` - Bulk operation scripts
- `scripts/routers/` - Router command scripts
- `scripts/backup/` - Backup scripts and router list
- `scripts/reporting/` - Report generation scripts and schedule
- `data/configs/` - Saved configurations
- `data/logs/` - Execution logs
- `data/backups/` - Device configuration backups

**Note**: The project has been reorganized for Docker compatibility. See [MIGRATION.md](MIGRATION.md) for details.

## Usage

### Bulk Device Operations

1. Prepare an Excel file with device information
2. Select operation type (Add/Update/Delete)
3. Upload the Excel file
4. Optionally provide custom names for saved config and log files
5. Click "Run bulk operation"

### Router Commands

1. **Simple Commands**: Enter routers and config commands, select credentials
2. **Interactive Commands**: Build a sequence of tasks (config, exec, interactive exec, write memory)
3. Select or enter SSH credentials
4. Optionally name the saved config and log files
5. Execute the commands

### Credential Management

1. Navigate to **Settings → Credentials**
2. Create credential sets with name, username, password, and optional enable password
3. Credentials are automatically available in router command forms
4. Edit or delete credentials as needed

### Viewing History

- **Saved Configs**: Browse configurations saved from operations
- **Execution Logs**: View detailed logs from command executions
- **Rename & Download**: Click ✏ to rename, ⬇ to download files

## API Endpoints

### Bulk Operations

- `POST /run` - Execute bulk add/update/delete operation

### Router Commands

- `POST /routers/run-simple` - Execute simple config commands
- `POST /routers/run-interactive` - Execute interactive command sequence

### Configs & Logs

- `GET /configs/{section}` - List configs by section
- `GET /configs/{section}/{name}` - Get config content or download
- `PUT /configs/{section}/{name}` - Rename config file
- `DELETE /configs/{section}/{name}` - Delete config file
- `GET /logs` - List all log files
- `GET /logs/{name}` - Get log content or download
- `PUT /logs/{name}` - Rename log file
- `DELETE /logs/{name}` - Delete log file

### Backups

- `GET /backups/devices` - List devices with backups
- `GET /backups/{device}` - List configs for a device
- `GET /backups/{device}/{filename}` - View backup file

### Reporting

- `GET /reports/schedule` - Get report schedule
- `POST /reports/schedule` - Update report schedule

## Docker Deployment

See [DOCKER.md](DOCKER.md) for comprehensive Docker deployment instructions.

### Quick Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Development mode (with hot reload)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Development

### Backend Development

The FastAPI server includes:

- Automatic API documentation at `http://localhost:8000/docs`
- CORS enabled for local development
- Hot reload with `--reload` flag

### Frontend Development

The React app uses:

- Create React App with React 19
- Hot module replacement
- ESLint configuration

## Security Notes

⚠️ **Important**: This application is designed for internal/development use. For production:

1. **Credentials**: Move from localStorage to secure backend storage
2. **Authentication**: Add user authentication and authorization
3. **HTTPS**: Use HTTPS in production
4. **CORS**: Restrict CORS origins to specific domains
5. **Secrets**: Move hardcoded credentials to environment variables or secure config

## Troubleshooting

### Database Connection Issues

- Verify SQL Server is running
- Check ODBC Driver 17 is installed
- Verify database name and server address

### Router Connection Issues

- Verify network connectivity to routers
- Check SSH credentials are correct
- Ensure routers allow SSH connections

### Frontend Not Loading

- Check backend is running on port 8000
- Verify CORS is enabled
- Check browser console for errors

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and updates.

## Support

For issues and questions, please open an issue on GitHub.
