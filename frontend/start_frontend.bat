@echo off
chcp 65001 >nul
echo ========================================
echo 正在启动前端服务器...
echo ========================================
cd /d %~dp0
echo 当前目录: %CD%
set VENV_PYTHON=%~dp0..\..\final_work2\.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    set VENV_PYTHON=%~dp0..\..\.venv\Scripts\python.exe
)
if not exist "%VENV_PYTHON%" (
    echo 错误: 虚拟环境不存在！
    echo 请检查路径: %VENV_PYTHON%
    pause
    exit /b 1
)
echo 使用虚拟环境: %VENV_PYTHON%
echo 启动前端服务器在端口 8080...
echo 前端地址: http://localhost:8080
echo ========================================
"%VENV_PYTHON%" -m http.server 8080
pause

