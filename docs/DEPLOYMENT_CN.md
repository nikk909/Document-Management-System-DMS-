# 部署指南

## 基础设施（Docker）

系统依赖 MySQL 和 MinIO。使用提供的 `docker-compose.yaml` 进行快速设置。

### docker-compose.yaml
```yaml
version: '3.8'
services:
  mysql:
    image: mysql:5.7
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: file_management
    ports:
      - "3306:3306"
  minio:
    image: minio/minio
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
```

## 后端配置

编辑 `backend/config/config.yaml` 以匹配您的基础设施。

```yaml
mysql:
  host: localhost
  port: 3306
  user: root
  password: root
  database: file_management

minio:
  endpoint: localhost:9000
  access_key: minioadmin
  secret_key: minioadmin
  bucket: documents
  secure: false

auth:
  secret_key: "your-jwt-secret"
  algorithm: HS256
```

## 初始化设置

1. 运行数据库初始化脚本（如果可用）或启动后端以自动创建表。
2. 确保在 MinIO 中创建了 `uncategorized` 存储桶。
3. 使用第一个创建的账户或默认的 `admin/admin` 账户来设置角色。

## 依赖安装

```bash
cd backend
pip install -r requirements.txt
```

## 启动服务

### 后端服务
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端访问
直接在浏览器中打开 `frontend/index.html`。

