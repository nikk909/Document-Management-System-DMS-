# Troubleshooting Guide

## Common Issues and Solutions

### 1. Backend Won't Start

**Error**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```bash
# Ensure you're in the virtual environment
cd backend
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install all dependencies
pip install -r requirements.txt
```

---

### 2. Database Connection Failed

**Error**: `OperationalError: (2003, "Can't connect to MySQL server")`

**Solutions**:
- Check if MySQL container is running: `docker ps`
- Verify MySQL port in `config.yaml` matches `docker-compose.yaml` (default: 3306)
- Check MySQL credentials in `config.yaml`
- Wait 30 seconds after starting Docker containers for MySQL to initialize

**Test Connection**:
```bash
docker exec -it dms-mysql mysql -uroot -proot -e "SHOW DATABASES;"
```

---

### 3. MinIO Connection Failed

**Error**: `S3Error: Invalid endpoint`

**Solutions**:
- Check if MinIO container is running: `docker ps`
- Access MinIO console at http://localhost:9001
- Verify `endpoint`, `access_key`, and `secret_key` in `config.yaml`
- Ensure MinIO is accessible: `curl http://localhost:9000/minio/health/live`

---

### 4. Port Already in Use

**Error**: `Address already in use` or `Port 8000 is already in use`

**Solutions**:

**Option 1**: Kill the process using the port
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

**Option 2**: Change the backend port
```bash
# Start backend on different port
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

Then update `frontend/app.js`:
```javascript
const API_BASE_URL = 'http://localhost:8001';
```

---

### 5. Frontend Can't Connect to Backend

**Error**: `Failed to fetch` or `CORS error`

**Solutions**:
- Ensure backend is running: `curl http://localhost:8000/docs`
- Check `API_BASE_URL` in `frontend/app.js` matches backend port
- If using different host/port, update CORS settings in `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    ...
)
```

---

### 6. Template Upload Fails

**Error**: `Template upload failed` or `Invalid template format`

**Solutions**:
- Ensure template file is `.docx`, `.html`, or `.pdf`
- Check file size (should be < 50MB)
- Verify template name doesn't contain special characters
- Check MinIO storage space: `docker exec dms-minio du -sh /data`

---

### 7. Document Generation Fails

**Error**: `Generation failed` or `Template rendering error`

**Solutions**:
- Check template syntax (Jinja2 format)
- Verify data file format (JSON/CSV)
- Check template placeholders match data keys
- Review error logs in `backend/templateFile/output/problems/`
- Ensure all required template variables are provided

---

### 8. Permission Denied Errors

**Error**: `您无权下载` or `您无权删除`

**Solutions**:
- Verify user role in database: `SELECT username, role FROM users;`
- Check if user/department is in document's blacklist
- Ensure you're logged in with correct account
- Clear browser cache and cookies, then re-login

---

### 9. Data Masking Not Working

**Issue**: Sensitive data not being masked

**Solutions**:
- Ensure "脱敏" (Data Masking) checkbox is checked in generation form
- Check if data fields match masking rules in `backend/src/security/data_masking.py`
- Verify data format (nested objects are supported)
- Check generation logs for masking errors

---

### 10. Watermark Not Appearing

**Issue**: Watermarks not visible in generated documents

**Solutions**:
- **Word**: Check if VML watermark is added (view document in Word, not preview)
- **PDF**: Ensure ReportLab is installed: `pip install reportlab PyPDF2`
- **HTML**: Check browser console for CSS errors
- Verify watermark image exists if using image watermark
- Check watermark settings in generation form

---

### 11. Categories Not Loading

**Error**: `加载失败:获取分类列表失败`

**Solutions**:
- Check `backend/categories.json` file exists and is valid JSON
- Verify file encoding is UTF-8
- Run: `python scripts/system_bootstrap.py` to reinitialize
- Check database connection
- Clear browser cache

---

### 12. Docker Containers Won't Start

**Error**: `Cannot connect to Docker daemon`

**Solutions**:
- Ensure Docker Desktop is running
- Check Docker service: `docker ps`
- Restart Docker Desktop
- Check disk space: `docker system df`
- Clean up unused resources: `docker system prune -a`

---

### 13. Import/Export Scripts Fail

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solutions**:
```bash
# Run from project root directory
cd backend
python scripts/system_bootstrap.py

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

---

### 14. WeasyPrint/PDF Generation Issues

**Error**: `ImportError: No module named 'weasyprint'` or PDF generation fails

**Solutions**:
- Install system dependencies (Linux):
```bash
sudo apt-get install python3-dev python3-pip python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```
- Install WeasyPrint: `pip install weasyprint`
- For Windows, use pre-built wheels or install GTK+ runtime

---

### 15. JWT Token Expired

**Error**: `401 Unauthorized` after some time

**Solutions**:
- Re-login to get new token
- Check token expiration in `backend/main.py`: `ACCESS_TOKEN_EXPIRE_HOURS`
- Clear browser localStorage and re-login
- Verify JWT secret key is consistent

---

## Getting Help

If you encounter issues not covered here:

1. Check the [Setup Guide](SETUP_GUIDE.md) for configuration steps
2. Review [Architecture Documentation](ARCHITECTURE.md) for system design
3. Check backend logs: `backend/templateFile/output/log/`
4. Check browser console for frontend errors
5. Verify all services are running: `docker ps`

