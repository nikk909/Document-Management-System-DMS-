@echo off
echo 启动 FastAPI 后端服务...
echo.
cd /d %~dp0
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause

