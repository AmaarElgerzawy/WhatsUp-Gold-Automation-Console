# Setup Guide

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd "WhatsUP Automatons"
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the server
cd WebUI/Backend
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd WebUI/Frontend/wug-ui

# Install dependencies
npm install

# Start development server
npm start
```

### 4. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Configuration

1. **Database**: Ensure SQL Server is running and update connection string in `WebUI/Backend/main.py` if needed
2. **Credentials**: Use the Credentials page in the UI to store SSH credentials
3. **File Paths**: Verify folder structure matches the expected paths in `main.py`

## Troubleshooting

- **Port already in use**: Change ports in uvicorn command or npm start
- **Database connection error**: Verify SQL Server is running and ODBC driver is installed
- **Module not found**: Ensure virtual environment is activated and requirements.txt is installed
