# 后端服务文档

FastAPI 后端服务，提供文档生成、模板管理、存储管理等 API。

## 📁 目录结构

```
backend/
├── config/
│   └── config.yaml          # 统一配置文件（MySQL、MinIO等）
├── src/
│   ├── core/                # 核心模块
│   │   ├── exporter.py      # 文档导出器
│   │   ├── data_processor.py # 数据处理器
│   │   └── validator.py     # 格式校验器
│   ├── exporters/           # 导出器（Word/PDF/HTML）
│   ├── processors/          # 处理器（表格/图表/图片）
│   ├── storage/             # 存储模块
│   │   ├── database.py      # 数据库模型
│   │   ├── storage_manager.py # 存储管理器
│   │   └── minio_client.py  # MinIO 客户端
│   ├── security/            # 安全模块
│   │   ├── user_manager.py  # 用户管理
│   │   ├── permission.py    # 权限控制
│   │   ├── data_masking.py  # 数据脱敏
│   │   └── access_logger.py # 访问日志
│   └── utils/               # 工具模块
│       ├── encryption.py    # 文档加密
│       └── word_protection.py # Word 保护（限制编辑、水印）
├── scripts/
│   ├── create_database.py   # 创建数据库
│   └── init_storage_db.py   # 初始化数据库表
├── main.py                  # FastAPI 主程序
└── requirements.txt         # Python 依赖
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config/config.yaml`，配置 MySQL 和 MinIO：

```yaml
mysql:
  host: "127.0.0.1"
  port: 3307
  user: "root"
  password: "your_password"
  database: "your_database"

minio:
  endpoint: "localhost:9000"
  access_key: "minioadmin"
  secret_key: "minioadmin"
```

### 3. 初始化数据库

```bash
python scripts/create_database.py
python scripts/init_storage_db.py
```

### 4. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:8000` 启动。

## 📡 API 端点

### 认证
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出

### 文件管理
- `GET /api/files` - 获取文件列表
- `POST /api/files/upload` - 上传文件
- `GET /api/files/{file_id}/download` - 下载文件
- `PUT /api/files/{file_id}/rename` - 重命名文件
- `DELETE /api/files/{file_id}` - 删除文件
- `POST /api/files/{file_id}/archive` - 归档/取消归档

### 模板管理
- `GET /api/templates` - 获取模板列表
- `POST /api/templates/upload` - 上传模板
- `GET /api/templates/{template_id}/versions` - 获取版本历史
- `POST /api/templates/{template_id}/rollback` - 回滚模板版本
- `GET /api/templates/{template_id}/download` - 下载模板
- `DELETE /api/templates/{template_id}` - 删除模板

### 文档生成
- `POST /api/documents/generate` - 生成文档
- `GET /api/documents/generated` - 获取生成的文档列表
- `GET /api/documents/generated/{doc_id}/download` - 下载生成的文档

### 访问日志
- `GET /api/logs` - 获取访问日志

### 系统管理
- `DELETE /api/system/clear-all` - 一键清空所有数据（仅管理员）

## 🔧 配置说明

### 配置文件位置

所有配置集中在 `config/config.yaml`：

- **MySQL 配置**: `mysql` 节点
- **MinIO 配置**: `minio` 节点
- **路径配置**: `paths` 节点
- **导出配置**: `export` 节点
- **模板配置**: `template` 节点
- **校验配置**: `validation` 节点
- **存储配置**: `storage` 节点
- **日志配置**: `logging` 节点

### MinIO 桶结构

- `documents` - 普通文档
- `templates` - 模板文件
- `generated-documents` - 生成的文档（按格式分类：pdf/word/html）
- `logs` - 访问日志

## 🔐 用户和权限

### 默认用户

用户配置在 `src/security/users.yaml`：

- **admin** - 系统管理员（所有权限）
- **user** - 普通用户（受限权限）

### 权限说明

- **admin**: 所有操作权限
- **user**: 上传、下载、修改、删除、生成文档

## 📦 依赖说明

### 核心依赖
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `sqlalchemy` - ORM
- `pymysql` - MySQL 驱动
- `minio` - MinIO 客户端

### 文档处理
- `python-docx` - Word 文档处理
- `weasyprint` - PDF 生成（需要 GTK+ 运行时）
- `jinja2` - 模板渲染
- `PyPDF2` - PDF 处理

### 数据处理
- `pandas` - CSV 处理
- `matplotlib` - 图表生成
- `pillow` - 图片处理

## ⚠️ 注意事项

### WeasyPrint (PDF 生成)

在 Windows 上，WeasyPrint 需要 GTK+ 运行时库：

1. 下载 GTK3-Runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
2. 安装后，将 GTK+ bin 目录添加到系统 PATH
3. 或设置环境变量 `GTK_BIN_PATH`

### Word 限制编辑

由于 python-docx 的限制，真正的限制编辑需要使用：
- COM 对象（Windows）
- msoffcrypto-tool 库

当前实现通过 XML 操作添加文档保护标记。

### PDF 水印

需要安装：
```bash
pip install reportlab PyPDF2
```

## 🐛 故障排除

### 数据库连接失败

1. 检查 MySQL 服务是否运行
2. 检查 `config/config.yaml` 中的 MySQL 配置
3. 确认数据库已创建

### MinIO 连接失败

1. 检查 MinIO 服务是否运行
2. 检查 `config/config.yaml` 中的 MinIO 配置
3. 确认 MinIO 桶已创建

### PDF 生成失败

1. 检查 WeasyPrint 是否正确安装
2. 在 Windows 上，确认 GTK+ 运行时已安装
3. 检查控制台错误信息

## 📚 更多信息

- API 文档: http://localhost:8000/docs
- 项目主 README: [../README.md](../README.md)
