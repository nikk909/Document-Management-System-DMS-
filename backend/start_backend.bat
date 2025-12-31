@echo off
REM 批处理脚本：启动后端服务（自动杀死占用端口的进程）
REM 使用方法：双击运行或在命令行执行 start_backend.bat

echo ========================================
echo   启动 FastAPI 后端服务
echo ========================================
echo.

REM 获取脚本所在目录
cd /d %~dp0
set BACKEND_DIR=%~dp0
set PROJECT_ROOT=%~dp0..
set VENV_PATH=%PROJECT_ROOT%\venv
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe

REM 检查虚拟环境是否存在
if not exist "%VENV_PATH%" (
    echo [错误] 虚拟环境不存在: %VENV_PATH%
    echo 请先创建虚拟环境: python -m venv venv
    pause
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo [错误] 虚拟环境Python不存在: %PYTHON_EXE%
    echo 请先创建虚拟环境: python -m venv venv
    pause
    exit /b 1
)

set PORT=8000

echo [1/4] 检查端口 %PORT% 占用情况...

REM 查找占用端口的进程（使用netstat和findstr）
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    set PID=%%a
    goto :found
)

:found
if defined PID (
    echo [警告] 端口 %PORT% 已被进程占用: PID=%PID%
    
    REM 尝试获取进程信息
    for /f "tokens=1,2" %%a in ('tasklist /FI "PID eq %PID%" /FO CSV /NH 2^>nul') do (
        set PROC_NAME=%%a
        set PROC_NAME=!PROC_NAME:"=!
    )
    
    echo   进程名: %PROC_NAME%
    echo [操作] 终止进程 %PID%...
    
    REM 终止进程
    taskkill /F /PID %PID% >nul 2>&1
    
    REM 等待端口释放
    echo [2/4] 等待端口释放...
    timeout /t 2 /nobreak >nul
) else (
    echo [成功] 端口 %PORT% 未被占用
)

echo.
echo [3/4] 切换到后端目录...
cd /d %BACKEND_DIR%

echo [4/4] 启动后端服务...
echo   虚拟环境: %VENV_PATH%
echo   Python: %PYTHON_EXE%
echo   目录: %BACKEND_DIR%
echo   端口: %PORT%
echo.
echo ========================================
echo   服务启动中，按 Ctrl+C 停止服务
echo ========================================
echo.

REM 启动服务
"%PYTHON_EXE%" -m uvicorn main:app --reload --host 0.0.0.0 --port %PORT%

pause

