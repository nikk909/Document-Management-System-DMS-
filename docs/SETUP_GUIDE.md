# 快速设置指南

## 前置要求

- **Docker** 和 **Docker Compose**（用于运行 MySQL 和 MinIO）
- **Python 3.10+**
- **Git**（用于克隆仓库）

## 第一步：克隆仓库

```bash
git clone https://github.com/nikk909/Document-Management-System-DMS-.git
cd Document-Management-System-DMS-
```

## 第二步：启动基础设施（MySQL + MinIO）

使用 Docker Compose 一键启动：

```bash
docker-compose up -d
```

等待服务启动完成（约 30 秒），然后访问：
- **MinIO 控制台**: http://localhost:9001
  - 用户名: `minioadmin`
  - 密码: `minioadmin`

## 第三步：配置后端

### 1. 创建配置文件

```bash
cd backend
cp config/config.yaml.example config/config.yaml
```

### 2. 编辑配置文件

编辑 `backend/config/config.yaml`，修改以下关键配置：

```yaml
mysql:
  host: "127.0.0.1"
  port: 3306                    # 确保与 docker-compose.yaml 中的端口一致
  user: "root"
  password: "root"              # 修改为 docker-compose.yaml 中设置的密码
  database: "file_management"

minio:
  endpoint: "localhost:9000"
  access_key: "minioadmin"      # 修改为 docker-compose.yaml 中设置的值
  secret_key: "minioadmin"      # 修改为 docker-compose.yaml 中设置的值
```

### 2.1. 配置 JWT 密钥（可选，生产环境必须）

编辑 `backend/main.py`，修改 JWT 密钥（第 47 行）：

```python
SECRET_KEY = "your-secret-key-change-in-production"  # 改为强随机字符串
```

**⚠️ 生产环境警告**: 必须修改此密钥，否则存在安全风险！

### 3. 安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 第四步：初始化系统

运行一键初始化脚本：

```bash
python scripts/system_bootstrap.py
```

此脚本将：
- ✅ 自动创建所有数据库表
- ✅ 创建默认管理员账号（`admin` / `admin`）
- ✅ 导入示例数据和模板（从 `testdata` 文件夹）

## 第五步：启动后端服务

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 `http://localhost:8000` 启动。

## 第六步：访问前端

在浏览器中打开 `frontend/index.html`，或使用本地服务器：

```bash
# 使用 Python 内置服务器
cd frontend
python -m http.server 8080
```

然后访问 `http://localhost:8080`

## 默认账号

- **用户名**: `admin`
- **密码**: `admin`

**⚠️ 重要**: 首次登录后请立即修改密码！

## 常见问题

### 1. 数据库连接失败

- 检查 MySQL 容器是否正常运行：`docker ps`
- 检查 `config.yaml` 中的端口和密码是否与 `docker-compose.yaml` 一致
- 检查防火墙是否阻止了 3306 端口

### 2. MinIO 连接失败

- 检查 MinIO 容器是否正常运行：`docker ps`
- 访问 http://localhost:9001 确认 MinIO 控制台可访问
- 检查 `config.yaml` 中的 `access_key` 和 `secret_key` 是否正确

### 3. 端口被占用

如果 8000 端口被占用，可以修改启动命令：

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

然后修改 `frontend/app.js` 中的 `API_BASE_URL` 为 `http://localhost:8001`

### 4. 依赖安装失败

如果某些包安装失败，尝试：

```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 下一步

- 查看 [功能指南](FUNCTIONALITY.md) 了解系统功能
- 查看 [架构文档](ARCHITECTURE.md) 了解系统架构
- 查看 [模板格式说明](模板格式说明.md) 学习如何创建模板

