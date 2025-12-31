# 系统快照

## 数据库摘要（MySQL）

### 数据表
- `users`: 用户账户和角色。
- `documents`: 上传的数据文件和通用资源的元数据。
- `templates`: 带版本历史的 Jinja2 模板。
- `generated_documents`: 生成的 Word/PDF/HTML 结果及其元数据和访问控制。
- `access_logs`: 系统审计跟踪。

### 关键配置
- **管理员账户**: `admin` / `admin`（IT 部门）
- **默认分类**: `未分类`、`images`、`基础测试`、`脱敏测试`。

## 存储摘要（MinIO）

### 存储桶
- `documents`: 数据文件的主存储。
- `templates`: Jinja2 模板文件的存储。
- `uncategorized`: 没有特定分类的文件的备用存储。
- `generated-word`: 生成的 Word 文档。
- `generated-pdf`: 生成的 PDF 文档。
- `generated-html`: 生成的 HTML 文档。

## 示例文件（testdata）

### 输入文件
- `test1.json`: 多字段示例数据。
- `test2.csv`: 用于图表测试的数值数据。
- `test3.json`: 用于表格合并测试的复杂嵌套数据。
- `test4.json`: 用于脱敏测试的敏感 PII 数据。
- `test4.csv`: CSV 格式的 PII 数据。

### 模板
- `test1`: 标准 Word/HTML 模板。
- `test2`: 带图表和表格占位符的模板。
- `test3(json)`: 专门用于嵌套 JSON 数据的 Word 模板。
- `test4`: 专注于展示数据脱敏的简化模板。

## 系统状态

### 当前运行状态
- 后端服务: `http://localhost:8000`
- 数据库: MySQL（默认端口 3306）
- 对象存储: MinIO（API 端口 9000，控制台端口 9001）

### 已知限制
- 模板版本控制的前端 UI 尚未完成（后端已支持）。
- 大规模并发处理需要进一步优化。

