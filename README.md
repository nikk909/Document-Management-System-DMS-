# Document Management System (DMS)

A comprehensive document management and generation system built with FastAPI, MinIO, and MySQL.

## Key Features

- **Document Generation**: Generate Word, PDF, and HTML documents from templates (Jinja2) using JSON/CSV data.
- **Template Management**: Multi-format template support (Word, HTML, PDF) with versioning and rollback.
- **Security & Compliance**:
  - **Data Masking**: Automatic detection and masking of PII (ID cards, phones, emails, bank cards).
  - **Watermarking**: Text and image watermarks for Word, PDF, and HTML.
  - **Encryption**: PDF password protection and Word editing restrictions.
  - **Access Control**: Blacklist-based download and delete permissions for users/departments.
- **File Management**: Categorized storage in MinIO with metadata in MySQL.
- **Audit Logging**: Comprehensive logging of all file access and system actions.

## Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: MySQL 5.7+ (Metadata storage)
- **Object Storage**: MinIO (File storage)
- **Document Processing**:
  - `python-docx`: Word document generation and protection.
  - `jinja2`: Template engine for HTML and Word.
  - `weasyprint`: HTML to PDF conversion.
  - `matplotlib`: Dynamic chart generation.
- **Frontend**: Vanilla JavaScript, CSS3, HTML5 (No complex frameworks for maximum compatibility).

### System Preview

#### 1. Template Management

![Template Management](image/program/template_management.png)

#### 2. Generated Documents List

![Generated Documents](image/program/generated_docs.png)

#### 3. MinIO Console

![MinIO Console](image/program/minio_console.png)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+

### Setup Infrastructure

```bash
# Start MySQL and MinIO using Docker
docker-compose up -d
```

### One-Click Initialization & Data Import

The system provides a bootstrap script to automatically create database tables, an admin account, and import sample data:

```bash
cd backend
# Ensure dependencies are installed
pip install -r requirements.txt
# Run the bootstrap script
python scripts/system_bootstrap.py
```

*Default admin account: `admin` / `admin`*

### Data Export (Creating Samples)

If you have modified templates or data in the system and want to save them to the `@testdata` folder as a new sample package:

```bash
cd backend
python scripts/export_data.py
```

### Start Backend

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Access Frontend

Open `frontend/index.html` in your browser.

## Documentation

### English

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Functionality Guide](docs/FUNCTIONALITY.md)
- [Template Format Specification](docs/模板格式说明.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [System Snapshot](docs/SYSTEM_SNAPSHOT.md)
- [Project Report](docs/REPORT_OVERVIEW.md)
- [Requirement Comparison](docs/REQUIREMENT_COMPARISON.md)

### 中文

- [系统架构](docs/ARCHITECTURE_CN.md)
- [功能指南](docs/FUNCTIONALITY_CN.md)
- [模板格式说明](docs/模板格式说明.md)
- [部署指南](docs/DEPLOYMENT_CN.md)
- [系统快照](docs/SYSTEM_SNAPSHOT_CN.md)
- [项目报告](docs/REPORT_OVERVIEW_CN.md)
- [需求对比](docs/REQUIREMENT_COMPARISON.md)
- [推荐模板说明](docs/推荐模板说明.md)

---

# 文件管理系统 (DMS)

基于 FastAPI、MinIO 和 MySQL 构建的全功能文档管理与生成系统。

## 核心功能

- **文档生成**：支持从 Word/HTML 模板使用 JSON/CSV 数据生成 Word、PDF 和 HTML 文档。
- **模板管理**：多格式模板支持，具备版本管理与一键回退功能。
- **安全与合规**：
  - **数据脱敏**：自动识别并脱敏敏感信息（身份证、手机号、邮箱、银行卡）。
  - **水印功能**：支持 Word、PDF、HTML 的文字和图片水印。
  - **加密保护**：支持 PDF 密码加密和 Word 限制编辑。
  - **权限控制**：基于黑名单的下载与删除权限管理。
- **文件管理**：MinIO 桶存储结合 MySQL 元数据管理，支持分类搜索。
- **审计日志**：完整记录所有文件访问和系统操作。

## 技术栈

- **后端**: FastAPI (Python 3.10+)
- **数据库**: MySQL 5.7+
- **对象存储**: MinIO
- **文档处理**:
  - `python-docx`: Word 生成与保护
  - `jinja2`: 模板引擎
  - `weasyprint`: HTML 转 PDF
  - `matplotlib`: 动态图表生成
- **前端**: 原生 JavaScript, CSS3, HTML5

## 快速开始

请参阅 [英文版 README](#document-management-system-dms) 了解详细步骤。
