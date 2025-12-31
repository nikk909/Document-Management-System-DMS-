# 故障排除指南

## 常见问题及解决方案

### 1. 后端无法启动

**错误**: `ModuleNotFoundError` 或 `ImportError`

**解决方案**:
```bash
# 确保在虚拟环境中
cd backend
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装所有依赖
pip install -r requirements.txt
```

---

### 2. 数据库连接失败

**错误**: `OperationalError: (2003, "Can't connect to MySQL server")`

**解决方案**:
- 检查 MySQL 容器是否运行: `docker ps`
- 验证 `config.yaml` 中的 MySQL 端口是否与 `docker-compose.yaml` 一致（默认: 3306）
- 检查 `config.yaml` 中的 MySQL 账号密码
- 启动 Docker 容器后等待 30 秒，让 MySQL 完成初始化

**测试连接**:
```bash
docker exec -it dms-mysql mysql -uroot -proot -e "SHOW DATABASES;"
```

---

### 3. MinIO 连接失败

**错误**: `S3Error: Invalid endpoint`

**解决方案**:
- 检查 MinIO 容器是否运行: `docker ps`
- 访问 MinIO 控制台: http://localhost:9001
- 验证 `config.yaml` 中的 `endpoint`、`access_key` 和 `secret_key`
- 确认 MinIO 可访问: `curl http://localhost:9000/minio/health/live`

---

### 4. 端口被占用

**错误**: `Address already in use` 或 `Port 8000 is already in use`

**解决方案**:

**选项 1**: 杀掉占用端口的进程
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

**选项 2**: 更改后端端口
```bash
# 在不同端口启动后端
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

然后更新 `frontend/app.js`:
```javascript
const API_BASE_URL = 'http://localhost:8001';
```

---

### 5. 前端无法连接到后端

**错误**: `Failed to fetch` 或 `CORS error`

**解决方案**:
- 确保后端正在运行: `curl http://localhost:8000/docs`
- 检查 `frontend/app.js` 中的 `API_BASE_URL` 是否与后端端口匹配
- 如果使用不同的主机/端口，更新 `backend/main.py` 中的 CORS 设置:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请改为特定域名
    ...
)
```

---

### 6. 模板上传失败

**错误**: `Template upload failed` 或 `Invalid template format`

**解决方案**:
- 确保模板文件是 `.docx`、`.html` 或 `.pdf` 格式
- 检查文件大小（应 < 50MB）
- 验证模板名称不包含特殊字符
- 检查 MinIO 存储空间: `docker exec dms-minio du -sh /data`

---

### 7. 文档生成失败

**错误**: `Generation failed` 或 `Template rendering error`

**解决方案**:
- 检查模板语法（Jinja2 格式）
- 验证数据文件格式（JSON/CSV）
- 检查模板占位符是否与数据键匹配
- 查看错误日志: `backend/templateFile/output/problems/`
- 确保所有必需的模板变量都已提供

---

### 8. 权限拒绝错误

**错误**: `您无权下载` 或 `您无权删除`

**解决方案**:
- 验证数据库中的用户角色: `SELECT username, role FROM users;`
- 检查用户/部门是否在文档的黑名单中
- 确保使用正确的账号登录
- 清除浏览器缓存和 Cookie，然后重新登录

---

### 9. 数据脱敏不工作

**问题**: 敏感数据未被脱敏

**解决方案**:
- 确保生成表单中勾选了"脱敏"（Data Masking）复选框
- 检查数据字段是否匹配 `backend/src/security/data_masking.py` 中的脱敏规则
- 验证数据格式（支持嵌套对象）
- 检查生成日志中的脱敏错误

---

### 10. 水印不显示

**问题**: 生成的文档中看不到水印

**解决方案**:
- **Word**: 检查是否添加了 VML 水印（在 Word 中查看文档，而非预览）
- **PDF**: 确保已安装 ReportLab: `pip install reportlab PyPDF2`
- **HTML**: 检查浏览器控制台是否有 CSS 错误
- 如果使用图片水印，验证水印图片是否存在
- 检查生成表单中的水印设置

---

### 11. 分类无法加载

**错误**: `加载失败:获取分类列表失败`

**解决方案**:
- 检查 `backend/categories.json` 文件是否存在且为有效的 JSON
- 验证文件编码为 UTF-8
- 运行: `python scripts/system_bootstrap.py` 重新初始化
- 检查数据库连接
- 清除浏览器缓存

---

### 12. Docker 容器无法启动

**错误**: `Cannot connect to Docker daemon`

**解决方案**:
- 确保 Docker Desktop 正在运行
- 检查 Docker 服务: `docker ps`
- 重启 Docker Desktop
- 检查磁盘空间: `docker system df`
- 清理未使用的资源: `docker system prune -a`

---

### 13. 导入/导出脚本失败

**错误**: `ModuleNotFoundError: No module named 'src'`

**解决方案**:
```bash
# 从项目根目录运行
cd backend
python scripts/system_bootstrap.py

# 或添加到 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

---

### 14. WeasyPrint/PDF 生成问题

**错误**: `ImportError: No module named 'weasyprint'` 或 PDF 生成失败

**解决方案**:
- 安装系统依赖（Linux）:
```bash
sudo apt-get install python3-dev python3-pip python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```
- 安装 WeasyPrint: `pip install weasyprint`
- Windows 用户，使用预编译的 wheel 或安装 GTK+ 运行时

---

### 15. JWT Token 过期

**错误**: 一段时间后出现 `401 Unauthorized`

**解决方案**:
- 重新登录以获取新 token
- 检查 `backend/main.py` 中的 token 过期时间: `ACCESS_TOKEN_EXPIRE_HOURS`
- 清除浏览器 localStorage 并重新登录
- 验证 JWT 密钥是否一致

---

## 获取帮助

如果遇到本文档未涵盖的问题：

1. 查看 [快速设置指南](SETUP_GUIDE_CN.md) 了解配置步骤
2. 查看 [架构文档](ARCHITECTURE_CN.md) 了解系统设计
3. 检查后端日志: `backend/templateFile/output/log/`
4. 检查浏览器控制台的前端错误
5. 验证所有服务正在运行: `docker ps`

