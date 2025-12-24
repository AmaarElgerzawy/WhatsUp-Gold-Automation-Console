# Docker Deployment Guide

This guide explains how to deploy the WhatsUp Automation Console using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 2GB+ free disk space

## Quick Start

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd "WhatsUP Automatons"
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start services**

   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Docker Compose Files

### `docker-compose.yml` (Base)

Base configuration for all environments.

### `docker-compose.dev.yml` (Development)

Development overrides with:

- Hot reload for backend
- Source code mounting
- Development-friendly settings

**Usage:**

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### `docker-compose.prod.yml` (Production)

Production overrides with:

- Named volumes for data persistence
- Logging configuration
- Restart policies

**Usage:**

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Required
WUG_JWT_SECRET=your-very-long-random-secret-key-min-32-chars

# Optional - Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Optional - API URL (for frontend build)
REACT_APP_API_URL=http://localhost:8000

# Optional - Database (if using external SQL Server)
DB_CONNECTION_STRING=Driver={ODBC Driver 17 for SQL Server};Server=db-server;Database=WhatsUp;UID=user;PWD=password;
```

## Building Images

### Build all services

```bash
docker-compose build
```

### Build specific service

```bash
docker-compose build backend
docker-compose build frontend
```

### Build with custom API URL

```bash
REACT_APP_API_URL=https://api.example.com docker-compose build frontend
```

## Running Containers

### Start in background

```bash
docker-compose up -d
```

### Start with logs

```bash
docker-compose up
```

### Start specific service

```bash
docker-compose up -d backend
```

### Restart services

```bash
docker-compose restart
```

## Data Persistence

Data is persisted using Docker volumes:

- **All data**: `./WebUI/Backend/data` (users, logs, configs, backups)
  - `data/configs/` - Saved configurations
  - `data/logs/` - Execution logs
  - `data/backups/` - Device backups

In production, consider using named volumes (see `docker-compose.prod.yml`).

## Health Checks

Both services include health checks:

- **Backend**: Checks `/docs` endpoint
- **Frontend**: Checks nginx health endpoint

View health status:

```bash
docker-compose ps
```

## Logs

### View all logs

```bash
docker-compose logs -f
```

### View specific service logs

```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### View last 100 lines

```bash
docker-compose logs --tail=100 backend
```

## Troubleshooting

### Backend won't start

1. Check logs: `docker-compose logs backend`
2. Verify database connection (if using external DB)
3. Check port availability: `netstat -an | grep 8000`

### Frontend shows connection errors

1. Verify `REACT_APP_API_URL` matches backend URL
2. Check backend is running: `docker-compose ps`
3. Check browser console for CORS errors

### Permission errors

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER WebUI/Backend/data
```

### Rebuild after code changes

```bash
docker-compose build --no-cache
docker-compose up -d
```

## Production Deployment

### 1. Set environment variables

```bash
export WUG_JWT_SECRET=$(openssl rand -base64 32)
export REACT_APP_API_URL=https://api.yourdomain.com
```

### 2. Build production images

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
```

### 3. Start services

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. Set up reverse proxy (nginx/traefik)

Configure your reverse proxy to route:

- `/api/*` → `backend:8000`
- `/*` → `frontend:80`

### 5. Set up SSL/TLS

Use Let's Encrypt or your SSL provider with the reverse proxy.

## Using Makefile

For convenience, use the provided Makefile:

```bash
make build      # Build images
make up         # Start services
make down       # Stop services
make logs       # View logs
make dev        # Start in dev mode
make prod       # Start in prod mode
make clean      # Clean up containers
```

## Multi-Architecture Support

To build for different architectures:

```bash
# Build for ARM64 (Apple Silicon, Raspberry Pi)
docker buildx build --platform linux/arm64 -t wug-backend:arm64 -f Dockerfile.backend .

# Build for AMD64
docker buildx build --platform linux/amd64 -t wug-backend:amd64 -f Dockerfile.backend .
```

## Backup and Restore

### Backup data

```bash
docker-compose exec backend tar -czf /tmp/backup.tar.gz /app/WebUI/Backend/data
docker cp wug-backend:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz
```

### Restore data

```bash
docker cp ./backup-20231218.tar.gz wug-backend:/tmp/
docker-compose exec backend tar -xzf /tmp/backup.tar.gz -C /
```

## Monitoring

### Resource usage

```bash
docker stats
```

### Container status

```bash
docker-compose ps
```

### Inspect logs

```bash
docker-compose logs --tail=50 backend
```

## Security Considerations

1. **Change default JWT secret** in `.env`
2. **Use secrets management** (Docker secrets, Kubernetes secrets, etc.)
3. **Limit exposed ports** in production
4. **Use reverse proxy** with SSL/TLS
5. **Regular updates**: Keep base images updated
6. **Network isolation**: Use Docker networks appropriately

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build images
        run: docker-compose build
      - name: Run tests
        run: docker-compose run backend pytest
```
