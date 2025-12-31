# PowerShell脚本：启动后端服务（自动杀死占用端口的进程）
# 使用方法：在项目根目录执行 .\backend\start_backend.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  启动 FastAPI 后端服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = $scriptDir
$projectRoot = Split-Path -Parent $backendDir
$venvPath = Join-Path $projectRoot "venv"

# 检查虚拟环境是否存在
if (-not (Test-Path $venvPath)) {
    Write-Host "[错误] 虚拟环境不存在: $venvPath" -ForegroundColor Red
    Write-Host "请先创建虚拟环境: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# 虚拟环境Python路径
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[错误] 虚拟环境Python不存在: $pythonExe" -ForegroundColor Red
    Write-Host "请先创建虚拟环境: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# 端口号
$port = 8000

Write-Host "[1/4] 检查端口 $port 占用情况..." -ForegroundColor Yellow

# 查找占用端口的进程
$processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if ($processes) {
    Write-Host "[警告] 端口 $port 已被以下进程占用:" -ForegroundColor Yellow
    foreach ($pid in $processes) {
        try {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                $procName = $proc.ProcessName
                $procPath = $proc.Path
                Write-Host "  PID: $pid, 进程名: $procName" -ForegroundColor Yellow
                if ($procPath) {
                    Write-Host "  路径: $procPath" -ForegroundColor Gray
                }
                
                # 如果是Python进程，尝试终止
                if ($procName -like "*python*" -or $procPath -like "*python*") {
                    Write-Host "  [操作] 终止进程 $pid ($procName)..." -ForegroundColor Yellow
                    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                    Start-Sleep -Milliseconds 500
                }
            }
        } catch {
            Write-Host "  [警告] 无法获取进程 $pid 信息: $_" -ForegroundColor Yellow
        }
    }
    
    # 等待端口释放
    Write-Host "[2/4] 等待端口释放..." -ForegroundColor Yellow
    $maxWait = 10
    $waited = 0
    while ($waited -lt $maxWait) {
        $remaining = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if (-not $remaining) {
            Write-Host "[成功] 端口已释放" -ForegroundColor Green
            break
        }
        Start-Sleep -Seconds 1
        $waited++
        Write-Host "  等待中... ($waited/$maxWait)" -ForegroundColor Gray
    }
    
    if ($waited -eq $maxWait) {
        Write-Host "[错误] 端口 $port 仍被占用，请手动关闭相关进程" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[成功] 端口 $port 未被占用" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/4] 切换到后端目录..." -ForegroundColor Yellow
Set-Location $backendDir

Write-Host "[4/4] 启动后端服务..." -ForegroundColor Yellow
Write-Host "  虚拟环境: $venvPath" -ForegroundColor Gray
Write-Host "  Python: $pythonExe" -ForegroundColor Gray
Write-Host "  目录: $backendDir" -ForegroundColor Gray
Write-Host "  端口: $port" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  服务启动中，按 Ctrl+C 停止服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 启动服务
& $pythonExe -m uvicorn main:app --reload --host 0.0.0.0 --port $port

