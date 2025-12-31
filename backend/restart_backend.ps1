# 重启后端服务器的PowerShell脚本
# 停止所有Python进程（使用uvicorn运行的后端）
Write-Host "正在停止后端服务器..." -ForegroundColor Yellow

# 查找并停止运行在8000端口的进程
$processes = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($processes) {
    foreach ($processId in $processes) {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($proc -and $proc.Path -like "*python*") {
            Write-Host "停止进程: $processId ($($proc.ProcessName))" -ForegroundColor Yellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

# 等待进程完全停止
Start-Sleep -Seconds 2

# 重新启动后端
Write-Host "正在启动后端服务器..." -ForegroundColor Green
$backendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $backendDir "..\venv\Scripts\python.exe"
$mainFile = Join-Path $backendDir "main.py"

# 确保路径是绝对路径
$backendDir = (Resolve-Path $backendDir).Path
$venvPython = (Resolve-Path $venvPython -ErrorAction SilentlyContinue).Path

if (-not $venvPython) {
    # 如果相对路径解析失败，尝试绝对路径
    $projectRoot = Split-Path -Parent $backendDir
    $venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"
    $venvPython = (Resolve-Path $venvPython -ErrorAction SilentlyContinue).Path
}

if ($venvPython -and (Test-Path $venvPython)) {
    Write-Host "使用Python: $venvPython" -ForegroundColor Cyan
    Write-Host "工作目录: $backendDir" -ForegroundColor Cyan
    Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -WorkingDirectory $backendDir -WindowStyle Hidden
    Write-Host "后端服务器已启动" -ForegroundColor Green
} else {
    Write-Host "错误: 找不到虚拟环境Python: $venvPython" -ForegroundColor Red
    Write-Host "尝试的路径: $venvPython" -ForegroundColor Red
    exit 1
}

