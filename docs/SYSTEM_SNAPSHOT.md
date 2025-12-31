# System Snapshot

## Database Summary (MySQL)

### Tables
- `users`: User accounts and roles.
- `documents`: Metadata for uploaded data files and general assets.
- `templates`: Jinja2 templates with version history.
- `generated_documents`: Generated Word/PDF/HTML results with metadata and access control.
- `access_logs`: System audit trail.

### Key Configuration
- **Admin Account**: `admin` / `admin` (IT Department)
- **Default Categories**: `未分类`, `images`, `基础测试`, `脱敏测试`.

## Storage Summary (MinIO)

### Buckets
- `documents`: Main storage for data files.
- `templates`: Storage for Jinja2 template files.
- `uncategorized`: Fallback for files without a specific category.
- `generated-word`: Generated Word documents.
- `generated-pdf`: Generated PDF documents.
- `generated-html`: Generated HTML documents.

## Sample Files (testdata)

### Input Files
- `test1.json`: Multi-field sample data.
- `test2.csv`: Numerical data for chart testing.
- `test3.json`: Complex nested data for table merge testing.
- `test4.json`: Sensitive PII data for masking testing.
- `test4.csv`: PII data in CSV format.

### Templates
- `test1`: Standard Word/HTML templates.
- `test2`: Templates with chart and table placeholders.
- `test3(json)`: Specialized Word template for nested JSON data.
- `test4`: Simplified templates focused on demonstrating data masking.

