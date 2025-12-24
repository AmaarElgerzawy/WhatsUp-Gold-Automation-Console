#!/bin/bash
set -e

echo "Starting WhatsUp Automation Backend..."

# Create necessary directories
mkdir -p WebUI/Backend/data/configs/{bulk_add,bulk_update,bulk_delete,router_simple,router_interactive}
mkdir -p WebUI/Backend/data/logs
mkdir -p WebUI/Backend/data/backups

# Wait for database to be ready (if using external DB)
if [ -n "$DB_CONNECTION_STRING" ] && [ -z "$DB_TRUSTED_CONNECTION" ]; then
    echo "Waiting for database to be ready..."
    until python -c "import pyodbc; pyodbc.connect('$DB_CONNECTION_STRING')" 2>/dev/null; do
        echo "Database is unavailable - sleeping"
        sleep 1
    done
    echo "Database is ready!"
fi

# Run the application
exec "$@"
