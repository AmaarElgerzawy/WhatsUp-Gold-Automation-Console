 Deployment Guide

## Production Deployment Checklist

### Security

- [ ] Move credentials from localStorage to secure backend storage
- [ ] Add user authentication and authorization
- [ ] Enable HTTPS
- [ ] Restrict CORS origins to production domain
- [ ] Move all secrets to environment variables
- [ ] Review and remove hardcoded credentials from Python scripts
- [ ] Set up proper logging and monitoring

### Backend Deployment

1. **Environment Setup**

   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Environment Variables**

   - Create `.env` file from `env.example`
   - Set all sensitive values (database, SMTP, etc.)
   - Never commit `.env` to git

3. **Production Server**

   ```bash
   # Using uvicorn with production settings
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

   # Or use a process manager like systemd, PM2, or supervisor
   ```

4. **Database**
   - Ensure SQL Server is accessible
   - Verify connection string
   - Test database connectivity

### Frontend Deployment

1. **Build for Production**

   ```bash
   cd WebUI/Frontend/wug-ui
   npm run build
   ```

2. **Serve Static Files**

   - Option 1: Serve with a web server (nginx, Apache)
   - Option 2: Use FastAPI to serve static files
   - Option 3: Deploy to a CDN or static hosting service

3. **API Configuration**
   - Update API base URL in frontend code
   - Use environment variables for API endpoint
   - Ensure CORS is properly configured

## Monitoring

- Set up application logging
- Monitor API response times
- Track error rates
- Set up alerts for critical failures

## Backup Strategy

- Regular database backups
- Backup config and log files
- Version control for code
- Document configuration changes
