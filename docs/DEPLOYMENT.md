# Deployment Guide

## Infrastructure (Docker)

The system relies on MySQL and MinIO. Use the provided `docker-compose.yaml` for a quick setup.

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

## Backend Configuration

Edit `backend/config/config.yaml` to match your infrastructure.

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

## Initial Setup

1. Run the database initialization script (if available) or start the backend to auto-create tables.
2. Ensure you have the `uncategorized` bucket created in MinIO.
3. Use the first created account or a default `admin/admin` account to set up roles.

