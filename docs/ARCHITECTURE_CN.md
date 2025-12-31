# 系统架构

## 概述

文档管理系统（DMS）采用经典客户端-服务器架构，清晰分离表示层、应用逻辑层和数据存储层。

## 前端架构

- **核心**: 原生 JavaScript (ES6+)、HTML5 和 CSS3。
- **UI 设计**: 使用 Flexbox 和 Grid 的现代响应式设计。自定义 CSS 变量以保持主题一致性。
- **状态管理**: 通过全局变量和 DOM 属性管理客户端状态。
- **API 交互**: 使用 `fetch` API 进行 RESTful API 调用。
- **功能特性**:
  - 动态标签页导航。
  - 文档生成的实时进度条。
  - 集成文件和模板预览器。
  - 权限管理的动态表单构建。

## 后端架构

- **框架**: FastAPI（异步 Python）。
- **ORM**: SQLAlchemy 2.0 用于关系数据映射。
- **认证**: JWT（JSON Web Tokens），采用 HTTP Bearer 方案。基于角色的访问控制（Admin/User）。
- **核心模块**:
  - `StorageManager`: MinIO 和 MySQL 同步的抽象接口。
  - `DocumentExporter`: 跨所有支持格式生成文档的统一入口点。
  - `DataMasker`: 基于规则和模式的 PII 脱敏引擎。
  - `AccessLogger`: 系统活动的同步和异步日志记录。
  - `TemplateManager`: 支持版本的模板检索和存储。

## 数据层

- **元数据（MySQL）**:
  - `users`: 用户凭据和角色。
  - `documents`: 原始数据文件和上传的资源。
  - `templates`: 带版本历史的 Jinja2 模板。
  - `generated_documents`: 生成输出的审计跟踪和元数据。
  - `access_logs`: 详细的活动日志。
- **存储（MinIO）**:
  - 文件根据分类组织到存储桶中（如 `images`、`templates`、`uncategorized`）。
  - 路径格式: `{category}/{year}/{month}/{day}/{filename}`。
  - 内置模板版本控制支持。

## 工作流程：文档生成

1. **上传/选择数据**: 用户提供 JSON 或 CSV 文件。
2. **选择模板**: 用户选择兼容的 Word 或 HTML 模板。
3. **配置**: 用户设置安全选项（水印、脱敏、加密）。
4. **处理**:
   - 后端通过 `DataProcessor` 解析数据。
   - 如果启用，`DataMasker` 会脱敏敏感字段。
   - `DocumentExporter` 使用 Jinja2 渲染模板。
   - 特定导出器（Word/PDF/HTML）应用最终格式和安全设置。
5. **存储**: 最终文档保存到 MinIO，元数据记录在 MySQL 中。
6. **交付**: 用户通过安全、权限检查的链接下载结果。

