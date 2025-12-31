#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FastAPI 后端服务 - 文件管理系统
完整实现所有前后端功能
"""

import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import bcrypt
import jwt

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session, load_only
from sqlalchemy import or_, and_, func

# 添加项目根目录到 Python 路径
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

from src.storage.database import DatabaseManager, User, DocumentMetadata, TemplateMetadata, get_db_session
from src.storage.storage_manager import StorageManager
from src.storage.metadata_manager import MetadataManager
from src.storage.template_metadata_manager import TemplateMetadataManager
from src.storage.utils import load_config, get_content_type
from src.security.access_logger import AccessLogger

app = FastAPI(title="文件管理系统 API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 配置
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# HTTP Bearer Token 认证
security = HTTPBearer()

# 全局存储管理器（延迟初始化）
_storage_manager: Optional[StorageManager] = None
_access_logger: Optional[AccessLogger] = None


def get_storage_manager() -> StorageManager:
    """获取存储管理器实例"""
    global _storage_manager
    if _storage_manager is None:
        config_path = backend_root / "config" / "config.yaml"
        _storage_manager = StorageManager(config_path=str(config_path))
    return _storage_manager


def get_access_logger() -> AccessLogger:
    """获取访问日志记录器"""
    global _access_logger
    if _access_logger is None:
        _access_logger = AccessLogger(session=None)
    return _access_logger


# ==================== 数据模型 ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[dict] = None


# ==================== 辅助函数 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_db():
    """获取数据库会话"""
    # 使用统一配置文件路径
    config_path = str(backend_root / "config" / "config.yaml")
    db = get_db_session(config_path=config_path)
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """从 token 获取当前用户"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ==================== 认证 API ====================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """登录接口"""
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "department": user.department},
        expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "message": "登录成功",
        "token": access_token,
        "user": {
            "username": user.username,
            "role": user.role,
            "department": user.department,
            "display_name": user.display_name or user.username
        }
    }


@app.post("/api/auth/logout")
async def logout():
    """登出接口"""
    return {"success": True, "message": "登出成功"}


@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {
        "username": current_user.username,
        "role": current_user.role,
        "department": current_user.department,
        "display_name": current_user.display_name or current_user.username
    }


# ==================== 文件管理 API ====================

@app.get("/api/files")
async def get_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    archive_status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件列表（支持筛选、搜索、分页）"""
    try:
        # 排除模板文件、生成的文档和图片（它们有单独的管理界面）
        # 使用 and_ 确保所有条件都满足
        query = db.query(DocumentMetadata).filter(
            DocumentMetadata.status == 'active'
        ).filter(
            DocumentMetadata.category != 'templates'
        ).filter(
            DocumentMetadata.category != 'generated_documents'
        ).filter(
            DocumentMetadata.category != 'images'  # 图片在图片管理中显示
        )
        
        # 关键词搜索（文件名、描述、分类、标签）
        if keyword:
            # 构建搜索条件：文件名、描述、分类
            search_conditions = [
                DocumentMetadata.filename.like(f"%{keyword}%"),
                DocumentMetadata.description.like(f"%{keyword}%"),
                DocumentMetadata.category.like(f"%{keyword}%")
            ]
            
            # 标签搜索（JSON字段）- 尝试在tags字段中搜索
            try:
                # 对于MySQL，使用JSON_SEARCH函数搜索tags字段
                # 如果tags是JSON格式，尝试搜索其中的值
                search_conditions.append(
                    func.json_search(DocumentMetadata.tags, 'one', f"%{keyword}%") != None
                )
            except:
                # 如果JSON搜索失败，尝试简单的LIKE搜索（适用于某些数据库）
                pass
            
            query = query.filter(or_(*search_conditions))
        
        # 日期筛选
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(DocumentMetadata.created_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                query = query.filter(DocumentMetadata.created_at <= date_to_obj)
            except ValueError:
                pass
        
        # 分类筛选（但不能选择 templates、generated_documents 或 images）
        if category:
            # 防止用户通过分类筛选查看 templates、generated_documents 或 images
            if category not in ['templates', 'generated_documents', 'images']:
                query = query.filter(DocumentMetadata.category == category)
            else:
                # 如果用户尝试选择这些分类，返回空结果
                query = query.filter(DocumentMetadata.id == -1)  # 永远不匹配的条件
        
        # 标签筛选
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            # JSON 字段查询（简化处理）
            for tag in tag_list:
                query = query.filter(
                    func.json_contains(DocumentMetadata.tags, f'"{tag}"')
                )
        
        # 归档状态筛选
        if archive_status == 'archived':
            query = query.filter(DocumentMetadata.is_archived == True)
        elif archive_status == 'active':
            query = query.filter(DocumentMetadata.is_archived == False)
        
        # 总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        docs = query.order_by(DocumentMetadata.created_at.desc()).offset(offset).limit(page_size).all()
        
        # 转换为响应格式
        files = []
        for doc in docs:
            doc_dict = doc.to_dict()
            # 提取标签列表
            tags_list = []
            if doc.tags:
                if isinstance(doc.tags, dict):
                    tags_list = list(doc.tags.values())
                elif isinstance(doc.tags, list):
                    tags_list = doc.tags
            
            files.append({
                "id": doc.id,
                "filename": doc.filename,
                "version": f"v{doc.id}",  # 简化版本号
                "upload_time": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "-",
                "category": doc.category or "-",
                "tags": tags_list,
                "uploader": doc.created_by or "系统",
                "is_archived": doc.is_archived,
                "minio_path": doc.minio_path,
                "file_size": doc.file_size,
                "description": doc.description
            })
        
        return {
            "files": files,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询文件列表失败: {str(e)}")


@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    encrypt: Optional[bool] = Form(False),
    restrict_edit: Optional[bool] = Form(False),
    watermark: Optional[bool] = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文件（存MinIO，元数据存MySQL）"""
    try:
        # 检查文件类型，如果是图片，拒绝上传（应该通过图片管理上传）
        if file.filename:
            file_ext = Path(file.filename).suffix.lower()
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
            if file_ext in image_extensions:
                raise HTTPException(
                    status_code=400, 
                    detail="图片文件请通过'图片管理'页面上传，不要在文件管理中上传图片"
                )
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 确定分类（默认为未分类，但不能是images、templates、generated_documents）
        file_category = category.strip() if category and category.strip() else "未分类"
        excluded_categories = ['images', 'templates', 'generated_documents']
        if file_category in excluded_categories:
            raise HTTPException(
                status_code=400,
                detail=f"不能使用保留的分类名称: {file_category}"
            )
        
        # 标签和描述不再使用，保留空字典以保持兼容
        tags_dict = {}
        
        # 获取内容类型
        content_type = get_content_type(file.filename)
        
        # 上传到MinIO
        storage = get_storage_manager()
        metadata = {
            "author": current_user.username,
            "department": current_user.department,
            "user_role": current_user.role,
            "description": "",
            "encrypt": str(encrypt),
            "restrict_edit": str(restrict_edit),
            "watermark": str(watermark)
        }
        
        result = storage.upload_bytes(
            data=file_content,
            filename=file.filename,
            category=file_category,
            content_type=content_type,
            metadata=metadata,
            tags=tags_dict
        )
        
        # 从统一配置文件获取数据库信息
        config = load_config(str(backend_root / "config" / "config.yaml"))
        mysql_db = config.get('mysql', {}).get('database', 'unknown')
        
        return {
            "success": True,
            "message": "上传成功",
            "filename": file.filename,
            "minio_bucket": storage.bucket,
            "minio_path": result['path'],
            "mysql_id": result.get('doc_id'),
            "mysql_info": {
                "table": "documents",
                "database": mysql_db,
                "record_id": result.get('doc_id')
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.get("/api/files/{file_id}")
async def get_file_detail(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件详情"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    doc_dict = doc.to_dict()
    tags_list = []
    if doc.tags:
        if isinstance(doc.tags, dict):
            tags_list = list(doc.tags.values())
        elif isinstance(doc.tags, list):
            tags_list = doc.tags
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "version": f"v{doc.id}",
        "category": doc.category,
        "tags": tags_list,
        "uploader": doc.created_by or "系统",
        "upload_time": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "-",
        "is_archived": doc.is_archived,
        "minio_path": doc.minio_path,
        "file_size": doc.file_size,
        "description": doc.description,
        "db_id": doc.id
    }


@app.get("/api/files/{file_id}/preview")
async def preview_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """预览文件（在线查看，不下载）"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        storage = get_storage_manager()
        file_data = storage.download_bytes(
            path=doc.minio_path,
            bucket=doc.bucket,  # 使用文档存储的bucket
            version_id=doc.version_id,
            user=current_user.username,
            user_role=current_user.role,
            user_department=current_user.department
        )
        
        # 记录预览日志
        access_logger = get_access_logger()
        access_logger.log(
            action='preview',
            object_path=doc.minio_path,
            user=current_user.username,
            bucket=doc.bucket,
            user_role=current_user.role,
            user_department=current_user.department,
            details={'filename': doc.filename, 'file_id': file_id}
        )
        
        # 预览模式：使用 inline 而不是 attachment
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=doc.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'inline; filename="{doc.filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


@app.get("/api/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载文件"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        storage = get_storage_manager()
        
        # 从MinIO中实际查找文件：尝试所有可能的bucket
        bucket = None
        path = doc.minio_path
        
        if not path:
            raise HTTPException(status_code=404, detail="文件路径不存在")
        
        # 可能的bucket列表（按优先级）
        possible_buckets = []
        
        # 1. 数据库中的bucket（如果存在）
        if doc.bucket:
            possible_buckets.append(doc.bucket)
        
        # 2. 根据路径前缀推断
        if path:
            path_parts = path.split('/')
            if path_parts:
                category = path_parts[0]
                inferred_bucket = storage._get_bucket_for_category(category)
                if inferred_bucket and inferred_bucket not in possible_buckets:
                    possible_buckets.append(inferred_bucket)
        
        # 3. 根据分类推断
        if doc.category:
            category_bucket = storage._get_bucket_for_category(doc.category)
            if category_bucket and category_bucket not in possible_buckets:
                possible_buckets.append(category_bucket)
        
        # 4. 所有已知的bucket
        all_buckets = list(storage.buckets.values())
        for b in all_buckets:
            if b not in possible_buckets:
                possible_buckets.append(b)
        
        # 在MinIO中查找文件
        found_bucket = None
        from minio.error import S3Error
        
        for test_bucket in possible_buckets:
            try:
                # 尝试检查文件是否存在
                storage.client.stat_object(test_bucket, path)
                found_bucket = test_bucket
                print(f"[下载] 在MinIO中找到文件: bucket={found_bucket}, path={path}")
                break
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    # 文件不存在，继续尝试下一个bucket
                    continue
                else:
                    # 其他错误，记录但不中断
                    print(f"[下载] 检查bucket {test_bucket} 时出错: {e}")
                    continue
            except Exception as e:
                # 其他异常，继续尝试
                print(f"[下载] 检查bucket {test_bucket} 时出错: {e}")
                continue
        
        if not found_bucket:
            # 如果所有bucket都没找到，返回详细错误信息
            error_detail = f"文件在MinIO中不存在。已检查的bucket: {possible_buckets}, 路径: {path}"
            print(f"[下载错误] {error_detail}")
            raise HTTPException(status_code=404, detail=error_detail)
        
        # 使用找到的bucket下载文件
        # 注意：不使用version_id，因为可能与实际版本不匹配
        # 如果需要版本控制，应该从MinIO获取最新版本信息
        try:
            file_data = storage.download_bytes(
                path=path,
                bucket=found_bucket,
                version_id=None,  # 不使用version_id，直接下载最新版本
                user=current_user.username,
                user_role=current_user.role,
                user_department=current_user.department
            )
        except Exception as download_error:
            print(f"[下载] 下载失败: {download_error}")
            raise HTTPException(status_code=500, detail=f"下载失败: {str(download_error)}")
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=doc.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{doc.filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[下载错误] {error_msg}")
        raise HTTPException(status_code=500, detail=f"下载失败: {error_msg}")


@app.get("/api/files/{file_id}/history")
async def get_file_history(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件历史版本"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 简化版本：返回当前文档信息
    # 实际应该查询MinIO的版本历史
    return {
        "file_id": file_id,
        "versions": [
            {
                "version": f"v{doc.id}",
                "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "-",
                "change_log": "当前版本",
                "version_id": doc.version_id
            }
        ]
    }


@app.post("/api/files/{file_id}/rollback")
async def rollback_file(
    file_id: int,
    version_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """回滚文件版本"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    try:
        storage = get_storage_manager()
        # 使用存储管理器的回滚功能
        result = storage.rollback(doc.minio_path, version_id)
        return {
            "success": True,
            "message": f"已回滚到版本 {version_id}",
            "file_id": file_id,
            "version": version_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


@app.post("/api/files/{file_id}/rename")
async def rename_file(
    file_id: int,
    new_filename: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重命名文件"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查权限：只能重命名自己创建的文件，或管理员可以重命名所有文件
    if current_user.role != 'admin' and doc.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="无权限重命名此文件")
    
    # 检查是否已归档
    if doc.is_archived:
        raise HTTPException(status_code=400, detail="已归档的文件不能重命名")
    
    # 验证新文件名
    if not new_filename or not new_filename.strip():
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    new_filename = new_filename.strip()
    
    # 保留原文件扩展名（如果新文件名没有扩展名）
    old_filename = doc.filename
    old_ext = Path(old_filename).suffix
    if not Path(new_filename).suffix and old_ext:
        new_filename = new_filename + old_ext
    
    try:
        old_filename = doc.filename
        doc.filename = new_filename
        db.commit()
        
        # 记录重命名日志
        access_logger = get_access_logger()
        access_logger.log(
            action='rename',
            object_path=doc.minio_path,
            user=current_user.username,
            bucket=doc.bucket,
            user_role=current_user.role,
            user_department=current_user.department,
            details={
                'file_id': file_id,
                'old_filename': old_filename,
                'new_filename': new_filename
            }
        )
        
        return {
            "success": True,
            "message": f"文件已重命名：{old_filename} → {new_filename}",
            "file_id": file_id,
            "old_filename": old_filename,
            "new_filename": new_filename
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")


@app.post("/api/files/{file_id}/edit")
async def edit_file(
    file_id: int,
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """编辑文件元数据"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查权限：只能编辑自己创建的文件，或管理员可以编辑所有文件
    if current_user.role != 'admin' and doc.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="无权限编辑此文件")
    
    # 检查是否已归档
    if doc.is_archived:
        raise HTTPException(status_code=400, detail="已归档的文件不能编辑")
    
    try:
        old_category = doc.category
        old_path = doc.minio_path
        old_bucket = doc.bucket
        
        # 更新分类（如果分类改变，需要更新MinIO路径）
        if category is not None and category != old_category:
            new_category = category
            doc.category = new_category
            
            # 如果MinIO路径存在且分类改变了，需要移动MinIO文件
            if old_path and old_category:
                try:
                    storage = get_storage_manager()
                    
                    # 构建新的MinIO路径（保持日期部分不变，只改变分类部分）
                    if old_path.startswith(f"{old_category}/"):
                        # 提取日期和文件名部分
                        path_parts = old_path.split('/', 1)
                        if len(path_parts) > 1:
                            date_and_filename = path_parts[1]  # 例如: "2025/12/30/filename.csv"
                            new_path = f"{new_category}/{date_and_filename}"
                            
                            # 在MinIO中移动文件
                            source_bucket = old_bucket or storage.bucket
                            dest_bucket = storage._get_bucket_for_category(new_category)
                            
                            # 使用MinIO客户端移动文件
                            from minio.commonconfig import CopySource
                            try:
                                # 复制文件到新路径
                                copy_source = CopySource(
                                    bucket_name=source_bucket,
                                    object_name=old_path
                                )
                                # storage.client 是 Minio 客户端
                                storage.client.copy_object(
                                    bucket_name=dest_bucket,
                                    object_name=new_path,
                                    source=copy_source
                                )
                                
                                # 复制成功后删除旧文件
                                try:
                                    storage.client.remove_object(source_bucket, old_path)
                                except Exception as e:
                                    print(f"删除旧文件失败 {old_path}: {e}")
                                
                                # 更新数据库中的路径和bucket
                                doc.minio_path = new_path
                                doc.bucket = dest_bucket
                            except Exception as e:
                                print(f"移动MinIO文件失败 {old_path} -> {new_path}: {e}")
                                # 即使MinIO移动失败，也更新数据库分类
                except Exception as e:
                    print(f"更新MinIO路径失败: {e}")
                    # 即使MinIO更新失败，也继续更新数据库分类
        
        # 更新标签
        if tags is not None:
            tag_list = [t.strip() for t in tags.split(',')]
            tags_dict = {}
            for i, tag in enumerate(tag_list):
                if tag:
                    tags_dict[f"tag_{i}"] = tag
            doc.tags = tags_dict
        
        # 更新描述
        if description is not None:
            doc.description = description
        
        db.commit()
        
        # 记录编辑日志
        access_logger = get_access_logger()
        access_logger.log(
            action='edit',
            object_path=doc.minio_path,
            user=current_user.username,
            bucket=doc.bucket,
            user_role=current_user.role,
            user_department=current_user.department,
            details={'filename': doc.filename, 'file_id': file_id}
        )
        
        return {
            "success": True,
            "message": "文件信息已更新",
            "file_id": file_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"编辑失败: {str(e)}")


@app.post("/api/files/{file_id}/archive")
async def archive_file(
    file_id: int,
    archive: str = Form("true"),  # 接收字符串，然后转换
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """归档/取消归档文件"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 将字符串转换为布尔值
    archive_bool = archive.lower() in ('true', '1', 'yes', 'on')
    
    doc.is_archived = archive_bool
    doc.is_readonly = archive_bool  # 归档后设为只读
    db.commit()
    
    # 记录归档日志
    access_logger = get_access_logger()
    access_logger.log(
        action='archive' if archive_bool else 'unarchive',
        object_path=doc.minio_path,
        user=current_user.username,
        bucket=doc.bucket,
        user_role=current_user.role,
        user_department=current_user.department,
        details={'filename': doc.filename, 'file_id': file_id, 'archived': archive_bool}
    )
    
    return {
        "success": True,
        "message": f"文件已{'归档' if archive_bool else '取消归档'}",
        "file_id": file_id,
        "is_archived": archive_bool
    }


@app.get("/api/categories")
async def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文件分类列表（使用简单的数组存储）"""
    try:
        from src.storage.categories import get_categories, sync_from_database, add_category
        
        # 从简单存储获取分类
        category_list = get_categories()
        
        # 确保"未分类"始终在列表中
        if '未分类' not in category_list:
            add_category('未分类')
            category_list = get_categories()
        
        # 同时从数据库同步（合并文件和模板中的分类）
        try:
            # 从文件表获取分类（只查询category列，避免file_tags问题）
            from sqlalchemy import text
            file_result = db.execute(text("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL AND category != ''"))
            file_category_list = [row[0] for row in file_result if row[0]]
            
            # 从模板表获取分类
            template_result = db.execute(text("SELECT DISTINCT category FROM templates WHERE category IS NOT NULL AND category != ''"))
            template_category_list = [row[0] for row in template_result if row[0]]
            
            # 合并所有分类
            all_db_categories = list(set(file_category_list + template_category_list))
            
            if all_db_categories:
                sync_from_database(all_db_categories)
            category_list = get_categories()  # 重新获取合并后的列表
            # 再次确保"未分类"在列表中
            if '未分类' not in category_list:
                add_category('未分类')
                category_list = get_categories()
        except Exception as e:
            print(f"从数据库同步分类失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 确保"未分类"在返回列表的最前面
        if '未分类' in category_list:
            category_list.remove('未分类')
            category_list.insert(0, '未分类')
        
        return {"categories": category_list}
    except Exception as e:
        print(f"获取分类列表失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@app.post("/api/categories")
async def create_category(
    category: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的文件分类（使用简单的数组存储）"""
    from src.storage.categories import add_category
    
    # 验证分类名称
    if not category or not category.strip():
        raise HTTPException(status_code=400, detail="分类名称不能为空")
    
    category = category.strip()
    
    # 使用简单存储添加分类
    if add_category(category):
        return {"message": "分类创建成功", "category": category}
    else:
        raise HTTPException(status_code=400, detail="分类创建失败，可能是保留的分类名称")


@app.put("/api/categories/{old_category}")
async def update_category(
    old_category: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新分类名称（使用简单的数组存储）"""
    from src.storage.categories import update_category
    from urllib.parse import unquote
    
    # 解码URL编码的分类名称
    old_category = unquote(old_category)
    
    # 获取请求体中的新分类名称
    body = await request.json()
    new_category = body.get('category') if isinstance(body, dict) else body
    if isinstance(new_category, str):
        new_category = new_category.strip()
    else:
        raise HTTPException(status_code=400, detail="新分类名称格式错误")
    
    # 验证新分类名称
    if not new_category:
        raise HTTPException(status_code=400, detail="新分类名称不能为空")
    
    # 更新分类
    if update_category(old_category, new_category):
        # 获取所有使用该分类的文件
        files_to_update = db.query(DocumentMetadata).filter(
            DocumentMetadata.category == old_category
        ).all()
        
        # 更新数据库中的分类和MinIO中的文件路径
        storage = get_storage_manager()
        moved_count = 0
        failed_count = 0
        
        for doc in files_to_update:
            try:
                # 构建新的MinIO路径（保持日期部分不变，只改变分类部分）
                old_path = doc.minio_path
                if old_path and old_path.startswith(f"{old_category}/"):
                    # 提取日期和文件名部分
                    path_parts = old_path.split('/', 1)
                    if len(path_parts) > 1:
                        date_and_filename = path_parts[1]  # 例如: "2025/12/30/filename.csv"
                        new_path = f"{new_category}/{date_and_filename}"
                        
                        # 在MinIO中移动文件
                        source_bucket = doc.bucket or storage.bucket
                        dest_bucket = storage._get_bucket_for_category(new_category)
                        
                        # 使用MinIO客户端移动文件
                        from minio.commonconfig import CopySource
                        try:
                            # 复制文件到新路径
                            copy_source = CopySource(
                                bucket_name=source_bucket,
                                object_name=old_path
                            )
                            # storage.client 是 Minio 客户端
                            storage.client.copy_object(
                                bucket_name=dest_bucket,
                                object_name=new_path,
                                source=copy_source
                            )
                            
                            # 复制成功后删除旧文件
                            try:
                                storage.client.remove_object(source_bucket, old_path)
                            except Exception as e:
                                print(f"删除旧文件失败 {old_path}: {e}")
                            
                            # 更新数据库中的路径和分类
                            doc.minio_path = new_path
                            doc.category = new_category
                            doc.bucket = dest_bucket
                            moved_count += 1
                        except Exception as e:
                            print(f"移动文件失败 {old_path} -> {new_path}: {e}")
                            failed_count += 1
                            # 即使MinIO移动失败，也更新数据库分类
                            doc.category = new_category
                    else:
                        # 路径格式不正确，只更新分类
                        doc.category = new_category
                        moved_count += 1
                else:
                    # 没有MinIO路径或路径格式不匹配，只更新分类
                    doc.category = new_category
                    moved_count += 1
                    
            except Exception as e:
                print(f"更新文件 {doc.id} 失败: {e}")
                failed_count += 1
                # 即使MinIO移动失败，也更新数据库分类
                doc.category = new_category
        
        # 提交数据库更改
        try:
            db.commit()
            message = f"分类更新成功"
            if moved_count > 0:
                message += f"，已更新 {moved_count} 个文件的分类"
            if failed_count > 0:
                message += f"，{failed_count} 个文件更新失败"
            return {
                "message": message,
                "old_category": old_category,
                "new_category": new_category,
                "moved_count": moved_count,
                "failed_count": failed_count
            }
        except Exception as e:
            db.rollback()
            print(f"更新数据库分类失败: {e}")
            raise HTTPException(status_code=500, detail=f"更新数据库失败: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="分类更新失败")


@app.delete("/api/categories/{category}")
async def delete_category(
    category: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除分类（使用简单的数组存储）"""
    from src.storage.categories import remove_category
    from urllib.parse import unquote
    
    # 解码URL编码的分类名称
    category = unquote(category)
    
    # 不允许删除"未分类"分类
    if category == '未分类':
        raise HTTPException(status_code=400, detail="不能删除默认分类'未分类'")
    
    # 删除分类
    if remove_category(category):
        # 将使用该分类的文件改为"未分类"（不删除文件）
        try:
            # 更新documents表
            db.query(DocumentMetadata).filter(
                DocumentMetadata.category == category
            ).update({DocumentMetadata.category: '未分类'})
            
            # 更新templates表
            from src.storage.database import TemplateMetadata
            db.query(TemplateMetadata).filter(
                TemplateMetadata.category == category
            ).update({TemplateMetadata.category: '未分类'})
            
            db.commit()
        except Exception as e:
            print(f"更新分类失败: {e}")
            import traceback
            traceback.print_exc()
        
        return {"message": "分类删除成功，相关文件已移至'未分类'", "category": category}
    else:
        raise HTTPException(status_code=404, detail="分类不存在")


@app.get("/api/templates/types")
async def get_template_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模板类型层级结构（基于分类）"""
    try:
        from src.storage.database import TemplateMetadata
        
        # 从数据库获取所有模板分类（使用category代替template_type）
        templates = db.query(TemplateMetadata.category).filter(
            TemplateMetadata.category.isnot(None),
            TemplateMetadata.category != ''
        ).distinct().all()
        
        # 构建层级结构（简化为单层分类）
        categories = []
        for (category,) in templates:
            if category and category not in categories:
                categories.append(category)
        
        # 返回分类列表（不再使用层级结构，因为template_type字段已移除）
        return {"types": categories, "categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板类型失败: {str(e)}")


@app.post("/api/templates/types")
async def create_template_type(
    request: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的模板类型"""
    try:
        level = request.get('level')
        name = request.get('name', '').strip()
        parent_level1 = request.get('parent_level1')
        parent_level2 = request.get('parent_level2')
        
        if not name:
            raise HTTPException(status_code=400, detail="类型名称不能为空")
        
        if level == 1:
            # 一级类型直接创建（实际上是通过上传模板自动创建）
            return {"message": "一级类型将在上传模板时自动创建", "name": name}
        elif level == 2:
            if not parent_level1:
                raise HTTPException(status_code=400, detail="二级类型需要指定一级类型")
            # 二级类型也是通过上传模板自动创建
            return {"message": "二级类型将在上传模板时自动创建", "name": name, "parent": parent_level1}
        elif level == 3:
            if not parent_level1 or not parent_level2:
                raise HTTPException(status_code=400, detail="三级类型需要指定一级和二级类型")
            # 三级类型也是通过上传模板自动创建
            return {"message": "三级类型将在上传模板时自动创建", "name": name, "parent": f"{parent_level1}-{parent_level2}"}
        else:
            raise HTTPException(status_code=400, detail="无效的层级")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建模板类型失败: {str(e)}")


@app.get("/api/files/tags")
async def get_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取标签列表"""
    # 从所有文档的tags字段中提取唯一标签
    docs = db.query(DocumentMetadata.tags).filter(DocumentMetadata.tags.isnot(None)).all()
    tag_set = set()
    for doc in docs:
        if doc[0]:
            if isinstance(doc[0], dict):
                tag_set.update(doc[0].values())
            elif isinstance(doc[0], list):
                tag_set.update(doc[0])
    
    tag_list = list(tag_set)
    if not tag_list:
        tag_list = ["重要", "月度", "合同", "测试", "进度", "报表"]
    return {"tags": tag_list}


@app.delete("/api/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文件（删除MySQL记录和MinIO文件）"""
    doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == file_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 检查权限：只能删除自己创建的文件，或管理员可以删除所有文件
    if current_user.role != 'admin' and doc.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="无权限删除此文件")
    
    try:
        storage = get_storage_manager()
        access_logger = get_access_logger()
        
        # 1. 删除MinIO中的文件（使用文档的bucket）
        deleted_minio = False
        if doc.minio_path:
            try:
                storage.client.remove_object(doc.bucket, doc.minio_path)  # 使用文档存储的bucket
                deleted_minio = True
            except Exception as e:
                print(f"删除MinIO文件失败 {doc.minio_path}: {e}")
        
        # 2. 删除MySQL记录
        db.delete(doc)
        db.commit()
        
        # 3. 记录访问日志
        try:
            access_logger.log(
                action='delete',
                object_path=doc.minio_path,
                user=current_user.username,
                bucket=doc.bucket,
                user_role=current_user.role,
                user_department=current_user.department,
                details={
                    'filename': doc.filename,
                    'file_id': file_id,
                    'deleted_minio': deleted_minio
                }
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return {
            "success": True,
            "message": f"文件已删除（MySQL记录已删除，MinIO文件{'已删除' if deleted_minio else '删除失败'}）",
            "file_id": file_id,
            "deleted_minio": deleted_minio
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@app.delete("/api/files/clear-all")
async def clear_all_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清空所有文件（删除MySQL记录和MinIO文件）- 仅管理员"""
    # 权限检查：只有admin可以清空所有文件
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限执行此操作，仅管理员可清空所有文件")
    
    try:
        storage = get_storage_manager()
        access_logger = get_access_logger()
        
        # 1. 获取所有文件记录
        all_docs = db.query(DocumentMetadata).filter(DocumentMetadata.status == 'active').all()
        total_count = len(all_docs)
        
        deleted_mysql = 0
        deleted_minio = 0
        
        # 2. 删除MinIO中的文件（使用每个文档的bucket）
        for doc in all_docs:
            try:
                if doc.minio_path:
                    storage.client.remove_object(doc.bucket, doc.minio_path)  # 使用文档存储的bucket
                    deleted_minio += 1
            except Exception as e:
                print(f"删除MinIO文件失败 {doc.minio_path}: {e}")
        
        # 3. 删除MySQL中的所有记录
        deleted_mysql = db.query(DocumentMetadata).filter(DocumentMetadata.status == 'active').delete()
        db.commit()
        
        # 4. 记录访问日志
        try:
            access_logger.log(
                action='clear_all',
                object_path='all',
                user=current_user.username,
                bucket=storage.bucket,
                user_role=current_user.role,
                user_department=current_user.department,
                details={
                    'total_files': total_count,
                    'deleted_mysql': deleted_mysql,
                    'deleted_minio': deleted_minio
                }
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return {
            "success": True,
            "message": f"清空完成：已删除 {deleted_mysql} 条MySQL记录，{deleted_minio} 个MinIO文件",
            "deleted_mysql": deleted_mysql,
            "deleted_minio": deleted_minio,
            "total": total_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清空文件失败: {str(e)}")


@app.get("/api/documents/generated")
async def get_generated_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    template_name: Optional[str] = None,
    format_type: Optional[str] = None,
    category: Optional[str] = None,  # 新增分类参数
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取生成的文档列表（使用新的 generated_documents 表）"""
    try:
        from src.storage.database import GeneratedDocumentMetadata
        from src.storage.metadata_manager import GeneratedDocumentMetadataManager
        
        # 使用新的 GeneratedDocumentMetadataManager
        with GeneratedDocumentMetadataManager(session=db) as mgr:
            # 构建查询条件
            date_from_obj = None
            date_to_obj = None
            
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                except ValueError:
                    pass
            
            if date_to:
                try:
                    # 将结束日期设为当天的 23:59:59
                    date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                except ValueError:
                    pass
            
            # 搜索生成的文档
            docs = mgr.search_generated_documents(
                format_type=format_type,
                template_name=template_name,
                status='active',
                keyword=keyword,
                date_from=date_from_obj,
                date_to=date_to_obj,
                category=category
            )
            
            # 总数
            total = len(docs)
            
            # 分页
            offset = (page - 1) * page_size
            docs = docs[offset:offset + page_size]
            
            # 转换为响应格式
            documents = []
            for doc in docs:
                tags_list = []
                if doc.tags:
                    if isinstance(doc.tags, dict):
                        tags_list = list(doc.tags.values())
                    elif isinstance(doc.tags, list):
                        tags_list = doc.tags
                
                # 处理权限信息
                blocked_users = doc.blocked_users if doc.blocked_users else []
                blocked_departments = doc.blocked_departments if doc.blocked_departments else []
                
                if isinstance(blocked_users, str):
                    import json
                    try:
                        blocked_users = json.loads(blocked_users)
                    except:
                        blocked_users = []
                if isinstance(blocked_departments, str):
                    import json
                    try:
                        blocked_departments = json.loads(blocked_departments)
                    except:
                        blocked_departments = []
                
                if not isinstance(blocked_users, list):
                    blocked_users = []
                if not isinstance(blocked_departments, list):
                    blocked_departments = []
                
                documents.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "version": f"v{doc.id}",
                    "generated_time": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "-",
                    "template_name": doc.template_name or "未知模板",
                    "template_id": doc.template_id,
                    "format_type": doc.format_type,
                    "tags": tags_list,
                    "generator": doc.created_by or doc.author or "系统",
                    "minio_path": doc.minio_path,
                    "file_size": doc.file_size,
                    "description": doc.description,
                    "category": doc.category or "未分类",
                    "is_masked": doc.is_masked or False,
                    "blocked_users": blocked_users,
                    "blocked_departments": blocked_departments
                })
            
            return {
                "documents": documents,
                "total": total,
                "page": page,
                "page_size": page_size
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"查询生成的文档列表失败: {str(e)}")


@app.get("/api/documents/generated/{doc_id}")
async def get_generated_document_detail(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取生成的文档详情"""
    try:
        from src.storage.database import GeneratedDocumentMetadata
        
        doc = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="生成的文档不存在")
        
        tags_list = []
        if doc.tags:
            if isinstance(doc.tags, dict):
                tags_list = list(doc.tags.values())
            elif isinstance(doc.tags, list):
                tags_list = doc.tags
        
        return {
            "id": doc.id,
            "filename": doc.filename,
            "version": f"v{doc.id}",
            "generated_time": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "-",
            "template_name": doc.template_name or "未知模板",
            "template_id": doc.template_id,
            "format_type": doc.format_type,
            "tags": tags_list,
            "generator": doc.created_by or doc.author or "系统",
            "minio_path": doc.minio_path,
            "bucket": doc.bucket,
            "file_size": doc.file_size,
            "description": doc.description,
            "is_archived": doc.is_archived
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取生成的文档详情失败: {str(e)}")


@app.get("/api/documents/generated/{doc_id}/preview")
async def preview_generated_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """预览生成的文档（在线查看，不下载）"""
    try:
        from src.storage.database import GeneratedDocumentMetadata
        
        doc = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="生成的文档不存在")
        
        storage = get_storage_manager()
        
        # 从MinIO中实际查找文件：尝试所有可能的bucket
        bucket = None
        path = doc.minio_path
        
        if not path:
            raise HTTPException(status_code=404, detail="文件路径不存在")
        
        # 可能的bucket列表（按优先级）
        possible_buckets = []
        
        # 1. 数据库中的bucket（如果存在）
        if doc.bucket:
            possible_buckets.append(doc.bucket)
        
        # 2. 生成的文档通常使用generated_documents bucket
        if 'generated_documents' not in possible_buckets:
            possible_buckets.append(storage.buckets.get('generated_documents', 'generated_documents'))
        
        # 3. 所有已知的bucket
        all_buckets = list(storage.buckets.values())
        for b in all_buckets:
            if b not in possible_buckets:
                possible_buckets.append(b)
        
        # 在MinIO中查找文件
        found_bucket = None
        from minio.error import S3Error
        
        for test_bucket in possible_buckets:
            try:
                # 尝试检查文件是否存在
                storage.client.stat_object(test_bucket, path)
                found_bucket = test_bucket
                print(f"[预览] 在MinIO中找到文件: bucket={found_bucket}, path={path}")
                break
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    continue
                else:
                    print(f"[预览] 检查bucket {test_bucket} 时出错: {e}")
                    continue
            except Exception as e:
                print(f"[预览] 检查bucket {test_bucket} 时出错: {e}")
                continue
        
        if not found_bucket:
            error_detail = f"文件在MinIO中不存在。已检查的bucket: {possible_buckets}, 路径: {path}"
            print(f"[预览错误] {error_detail}")
            raise HTTPException(status_code=404, detail=error_detail)
        
        # 不使用version_id，直接下载最新版本
        file_data = storage.download_bytes(
            path=path,
            bucket=found_bucket,
            version_id=None,
            user=current_user.username,
            user_role=current_user.role,
            user_department=current_user.department
        )
        
        # 记录预览日志
        access_logger = get_access_logger()
        access_logger.log(
            action='preview',
            object_path=doc.minio_path,
            user=current_user.username,
            bucket=doc.bucket,
            user_role=current_user.role,
            user_department=current_user.department,
            details={'filename': doc.filename, 'doc_id': doc_id, 'format_type': doc.format_type}
        )
        
        # 预览模式：使用 inline 而不是 attachment
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=doc.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'inline; filename="{doc.filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览生成的文档失败: {str(e)}")


@app.get("/api/documents/generated/{doc_id}/download")
async def download_generated_document(
    doc_id: int,
    version: Optional[str] = Query(None, description="版本选择：original（原始版本，仅管理员）或 masked（脱敏版本）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载生成的文档"""
    try:
        from src.storage.database import GeneratedDocumentMetadata
        
        doc = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="生成的文档不存在")
        
        # 权限检查（黑名单）
        # 重要：从数据库读取后，SQLAlchemy的JSON列可能返回字符串或对象，需要统一处理
        import json
        
        blocked_users_raw = doc.blocked_users
        blocked_departments_raw = doc.blocked_departments
        
        # 调试：打印原始数据
        print(f"[DEBUG 下载权限] doc.blocked_users 原始值: {blocked_users_raw}, 类型: {type(blocked_users_raw)}")
        print(f"[DEBUG 下载权限] doc.blocked_departments 原始值: {blocked_departments_raw}, 类型: {type(blocked_departments_raw)}")
        print(f"[DEBUG 下载权限] 当前用户: {current_user.username}, 部门: {current_user.department}")
        
        # 处理blocked_users：统一转换为字符串列表
        blocked_users = []
        if blocked_users_raw:
            if isinstance(blocked_users_raw, str):
                try:
                    parsed = json.loads(blocked_users_raw)
                    if isinstance(parsed, list):
                        blocked_users = [str(u).strip().lower() for u in parsed if u]
                    else:
                        blocked_users = [str(blocked_users_raw).strip().lower()]
                except:
                    blocked_users = [str(blocked_users_raw).strip().lower()]
            elif isinstance(blocked_users_raw, list):
                blocked_users = [str(u).strip().lower() for u in blocked_users_raw if u]
            else:
                blocked_users = [str(blocked_users_raw).strip().lower()]
        
        # 处理blocked_departments：统一转换为字符串列表
        blocked_departments = []
        if blocked_departments_raw:
            if isinstance(blocked_departments_raw, str):
                try:
                    parsed = json.loads(blocked_departments_raw)
                    if isinstance(parsed, list):
                        blocked_departments = [str(d).strip().lower() for d in parsed if d]
                    else:
                        blocked_departments = [str(blocked_departments_raw).strip().lower()]
                except:
                    blocked_departments = [str(blocked_departments_raw).strip().lower()]
            elif isinstance(blocked_departments_raw, list):
                blocked_departments = [str(d).strip().lower() for d in blocked_departments_raw if d]
            else:
                blocked_departments = [str(blocked_departments_raw).strip().lower()]
        
        # 将用户名和部门名也转换为小写进行比较（确保大小写不敏感）
        current_username_lower = current_user.username.strip().lower() if current_user.username else ''
        current_dept_lower = current_user.department.strip().lower() if current_user.department else ''
        
        print(f"[DEBUG 下载权限] 处理后的 blocked_users: {blocked_users}")
        print(f"[DEBUG 下载权限] 处理后的 blocked_departments: {blocked_departments}")
        print(f"[DEBUG 下载权限] 当前用户名（小写）: '{current_username_lower}'")
        print(f"[DEBUG 下载权限] 当前部门（小写）: '{current_dept_lower}'")
        print(f"[DEBUG 下载权限] 用户 '{current_username_lower}' 在黑名单中: {current_username_lower in blocked_users}")
        print(f"[DEBUG 下载权限] 部门 '{current_dept_lower}' 在黑名单中: {current_dept_lower in blocked_departments}")
        
        # 检查用户是否在黑名单中（大小写不敏感）
        if current_username_lower and current_username_lower in blocked_users:
            print(f"[DEBUG 下载权限] [ERROR] 拒绝下载：用户 '{current_username_lower}' 在黑名单中")
            raise HTTPException(status_code=403, detail="您无权下载")
        
        # 检查用户部门是否在黑名单中（大小写不敏感）
        if current_dept_lower and current_dept_lower in blocked_departments:
            print(f"[DEBUG 下载权限] [ERROR] 拒绝下载：部门 '{current_dept_lower}' 在黑名单中")
            raise HTTPException(status_code=403, detail="您无权下载")
        
        print(f"[DEBUG 下载权限] [OK] 权限检查通过，允许下载")
        
        storage = get_storage_manager()
        
        # 管理员可以选择下载原始版本（如果启用了脱敏）
        # 注意：由于原始版本需要在生成时保存原始数据才能重新生成，当前实现中如果启用了脱敏，
        # 只保存了脱敏后的版本。因此，原始版本下载功能需要完善（在生成时同时保存原始版本）。
        # 当前如果管理员请求原始版本，返回脱敏版本并记录日志提示。
        if version == 'original' and current_user.role == 'admin' and doc.is_masked:
            # 记录日志提示：管理员请求原始版本但原始数据未保存
            access_logger = get_access_logger()
            access_logger.log(
                action='download_original_requested',
                object_path=doc.minio_path,
                user=current_user.username,
                bucket=doc.bucket,
                user_role=current_user.role,
                user_department=current_user.department,
                details={
                    'filename': doc.filename,
                    'doc_id': doc_id,
                    'format_type': doc.format_type,
                    'note': '管理员请求下载原始版本，但原始数据未保存，返回脱敏版本'
                }
            )
            # 继续执行，返回脱敏版本（因为原始版本未保存）
            # 如果需要真正的原始版本，需要在文档生成时同时保存原始版本
        
        # 从MinIO中实际查找文件：尝试所有可能的bucket
        bucket = None
        path = doc.minio_path
        
        if not path:
            raise HTTPException(status_code=404, detail="文件路径不存在")
        
        # 可能的bucket列表（按优先级）
        possible_buckets = []
        
        # 1. 数据库中的bucket（如果存在）
        if doc.bucket:
            possible_buckets.append(doc.bucket)
        
        # 2. 生成的文档通常使用generated_documents bucket
        if 'generated_documents' not in possible_buckets:
            possible_buckets.append(storage.buckets.get('generated_documents', 'generated_documents'))
        
        # 3. 所有已知的bucket
        all_buckets = list(storage.buckets.values())
        for b in all_buckets:
            if b not in possible_buckets:
                possible_buckets.append(b)
        
        # 在MinIO中查找文件
        found_bucket = None
        from minio.error import S3Error
        
        for test_bucket in possible_buckets:
            try:
                # 尝试检查文件是否存在
                storage.client.stat_object(test_bucket, path)
                found_bucket = test_bucket
                print(f"[下载生成的文档] 在MinIO中找到文件: bucket={found_bucket}, path={path}")
                break
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    continue
                else:
                    print(f"[下载生成的文档] 检查bucket {test_bucket} 时出错: {e}")
                    continue
            except Exception as e:
                print(f"[下载生成的文档] 检查bucket {test_bucket} 时出错: {e}")
                continue
        
        if not found_bucket:
            error_detail = f"文件在MinIO中不存在。已检查的bucket: {possible_buckets}, 路径: {path}"
            print(f"[下载生成的文档错误] {error_detail}")
            raise HTTPException(status_code=404, detail=error_detail)
        
        # 不使用version_id，直接下载最新版本
        file_data = storage.download_bytes(
            path=path,
            bucket=found_bucket,
            version_id=None,
            user=current_user.username,
            user_role=current_user.role,
            user_department=current_user.department
        )
        
        # 记录下载日志
        log_details = {'filename': doc.filename, 'doc_id': doc_id, 'format_type': doc.format_type}
        if version == 'original':
            log_details['version'] = 'original'
            log_details['note'] = '管理员下载原始版本请求（返回脱敏版本，原始数据未保存）'
        
        access_logger = get_access_logger()
        access_logger.log(
            action='download',
            object_path=doc.minio_path,
            user=current_user.username,
            bucket=found_bucket,
            user_role=current_user.role,
            user_department=current_user.department,
            details=log_details
        )
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=doc.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{doc.filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载生成的文档失败: {str(e)}")


@app.put("/api/generated/{doc_id}/permissions")
async def update_document_permissions(
    doc_id: int,
    request: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新文档下载权限设置（仅管理员）"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限设置文档权限，仅管理员可操作")
    
    try:
        from src.storage.database import GeneratedDocumentMetadata
        
        doc = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="生成的文档不存在")
        
        # 更新权限设置（确保存储为JSON数组格式）
        import json
        if 'blocked_users' in request:
            users = request.get('blocked_users', [])
            # 确保是列表类型
            if isinstance(users, str):
                try:
                    users = json.loads(users)
                except:
                    users = [users] if users else []
            # 确保是列表，且元素都是字符串
            if isinstance(users, list):
                users = [str(u).strip() for u in users if u]  # 转换为字符串列表，去除空值
            else:
                users = []
            doc.blocked_users = users
            print(f"[DEBUG 权限设置] blocked_users 保存值: {doc.blocked_users}, 类型: {type(doc.blocked_users)}")
        if 'blocked_departments' in request:
            depts = request.get('blocked_departments', [])
            # 确保是列表类型
            if isinstance(depts, str):
                try:
                    depts = json.loads(depts)
                except:
                    depts = [depts] if depts else []
            # 确保是列表，且元素都是字符串
            if isinstance(depts, list):
                depts = [str(d).strip() for d in depts if d]  # 转换为字符串列表，去除空值
            else:
                depts = []
            doc.blocked_departments = depts
            print(f"[DEBUG 权限设置] blocked_departments 保存值: {doc.blocked_departments}, 类型: {type(doc.blocked_departments)}")
        
        db.commit()
        # 强制刷新，确保从数据库重新加载
        db.refresh(doc)
        # 再次打印，确认数据库中的实际值
        print(f"[DEBUG 权限设置] 保存后从数据库读取 blocked_users: {doc.blocked_users}, 类型: {type(doc.blocked_users)}")
        print(f"[DEBUG 权限设置] 保存后从数据库读取 blocked_departments: {doc.blocked_departments}, 类型: {type(doc.blocked_departments)}")
        
        return {"message": "权限设置已更新", "doc_id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新权限设置失败: {str(e)}")


@app.delete("/api/documents/generated/{doc_id}")
async def delete_generated_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除生成的文档（删除MySQL记录和MinIO文件）"""
    try:
        from src.storage.database import GeneratedDocumentMetadata
        
        doc = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="生成的文档不存在")
        
        # 检查权限：只能删除自己创建的文档，或管理员可以删除所有文档
        if current_user.role != 'admin' and doc.created_by != current_user.username:
            raise HTTPException(status_code=403, detail="无权限删除此文档")
        
        # 检查黑名单：黑名单用户不能删除文档（使用与下载相同的处理逻辑）
        import json
        
        blocked_users_raw = doc.blocked_users
        blocked_departments_raw = doc.blocked_departments
        
        # 处理blocked_users：统一转换为字符串列表（小写）
        blocked_users = []
        if blocked_users_raw:
            if isinstance(blocked_users_raw, str):
                try:
                    parsed = json.loads(blocked_users_raw)
                    if isinstance(parsed, list):
                        blocked_users = [str(u).strip().lower() for u in parsed if u]
                    else:
                        blocked_users = [str(blocked_users_raw).strip().lower()]
                except:
                    blocked_users = [str(blocked_users_raw).strip().lower()]
            elif isinstance(blocked_users_raw, list):
                blocked_users = [str(u).strip().lower() for u in blocked_users_raw if u]
            else:
                blocked_users = [str(blocked_users_raw).strip().lower()]
        
        # 处理blocked_departments：统一转换为字符串列表（小写）
        blocked_departments = []
        if blocked_departments_raw:
            if isinstance(blocked_departments_raw, str):
                try:
                    parsed = json.loads(blocked_departments_raw)
                    if isinstance(parsed, list):
                        blocked_departments = [str(d).strip().lower() for d in parsed if d]
                    else:
                        blocked_departments = [str(blocked_departments_raw).strip().lower()]
                except:
                    blocked_departments = [str(blocked_departments_raw).strip().lower()]
            elif isinstance(blocked_departments_raw, list):
                blocked_departments = [str(d).strip().lower() for d in blocked_departments_raw if d]
            else:
                blocked_departments = [str(blocked_departments_raw).strip().lower()]
        
        # 将用户名和部门名也转换为小写进行比较（确保大小写不敏感）
        current_username_lower = current_user.username.strip().lower() if current_user.username else ''
        current_dept_lower = current_user.department.strip().lower() if current_user.department else ''
        
        # 检查用户是否在黑名单中（即使是管理员，黑名单用户也不能删除）
        if current_username_lower and current_username_lower in blocked_users:
            raise HTTPException(status_code=403, detail="您无权删除")
        
        # 检查用户部门是否在黑名单中
        if current_dept_lower and current_dept_lower in blocked_departments:
            raise HTTPException(status_code=403, detail="您无权删除")
        
        storage = get_storage_manager()
        access_logger = get_access_logger()
        
        # 1. 删除MinIO中的文件（使用生成的文档的bucket）
        deleted_minio = False
        if doc.minio_path:
            try:
                storage.client.remove_object(doc.bucket, doc.minio_path)
                deleted_minio = True
            except Exception as e:
                print(f"删除MinIO文件失败 {doc.minio_path}: {e}")
        
        # 2. 删除MySQL记录
        db.delete(doc)
        db.commit()
        
        # 3. 记录访问日志
        try:
            access_logger.log(
                action='delete',
                object_path=doc.minio_path,
                user=current_user.username,
                bucket=doc.bucket,
                user_role=current_user.role,
                user_department=current_user.department,
                details={
                    'filename': doc.filename,
                    'doc_id': doc_id,
                    'format_type': doc.format_type,
                    'deleted_minio': deleted_minio
                }
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return {
            "success": True,
            "message": f"生成的文档已删除（MySQL记录已删除，MinIO文件{'已删除' if deleted_minio else '删除失败'}）",
            "doc_id": doc_id,
            "deleted_minio": deleted_minio
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除生成的文档失败: {str(e)}")


# ==================== 模板管理 API ====================

@app.get("/api/templates")
async def get_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    group_by_name: bool = Query(False, description="是否按模板名称分组（显示同一模板的不同格式版本）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模板列表（支持按模板名称分组）"""
    try:
        query = db.query(TemplateMetadata).filter(TemplateMetadata.is_latest == True)
        
        if category:
            query = query.filter(TemplateMetadata.category == category)
        
        if search:
            query = query.filter(
                or_(
                    TemplateMetadata.template_name.like(f"%{search}%"),
                    TemplateMetadata.filename.like(f"%{search}%")
                )
            )
        
        templates = query.order_by(TemplateMetadata.template_name, TemplateMetadata.created_at.desc()).all()
        
        if group_by_name:
            # 按模板名称分组
            template_groups = {}
            for tpl in templates:
                name = tpl.template_name
                if name not in template_groups:
                    template_groups[name] = []
                template_groups[name].append(tpl)
            
            # 转换为分组后的结果
            result = []
            for name, tpl_list in template_groups.items():
                # 使用最新创建的模板作为主模板
                main_tpl = max(tpl_list, key=lambda x: x.created_at if x.created_at else datetime.min)
                
                tags_list = []
                if main_tpl.tags:
                    if isinstance(main_tpl.tags, dict):
                        tags_list = list(main_tpl.tags.values())
                    elif isinstance(main_tpl.tags, list):
                        tags_list = main_tpl.tags
                
                # 收集所有格式类型
                format_types = [t.format_type for t in tpl_list]
                
                # 建立格式到ID的映射
                format_to_id_map = {}
                for tpl in tpl_list:
                    format_to_id_map[tpl.format_type] = tpl.id
                
                result.append({
                    "id": main_tpl.id,  # 使用主模板的ID
                    "name": name,
                    "version": f"v{main_tpl.version}",
                    "format_type": main_tpl.format_type,
                    "available_formats": format_types,  # 所有可用的格式
                    "category": main_tpl.category or "-",
                    "description": main_tpl.change_log or "-",
                    "tags": tags_list,
                    "created_at": main_tpl.created_at.strftime("%Y-%m-%d %H:%M:%S") if main_tpl.created_at else "-",
                    "template_ids": [t.id for t in tpl_list],  # 所有格式版本的ID
                    "format_to_id": format_to_id_map  # 格式到ID的映射 {format: id}
                })
            
            # 分页
            total = len(result)
            offset = (page - 1) * page_size
            result = result[offset:offset + page_size]
        else:
            # 不分组，直接返回
            total = len(templates)
            offset = (page - 1) * page_size
            templates = templates[offset:offset + page_size]
            
            result = []
            for tpl in templates:
                tags_list = []
                if tpl.tags:
                    if isinstance(tpl.tags, dict):
                        tags_list = list(tpl.tags.values())
                    elif isinstance(tpl.tags, list):
                        tags_list = tpl.tags
                
                result.append({
                    "id": tpl.id,
                    "name": tpl.template_name,
                    "version": f"v{tpl.version}",
                    "format_type": tpl.format_type,
                    "available_formats": [tpl.format_type],
                    "category": tpl.category or "-",
                    "description": tpl.change_log or "-",
                    "tags": tags_list,
                    "created_at": tpl.created_at.strftime("%Y-%m-%d %H:%M:%S") if tpl.created_at else "-"
                })
        
        return {
            "templates": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询模板列表失败: {str(e)}")


@app.post("/api/templates/upload")
async def upload_template(
    file: UploadFile = File(...),
    template_name: str = Form(...),
    template_type: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传模板（存MinIO，元数据存MySQL）"""
    try:
        file_content = await file.read()
        file_size = len(file_content)
        
        # 自动检测格式类型
        filename_lower = file.filename.lower()
        template_name_lower = template_name.lower() if template_name else ''
        
        if filename_lower.endswith('.json'):
            # JSON模板文件（数据模板）
            format_type = 'json'
        elif filename_lower.endswith('.docx'):
            format_type = 'word'
        elif filename_lower.endswith('.html') or filename_lower.endswith('.htm'):
            # HTML模板，需要判断是HTML还是PDF模板
            # 如果文件名、模板名称或路径包含'pdf'，则认为是PDF模板
            if 'pdf' in filename_lower or 'pdf' in template_name_lower:
                format_type = 'pdf'
            else:
                format_type = 'html'
        elif filename_lower.endswith('.pdf'):
            format_type = 'pdf'
        else:
            # 默认根据文件内容或扩展名判断
            # 如果模板名称包含格式提示，使用提示的格式
            if 'word' in template_name_lower or 'docx' in template_name_lower:
                format_type = 'word'
            elif 'pdf' in template_name_lower:
                format_type = 'pdf'
            elif 'html' in template_name_lower:
                format_type = 'html'
            else:
                format_type = 'html'  # 默认HTML
        
        # 确定分类（保留用于兼容）
        template_category = category or "未分类"
        
        # 上传到MinIO
        storage = get_storage_manager()
        metadata = {
            "author": current_user.username,
            "department": current_user.department,
            "description": description or ""
        }
        
        # 构建模板路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        minio_filename = f"{template_name}_{timestamp}{Path(file.filename).suffix}"
        minio_path = f"templates/{format_type}/{minio_filename}"
        
        result = storage.upload_bytes(
            data=file_content,
            filename=minio_filename,
            category="templates",
            content_type=get_content_type(file.filename),
            metadata=metadata
        )
        
        # 保存到数据库 - 使用传入的 db 会话，避免会话绑定问题
        with TemplateMetadataManager(session=db) as mgr:
            # 获取当前版本号
            existing = mgr.get_template(template_name, format_type=format_type, is_latest=True)
            new_version = (existing.version + 1) if existing else 1
            
            template = mgr.add_template(
                template_name=template_name,
                minio_path=result['path'],
                bucket=storage.buckets['templates'],  # 使用 templates 桶
                filename=file.filename,
                file_size=file_size,
                content_type=get_content_type(file.filename),
                format_type=format_type,
                version=new_version,
                is_latest=True,
                category=template_category,
                # template_type=template_type,  # 已移除：数据库表中不存在此列
                change_log=description or "上传新模板",
                created_by=current_user.username
            )
            
            # 将旧版本设为非最新
            if existing:
                existing.is_latest = False
            
            # 提交事务
            db.commit()
            
            # 在会话内提取需要的数据
            template_id = template.id
        
        # 从统一配置文件获取数据库信息
        config = load_config(str(backend_root / "config" / "config.yaml"))
        mysql_db = config.get('mysql', {}).get('database', 'unknown')
        
        return {
            "success": True,
            "message": "模板上传成功",
            "template_id": template_id,
            "template_name": template_name,
            "version": new_version,
            "minio_bucket": storage.bucket,
            "minio_path": result['path'],
            "mysql_info": {
                "table": "templates",
                "database": mysql_db,
                "record_id": template_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传模板失败: {str(e)}")


@app.get("/api/templates/{template_id}")
async def get_template_detail(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模板详情"""
    template = db.query(TemplateMetadata).filter(TemplateMetadata.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    tags_list = []
    if template.tags:
        if isinstance(template.tags, dict):
            tags_list = list(template.tags.values())
        elif isinstance(template.tags, list):
            tags_list = template.tags
    
    # 查询同一模板名称的所有格式版本
    all_formats = db.query(TemplateMetadata).filter(
        TemplateMetadata.template_name == template.template_name,
        TemplateMetadata.is_latest == True
    ).all()
    
    format_types = [f.format_type for f in all_formats]
    
    return {
        "id": template.id,
        "name": template.template_name,
        "version": f"v{template.version}",
        "format_type": template.format_type,
        "available_formats": format_types,
        "category": template.category or "-",
        "description": template.change_log or "-",
        "tags": tags_list,
        "filename": template.filename,
        "file_size": template.file_size,
        "created_at": template.created_at.strftime("%Y-%m-%d %H:%M:%S") if template.created_at else "-",
        "created_by": template.created_by or "系统",
        "minio_path": template.minio_path,
        "is_latest": template.is_latest
    }


@app.get("/api/templates/{template_id}/versions")
async def get_template_versions(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取模板版本历史"""
    template = db.query(TemplateMetadata).filter(TemplateMetadata.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 查询所有版本（同一模板名称和格式类型）
    versions = db.query(TemplateMetadata).filter(
        TemplateMetadata.template_name == template.template_name,
        TemplateMetadata.format_type == template.format_type
    ).order_by(TemplateMetadata.version.desc()).all()
    
    result = []
    for v in versions:
        result.append({
            "id": v.id,
            "version": f"v{v.version}",
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S") if v.created_at else "-",
            "change_log": v.change_log or "-",
            "is_latest": v.is_latest,
            "format_type": v.format_type
        })
    
    return {
        "template_id": template_id,
        "template_name": template.template_name,
        "format_type": template.format_type,
        "versions": result
    }


@app.post("/api/templates/{template_id}/edit")
async def edit_template(
    template_id: int,
    template_name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """编辑模板元数据"""
    template = db.query(TemplateMetadata).filter(TemplateMetadata.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 权限检查：只能编辑自己创建的模板，或管理员可以编辑所有模板
    if current_user.role != 'admin' and template.created_by != current_user.username:
        raise HTTPException(status_code=403, detail="无权限编辑此模板")
    
    # 更新字段
    if template_name:
        template.template_name = template_name
    if category:
        template.category = category
    if description is not None:
        template.change_log = description
    
    db.commit()
    
    return {
        "success": True,
        "message": "模板编辑成功",
        "template_id": template_id
    }


@app.get("/api/templates/{template_id}/download")
async def download_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载模板文件"""
    try:
        template = db.query(TemplateMetadata).filter(TemplateMetadata.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        storage = get_storage_manager()
        file_data = storage.download_bytes(
            path=template.minio_path,
            bucket=template.bucket,  # 使用模板存储的bucket
            version_id=template.version_id,
            user=current_user.username,
            user_role=current_user.role,
            user_department=current_user.department
        )
        
        # 记录下载日志
        access_logger = get_access_logger()
        access_logger.log(
            action='download',
            object_path=template.minio_path,
            user=current_user.username,
            bucket=template.bucket,
            user_role=current_user.role,
            user_department=current_user.department,
            details={'filename': template.filename, 'template_id': template_id, 'template_name': template.template_name}
        )
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=template.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{template.filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载模板失败: {str(e)}")


@app.post("/api/templates/{template_id}/rollback")
async def rollback_template(
    template_id: int,
    target_version: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """回滚模板到指定版本"""
    try:
        # 获取当前模板
        current_template = db.query(TemplateMetadata).filter(TemplateMetadata.id == template_id).first()
        if not current_template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 权限检查：只能回滚自己创建的模板，或管理员可以回滚所有模板
        if current_user.role != 'admin' and current_template.created_by != current_user.username:
            raise HTTPException(status_code=403, detail="无权限回滚此模板")
        
        # 查找目标版本
        target_template = db.query(TemplateMetadata).filter(
            TemplateMetadata.template_name == current_template.template_name,
            TemplateMetadata.format_type == current_template.format_type,
            TemplateMetadata.version == target_version
        ).first()
        
        if not target_template:
            raise HTTPException(status_code=404, detail=f"目标版本 v{target_version} 不存在")
        
        # 如果目标版本就是当前版本，无需回滚
        if target_template.id == current_template.id:
            return {
                "success": True,
                "message": "模板已经是目标版本，无需回滚",
                "template_id": template_id,
                "version": target_version
            }
        
        # 将目标版本设为最新版本
        # 1. 将当前最新版本设为非最新
        db.query(TemplateMetadata).filter(
            TemplateMetadata.template_name == current_template.template_name,
            TemplateMetadata.format_type == current_template.format_type,
            TemplateMetadata.is_latest == True
        ).update({"is_latest": False})
        
        # 2. 将目标版本设为最新
        target_template.is_latest = True
        
        db.commit()
        
        # 记录回滚日志
        access_logger = get_access_logger()
        access_logger.log(
            action='rollback_template',
            object_path=target_template.minio_path,
            user=current_user.username,
            bucket=target_template.bucket,
            user_role=current_user.role,
            user_department=current_user.department,
            details={
                'template_id': template_id,
                'template_name': current_template.template_name,
                'from_version': current_template.version,
                'to_version': target_version
            }
        )
        
        return {
            "success": True,
            "message": f"模板已回滚到版本 v{target_version}",
            "template_id": template_id,
            "current_version": target_version,
            "previous_version": current_template.version
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"回滚模板失败: {str(e)}")


@app.delete("/api/templates/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除模板"""
    template = db.query(TemplateMetadata).filter(TemplateMetadata.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # 只允许admin删除
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限删除模板")
    
    db.delete(template)
    db.commit()
    
    return {"success": True, "message": "模板已删除"}


# ==================== 文档生成 API ====================

@app.get("/api/documents/recommend")
async def recommend_document_generation(
    data_filename: Optional[str] = Query(None, description="数据文件名（用于匹配模板）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """推荐文档生成（根据数据文件名匹配模板）"""
    try:
        # 获取所有最新模板
        templates = db.query(TemplateMetadata).filter(
            TemplateMetadata.is_latest == True
        ).all()
        
        recommendations = []
        
        if data_filename:
            # 从数据文件名提取可能的模板名称
            data_name = Path(data_filename).stem.lower()
            
            # 按模板名称分组
            template_groups = {}
            for tpl in templates:
                name = tpl.template_name.lower()
                if name not in template_groups:
                    template_groups[name] = []
                template_groups[name].append(tpl)
            
            # 匹配模板名称
            for tpl_name, tpl_list in template_groups.items():
                # 检查模板名称是否与数据文件名匹配
                if data_name in tpl_name or tpl_name in data_name:
                    # 使用最新创建的模板作为主模板
                    main_tpl = max(tpl_list, key=lambda x: x.created_at if x.created_at else datetime.min)
                    
                    format_types = [t.format_type for t in tpl_list]
                    
                    recommendations.append({
                        "template_id": main_tpl.id,
                        "template_name": main_tpl.template_name,
                        "available_formats": format_types,
                        "category": main_tpl.category or "-",
                        "match_score": 1.0 if data_name == tpl_name else 0.8,  # 完全匹配分数更高
                        "reason": f"数据文件名 '{data_filename}' 与模板 '{main_tpl.template_name}' 匹配"
                    })
        
        # 如果没有匹配，返回所有模板（按分类分组）
        if not recommendations:
            category_groups = {}
            for tpl in templates:
                cat = tpl.category or "未分类"
                if cat not in category_groups:
                    category_groups[cat] = []
                category_groups[cat].append(tpl)
            
            for cat, tpl_list in category_groups.items():
                main_tpl = max(tpl_list, key=lambda x: x.created_at if x.created_at else datetime.min)
                format_types = [t.format_type for t in tpl_list]
                
                recommendations.append({
                    "template_id": main_tpl.id,
                    "template_name": main_tpl.template_name,
                    "available_formats": format_types,
                    "category": cat,
                    "match_score": 0.5,
                    "reason": f"分类 '{cat}' 的模板"
                })
        
        # 按匹配分数排序
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        
        return {
            "recommendations": recommendations[:10],  # 返回前10个推荐
            "total": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐文档生成失败: {str(e)}")


@app.post("/api/documents/generate")
async def generate_document(
    template_id: int = Form(...),
    data_file: Optional[UploadFile] = File(None),
    data_file_id: Optional[int] = Form(None),
    output_format: Optional[str] = Form(None),
    enable_masking: Optional[bool] = Form(False),
    enable_encryption: Optional[bool] = Form(False),
    pdf_password: Optional[str] = Form(None),
    enable_watermark: Optional[bool] = Form(False),
    watermark_text: Optional[str] = Form(None),
    watermark_image_id: Optional[int] = Form(None),  # 水印图片ID（从图片管理中选择）
    restrict_edit: Optional[bool] = Form(False),
    restrict_edit_password: Optional[str] = Form(None),
    enable_table: Optional[bool] = Form(True),  # 默认启用表格生成
    enable_chart: Optional[bool] = Form(True),  # 默认启用图表生成
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """生成文档（使用模板和数据文件）
    
    支持两种方式：
    1. 上传新文件：提供 data_file
    2. 使用已有文件：提供 data_file_id
    """
    try:
        # 1. 获取模板信息
        template = db.query(TemplateMetadata).filter(TemplateMetadata.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")
        
        # 2. 读取数据文件（支持上传新文件或使用已有文件）
        file_content = None
        file_ext = None
        data_filename = None
        
        if data_file_id:
            # 使用已有文件
            doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == data_file_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="数据文件不存在")
            
            # 验证文件格式
            filename_lower = doc.filename.lower()
            if not (filename_lower.endswith('.json') or filename_lower.endswith('.csv')):
                raise HTTPException(status_code=400, detail="所选文件不是JSON或CSV格式，请选择JSON或CSV文件")
            
            # 从MinIO下载文件（使用文档的bucket）
            storage = get_storage_manager()
            
            # 确定bucket：优先使用数据库中的bucket，如果不正确，根据路径推断
            bucket = doc.bucket
            if not bucket or (bucket == 'documents' and doc.category == '未分类'):
                if doc.minio_path:
                    path_parts = doc.minio_path.split('/')
                    if path_parts:
                        category = path_parts[0]
                        bucket = storage._get_bucket_for_category(category)
            
            if not bucket and doc.category:
                bucket = storage._get_bucket_for_category(doc.category)
            
            if not bucket:
                bucket = storage.bucket
            
            # 不使用version_id，直接下载最新版本（避免版本不匹配问题）
            file_content = storage.download_bytes(
                path=doc.minio_path,
                bucket=bucket,
                version_id=None,  # 不使用version_id
                user=current_user.username,
                user_role=current_user.role,
                user_department=current_user.department
            )
            from pathlib import Path as PathLib
            file_ext = PathLib(doc.filename).suffix.lower()
            data_filename = doc.filename
            
        elif data_file:
            # 上传新文件
            file_content = await data_file.read()
            from pathlib import Path as PathLib
            file_ext = PathLib(data_file.filename).suffix.lower()
            data_filename = data_file.filename
        else:
            raise HTTPException(status_code=400, detail="请提供数据文件（上传新文件或选择已有文件）")
        
        # ========== 按照要求的流程生成文档 ==========
        # 流程：1. 先看原文件是csv还是json
        #       2. 然后看模板是word还是pdf
        #       3. 然后看生成的是word还是html还是pdf（html和pdf使用一套模板）
        #       4. 最后按照要求生成文档
        
        # 步骤1: 判断数据文件格式（csv/json）
        data_file_format = None
        if file_ext == '.json':
            data_file_format = 'json'
            print(f"[流程] 步骤1: 数据文件格式 = JSON")
        elif file_ext == '.csv':
            data_file_format = 'csv'
            print(f"[流程] 步骤1: 数据文件格式 = CSV")
        else:
            raise HTTPException(status_code=400, detail="不支持的数据文件格式，请使用JSON或CSV")
        
        # 步骤2: 判断模板格式（word/pdf）
        template_format = template.format_type.lower() if template.format_type else 'word'
        if template_format not in ['word', 'pdf', 'html']:
            template_format = 'word'  # 默认使用word
        print(f"[流程] 步骤2: 模板格式 = {template_format.upper()}")
        
        # 步骤3: 判断输出格式（word/html/pdf，html和pdf使用一套模板）
        if output_format and output_format.lower() in ['pdf', 'word', 'html']:
            final_output_format = output_format.lower()
        else:
            # 如果没有指定输出格式，使用模板格式
            final_output_format = template_format
        print(f"[流程] 步骤3: 输出格式 = {final_output_format.upper()}")
        
        # 重要：HTML和PDF使用同一套模板（HTML模板）
        # 如果输出格式是PDF或HTML，但模板是PDF格式，需要查找对应的HTML模板
        template_to_use = template
        if final_output_format in ['pdf', 'html']:
            # PDF和HTML使用HTML模板
            if template_format == 'word':
                # 如果模板是word，需要查找对应的HTML/PDF模板
                # 查找同名的HTML模板
                html_template = db.query(TemplateMetadata).filter(
                    TemplateMetadata.template_name == template.template_name,
                    TemplateMetadata.format_type.in_(['html', 'pdf']),
                    TemplateMetadata.is_latest == True
                ).order_by(TemplateMetadata.version.desc()).first()
                
                if html_template:
                    template_to_use = html_template
                    print(f"[流程] 步骤3.1: 找到HTML/PDF模板，ID={html_template.id}, 格式={html_template.format_type}")
                else:
                    # 如果找不到HTML/PDF模板，明确报错
                    error_msg = f"生成{final_output_format.upper()}格式需要HTML或PDF模板，但模板'{template.template_name}'只有Word格式。请上传对应的HTML/PDF模板。"
                    print(f"[流程] 步骤3.1: {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)
            elif template_format == 'pdf':
                # 如果模板是PDF，直接使用（PDF模板实际是HTML格式）
                template_to_use = template
                print(f"[流程] 步骤3.1: 使用PDF模板（实际为HTML格式）")
            # 如果模板已经是HTML，直接使用
        else:
            # Word输出使用Word模板
            if template_format != 'word':
                # 如果模板不是word，查找对应的word模板
                word_template = db.query(TemplateMetadata).filter(
                    TemplateMetadata.template_name == template.template_name,
                    TemplateMetadata.format_type == 'word',
                    TemplateMetadata.is_latest == True
                ).order_by(TemplateMetadata.version.desc()).first()
                
                if word_template:
                    template_to_use = word_template
                    print(f"[流程] 步骤3.1: 找到Word模板，ID={word_template.id}")
                else:
                    # 如果找不到Word模板，明确报错
                    error_msg = f"生成Word格式需要Word模板，但模板'{template.template_name}'只有{template_format.upper()}格式。请上传对应的Word模板。"
                    print(f"[流程] 步骤3.1: {error_msg}")
                    raise HTTPException(status_code=400, detail=error_msg)
        
        # 步骤4: 解析数据文件（使用 DataProcessor 确保数据格式正确）
        print(f"[流程] 步骤4: 开始解析数据文件，格式: {data_file_format}, 文件名: {data_filename}")
        from src.core.data_processor import DataProcessor
        import tempfile
        import json
        
        data_processor = DataProcessor()
        data_dict = {}
        
        try:
            if data_file_format == 'json':
                # JSON 文件：直接解析
                print(f"[DEBUG] 解析JSON文件，大小: {len(file_content)} 字节")
                raw_data = json.loads(file_content.decode('utf-8'))
                print(f"[DEBUG] JSON解析成功，原始数据键: {list(raw_data.keys())}")
                
                # 重要改进：将原始JSON数据的所有字段都展开到data_dict
                # 这样模板可以访问任何原始数据字段，如 store、products 等
                data_dict = dict(raw_data)  # 复制所有原始数据
                
                # 表格数据：如果启用表格生成，处理 table_data 和 table_merge
                if enable_table:
                    if 'table_data' in raw_data:
                        # 将 table_data 转换为标准格式
                        if isinstance(raw_data['table_data'], list):
                            data_dict['tables'] = {'data': raw_data['table_data']}
                            # 增加兼容性：允许 {{table:table_data}}
                            data_dict['tables']['table_data'] = raw_data['table_data']
                        else:
                            data_dict['tables'] = raw_data['table_data']
                        print(f"[DEBUG] 启用表格生成，table_data: {len(raw_data['table_data']) if isinstance(raw_data['table_data'], list) else 'N/A'} 行")
                    
                    # 表格合并配置
                    if 'table_merge' in raw_data:
                        print(f"[DEBUG] 表格合并配置: {raw_data['table_merge']}")
                else:
                    print(f"[DEBUG] 表格生成已禁用，跳过 table_data")
                    # 如果禁用表格，删除tables
                    data_dict.pop('tables', None)
                    data_dict.pop('table_data', None)
                
                # 图表数据：如果启用图表生成，处理 chart_data
                if enable_chart:
                    if 'chart_data' in raw_data:
                        # 将 chart_data 转换为标准格式 {chart_name: chart_data}
                        chart_name = raw_data['chart_data'].get('title', 'chart_data')
                        data_dict['charts'] = {chart_name: raw_data['chart_data']}
                        # 同时保留原始键名，增加兼容性
                        data_dict['charts']['chart_data'] = raw_data['chart_data']
                        print(f"[DEBUG] 启用图表生成，chart_data: {raw_data['chart_data'].get('type', 'N/A')}")
                else:
                    print(f"[DEBUG] 图表生成已禁用，跳过 chart_data")
                    # 如果禁用图表，删除charts
                    data_dict.pop('charts', None)
                    data_dict.pop('chart_data', None)
                
                # 图片数据日志
                if 'images' in raw_data:
                    print(f"[DEBUG] 图片数据: {len(raw_data['images']) if isinstance(raw_data['images'], list) else 'N/A'}")
                
                # 添加选项变量（传递给模板，用于条件判断）
                data_dict['enable_table'] = enable_table
                data_dict['enable_chart'] = enable_chart
                
                print(f"[DEBUG] 处理后的数据字典键: {list(data_dict.keys())}")
                print(f"[DEBUG] 选项: enable_table={enable_table}, enable_chart={enable_chart}")
                
                # 如果启用了脱敏，应用敏感字段脱敏
                if enable_masking:
                    from src.security.data_masking import DataMasker
                    masker = DataMasker()
                    print(f"[DEBUG] 启用敏感字段脱敏")
                    # 对数据字典进行脱敏处理（递归处理嵌套结构）
                    data_dict = masker.mask_dict(data_dict)
                    print(f"[DEBUG] 脱敏处理完成")
            elif data_file_format == 'csv':
                # CSV 文件：使用 DataProcessor 处理，确保格式正确
                print(f"[DEBUG] 解析CSV文件，大小: {len(file_content)} 字节")
                # 将文件内容保存到临时文件，然后使用 DataProcessor 处理
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_csv_path = temp_file.name
                
                try:
                    from pathlib import Path as PathLib
                    # 使用 DataProcessor 处理 CSV，它会正确转换为标准格式
                    print(f"[DEBUG] 使用DataProcessor处理CSV文件: {temp_csv_path}")
                    data_structure = data_processor.process(PathLib(temp_csv_path))
                    print(f"[DEBUG] CSV处理成功，tables类型: {type(data_structure.tables)}, tables键: {list(data_structure.tables.keys()) if isinstance(data_structure.tables, dict) else 'N/A'}")
                    # 将 DataStructure 转换回字典格式
                    # 确保tables是字典格式
                    if isinstance(data_structure.tables, list):
                        # 如果是列表，转换为字典格式
                        data_dict = {
                            'title': data_structure.title,
                            'content': data_structure.content,
                            'tables': {'data': data_structure.tables},  # 转换为字典格式
                            'charts': data_structure.charts,
                            'images': data_structure.images
                        }
                        # 同时直接提供 table_data 变量，增加兼容性
                        data_dict['table_data'] = data_structure.tables
                    else:
                        data_dict = {
                            'title': data_structure.title,
                            'content': data_structure.content,
                            'tables': data_structure.tables,  # 这应该是一个字典 {table_name: [rows]}
                            'charts': data_structure.charts,
                            'images': data_structure.images
                        }
                        # 尝试从 tables 字典中提取默认表格数据
                        if isinstance(data_structure.tables, dict):
                            if 'data' in data_structure.tables:
                                data_dict['table_data'] = data_structure.tables['data']
                            elif 'table_data' in data_structure.tables:
                                data_dict['table_data'] = data_structure.tables['table_data']
                            elif len(data_structure.tables) > 0:
                                # 使用第一个表格作为默认 table_data
                                first_key = list(data_structure.tables.keys())[0]
                                data_dict['table_data'] = data_structure.tables[first_key]
                    
                    # 添加选项变量（传递给模板，用于条件判断）
                    data_dict['enable_table'] = enable_table
                    data_dict['enable_chart'] = enable_chart
                    
                    print(f"[DEBUG] 数据字典构建成功，tables类型: {type(data_dict.get('tables'))}, tables键: {list(data_dict['tables'].keys()) if isinstance(data_dict.get('tables'), dict) else 'N/A'}")
                    print(f"[DEBUG] 选项: enable_table={enable_table}, enable_chart={enable_chart}")
                    # 打印表格数据示例（前2行）
                    if isinstance(data_dict.get('tables'), dict) and 'data' in data_dict['tables']:
                        table_data = data_dict['tables']['data']
                        if isinstance(table_data, list) and len(table_data) > 0:
                            print(f"[DEBUG] 表格数据示例（第1行）: {table_data[0]}")
                            if len(table_data) > 1:
                                print(f"[DEBUG] 表格数据示例（第2行）: {table_data[1]}")
                    
                    # 如果启用了脱敏，应用敏感字段脱敏
                    if enable_masking:
                        from src.security.data_masking import DataMasker
                        masker = DataMasker()
                        print(f"[DEBUG] 启用敏感字段脱敏")
                        # 对数据字典进行脱敏处理（递归处理嵌套结构）
                        data_dict = masker.mask_dict(data_dict)
                        print(f"[DEBUG] 脱敏处理完成")
                finally:
                    # 清理临时文件
                    import os
                    try:
                        os.unlink(temp_csv_path)
                    except:
                        pass
        except Exception as e:
            print(f"[ERROR] 数据解析失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"数据解析失败: {str(e)}")
        
        # 步骤5: 从MinIO下载模板文件（使用模板的bucket）
        print(f"[流程] 步骤5: 开始下载模板，模板ID: {template_to_use.id}, 模板名: {template_to_use.template_name}, 格式: {template_to_use.format_type}, MinIO路径: {template_to_use.minio_path}, Bucket: {template_to_use.bucket}")
        storage = get_storage_manager()
        try:
            # 不使用version_id，直接下载最新版本（避免版本不匹配问题）
            template_bytes = storage.download_bytes(
                path=template_to_use.minio_path,
                bucket=template_to_use.bucket,  # 使用模板存储的bucket
                version_id=None,  # 不使用version_id
                user=current_user.username,
                user_role=current_user.role,
                user_department=current_user.department
            )
            print(f"[DEBUG] 模板下载成功，大小: {len(template_bytes)} 字节")
        except Exception as e:
            print(f"[ERROR] 模板下载失败: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"模板下载失败: {str(e)}")
        
        # 步骤6: 使用DocumentExporter生成文档
        from src.core.exporter import DocumentExporter
        # DocumentMetadata 已在文件开头全局导入，不要在这里重复导入
        from pathlib import Path as PathLib
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = PathLib(temp_dir)
            print(f"[流程] 步骤6: 创建临时目录: {temp_path}")
            
            # 保存模板到临时文件
            template_path = temp_path / template_to_use.filename
            print(f"[DEBUG] 保存模板到临时文件: {template_path}")
            with open(template_path, 'wb') as f:
                f.write(template_bytes)
            print(f"[DEBUG] 模板文件已保存，大小: {template_path.stat().st_size} 字节，存在: {template_path.exists()}")
            
            # 保存数据到临时文件（用于调试，但实际使用data_dict）
            data_path = temp_path / data_filename
            with open(data_path, 'wb') as f:
                f.write(file_content)
            
            # 初始化导出器（需要配置路径）
            project_root = backend_root.parent  # final_work2
            config_path = project_root / "config" / "config.yaml"
            print(f"[DEBUG] 初始化DocumentExporter，配置路径: {config_path}, 存在: {config_path.exists()}")
            
            exporter = DocumentExporter(
                config_path=config_path if config_path.exists() else None,
                enable_storage=False  # 禁用自动存储，我们手动上传到MinIO
            )
            print(f"[DEBUG] DocumentExporter初始化成功")
            print(f"[流程] 最终配置: 数据格式={data_file_format}, 模板格式={template_to_use.format_type}, 输出格式={final_output_format}")
            
            # 验证数据格式
            print(f"[DEBUG] 数据字典验证:")
            print(f"[DEBUG]   - 类型: {type(data_dict)}")
            print(f"[DEBUG]   - 键: {list(data_dict.keys())}")
            if 'tables' in data_dict:
                print(f"[DEBUG]   - tables类型: {type(data_dict['tables'])}")
                if isinstance(data_dict['tables'], dict):
                    print(f"[DEBUG]   - tables键: {list(data_dict['tables'].keys())}")
                    for table_name, table_data in list(data_dict['tables'].items())[:2]:  # 只打印前2个
                        print(f"[DEBUG]   - {table_name}: 类型={type(table_data)}, 长度={len(table_data) if isinstance(table_data, list) else 'N/A'}")
            
            # 处理水印图片（如果指定了watermark_image_id）
            watermark_image_path = None
            if enable_watermark and watermark_image_id:
                try:
                    # 从数据库获取图片信息
                    watermark_doc = db.query(DocumentMetadata).filter(
                        DocumentMetadata.id == watermark_image_id,
                        DocumentMetadata.category == 'images'
                    ).first()
                    if watermark_doc:
                        # 从MinIO下载图片（不使用version_id）
                        watermark_image_bytes = storage.download_bytes(
                            path=watermark_doc.minio_path,
                            bucket=watermark_doc.bucket,
                            version_id=None,  # 不使用version_id
                            user=current_user.username,
                            user_role=current_user.role,
                            user_department=current_user.department
                        )
                        # 保存到临时文件
                        watermark_image_path = temp_path / f"watermark_{watermark_image_id}.{PathLib(watermark_doc.filename).suffix}"
                        with open(watermark_image_path, 'wb') as f:
                            f.write(watermark_image_bytes)
                        print(f"[DEBUG] 水印图片已下载: {watermark_image_path}")
                    else:
                        print(f"[WARNING] 水印图片ID {watermark_image_id} 不存在，将使用文本水印")
                except Exception as e:
                    print(f"[WARNING] 下载水印图片失败: {e}，将使用文本水印")
                    import traceback
                    traceback.print_exc()
            
            # 生成文档（直接使用临时模板文件路径，而不是模板名称）
            # 注意：传递数据字典而不是文件路径，确保数据正确填充到模板
            print(f"[DEBUG] 开始调用exporter.export_document()")
            print(f"[DEBUG]   - template_path: {template_path}")
            print(f"[DEBUG]   - output_format: {final_output_format}")
            print(f"[DEBUG]   - data_dict keys: {list(data_dict.keys())}")
            print(f"[DEBUG]   - data_dict title: {data_dict.get('title', 'N/A')}")
            print(f"[DEBUG]   - data_dict tables keys: {list(data_dict.get('tables', {}).keys()) if isinstance(data_dict.get('tables'), dict) else 'N/A'}")
            if isinstance(data_dict.get('tables'), dict):
                for table_name, table_data in data_dict['tables'].items():
                    if isinstance(table_data, list):
                        print(f"[DEBUG]   - table '{table_name}': {len(table_data)} 行")
                    else:
                        print(f"[DEBUG]   - table '{table_name}': 类型={type(table_data)}")
            
            # 调试：打印水印参数
            print(f"[DEBUG] 水印参数: enable_watermark={enable_watermark}, watermark_text='{watermark_text}', watermark_image_path={watermark_image_path}")
            
            try:
                result = exporter.export_document(
                    data=data_dict,  # 直接传递解析后的数据字典，而不是文件路径
                    template_name=None,  # 不通过模板管理器加载，直接使用临时文件
                    output_format=final_output_format,
                    password=pdf_password if enable_encryption and final_output_format == 'pdf' else None,  # 只对PDF格式启用加密
                    auto_store=False,  # 禁用自动存储，我们手动上传
                    metadata={
                        "author": current_user.username,
                        "department": current_user.department,
                        "template_id": template_id,
                        "template_name": template.template_name
                    },
                    category="generated_documents",
                    template_path=str(template_path),  # 直接传递模板路径
                    watermark=enable_watermark,  # 是否添加水印
                    watermark_text=watermark_text or "内部使用，禁止外传",  # 水印文本（确保有默认值）
                    watermark_image_path=str(watermark_image_path) if watermark_image_path else None,  # 水印图片路径
                    restrict_edit=restrict_edit,  # 是否限制编辑（仅Word）
                    restrict_edit_password=restrict_edit_password  # 限制编辑密码
                )
                print(f"[DEBUG] exporter.export_document()调用完成，状态: {result.status if hasattr(result, 'status') else 'N/A'}")
            except Exception as e:
                print(f"[ERROR] exporter.export_document()调用失败: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            if result.status == 'success':
                # 从结果中获取文档信息
                generated_file = PathLib(result.result_file)
                
                if generated_file.exists():
                    # 读取生成的文件
                    with open(generated_file, 'rb') as f:
                        doc_content = f.read()
                    
                    # 上传到MinIO
                    doc_filename = generated_file.name
                    # 确定格式类型（使用最终确定的输出格式）
                    format_type = final_output_format  # pdf/word/html
                    
                    # 确定分类：与模板或数据文件一致
                    target_category = template.category or doc.category if 'doc' in locals() else template.category or "未分类"
                    if not target_category or target_category == 'generated_documents':
                        target_category = "未分类"
                    
                    # 上传到MinIO（使用新的存储逻辑：按格式类型分开存储，使用单独的桶）
                    upload_result = storage.upload_bytes(
                        data=doc_content,
                        filename=doc_filename,
                        category=target_category,  # 使用同步后的分类
                        content_type=get_content_type(doc_filename),
                        format_type=format_type,  # 传递格式类型，用于路径构建
                        metadata={
                            "author": current_user.username,
                            "department": current_user.department,
                            "template_id": template_id,  # 直接传递整数，不要转换为字符串
                            "template_name": template.template_name,
                            "description": f"由模板 '{template.template_name}' 生成",  # 更清晰的描述
                            "is_masked": enable_masking  # 记录是否脱敏
                        }
                    )
                    
                    return {
                        "success": True,
                        "message": "文档生成成功",
                        "document_id": upload_result.get('doc_id'),
                        "filename": doc_filename,
                        "minio_path": upload_result['path']
                    }
                else:
                    raise HTTPException(status_code=500, detail="生成的文档文件不存在")
            else:
                # 改进错误信息提取逻辑
                error_msg = '生成失败'
                error_details = []
                problems_file_content = None
                
                # 读取错误日志文件内容
                if hasattr(result, 'problems_file') and result.problems_file:
                    try:
                        problems_path = PathLib(result.problems_file)
                        if problems_path.exists():
                            problems_file_content = problems_path.read_text(encoding='utf-8')
                            print(f"[DEBUG] 已读取错误日志文件: {result.problems_file}")
                    except Exception as e:
                        print(f"[WARN] 无法读取错误日志文件: {e}")
                
                if hasattr(result, 'metadata') and result.metadata:
                    # 优先使用 metadata 中的 error 字段
                    if 'error' in result.metadata:
                        error_msg = result.metadata.get('error', '未知错误')
                    elif 'error_summary' in result.metadata:
                        error_msg = result.metadata.get('error_summary', '未知错误')
                    else:
                        # 如果没有 error 字段，尝试从其他字段推断错误原因
                        if 'errors_count' in result.metadata and result.metadata.get('errors_count', 0) > 0:
                            error_msg = f"验证失败：发现 {result.metadata.get('errors_count', 0)} 个错误"
                        elif 'problems_count' in result.metadata and result.metadata.get('problems_count', 0) > 0:
                            error_msg = f"验证失败：发现 {result.metadata.get('problems_count', 0)} 个问题"
                        elif 'style_reduction_score' in result.metadata:
                            score = result.metadata.get('style_reduction_score', 0)
                            if score < 0.95:
                                error_msg = f"样式还原度不足：{score:.2%}（要求≥95%）"
                            else:
                                error_msg = '未知错误'
                        else:
                            error_msg = '未知错误'
                    
                    # 添加额外的调试信息
                    if 'generation_time' in result.metadata:
                        error_details.append(f"生成耗时: {result.metadata.get('generation_time', 0):.2f}秒")
                    if 'file_size' in result.metadata:
                        file_size = result.metadata.get('file_size', 0)
                        error_details.append(f"文件大小: {file_size}字节")
                    if 'page_count' in result.metadata:
                        error_details.append(f"页数: {result.metadata.get('page_count', 0)}")
                
                elif hasattr(result, 'status'):
                    error_msg = f"文档生成失败，状态: {result.status}"
                
                # 如果有额外信息，添加到错误消息中
                if error_details:
                    error_msg = f"{error_msg} ({', '.join(error_details)})"
                
                # 安全处理错误消息，避免GBK编码错误
                try:
                    safe_error_msg = str(error_msg).encode('utf-8').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    safe_error_msg = str(error_msg).encode('ascii', 'ignore').decode('ascii')
                
                # 记录详细错误信息到控制台（用于调试）
                import traceback
                print(f"[ERROR] ========== 文档生成失败 ==========")
                print(f"[ERROR] 错误消息: {safe_error_msg}")
                print(f"[ERROR] result.status: {result.status if hasattr(result, 'status') else 'N/A'}")
                if hasattr(result, 'metadata') and result.metadata:
                    print(f"[ERROR] metadata 完整内容: {result.metadata}")
                    print(f"[ERROR] metadata 键列表: {list(result.metadata.keys())}")
                    if 'error' in result.metadata:
                        error_detail = result.metadata.get('error')
                        print(f"[ERROR] metadata['error']: {error_detail}")
                        # 如果 error 是长文本，只打印前500字符
                        if isinstance(error_detail, str) and len(error_detail) > 500:
                            print(f"[ERROR] metadata['error'] (前500字符): {error_detail[:500]}")
                    if 'error_summary' in result.metadata:
                        print(f"[ERROR] metadata['error_summary']: {result.metadata.get('error_summary')}")
                    if 'problems_count' in result.metadata:
                        print(f"[ERROR] metadata['problems_count']: {result.metadata.get('problems_count', 0)}")
                    if 'errors_count' in result.metadata:
                        print(f"[ERROR] metadata['errors_count']: {result.metadata.get('errors_count', 0)}")
                    if 'style_reduction_score' in result.metadata:
                        print(f"[ERROR] metadata['style_reduction_score']: {result.metadata.get('style_reduction_score', 0)}")
                else:
                    print(f"[ERROR] result.metadata 不存在或为空")
                # 打印 result 对象的其他属性
                if hasattr(result, 'problems_file') and result.problems_file:
                    print(f"[ERROR] problems_file: {result.problems_file}")
                    if problems_file_content:
                        print(f"[ERROR] problems_file 内容 (前1000字符): {problems_file_content[:1000]}")
                print(f"[ERROR] ====================================")
                
                # 返回详细的错误信息，包括错误日志内容
                # 使用JSONResponse返回详细错误信息
                from fastapi.responses import JSONResponse
                error_response = {
                    "detail": safe_error_msg,
                    "error_log": problems_file_content,
                    "problems_file": str(result.problems_file) if hasattr(result, 'problems_file') and result.problems_file else None,
                    "metadata": result.metadata if hasattr(result, 'metadata') else None
                }
                
                return JSONResponse(
                    status_code=500,
                    content=error_response
                )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        import sys
        # 安全处理错误消息，避免GBK编码错误
        try:
            error_msg = str(e)
            # 尝试编码为UTF-8，如果失败则使用ASCII安全版本
            error_msg.encode('utf-8')
        except UnicodeEncodeError:
            # 如果包含无法编码的字符，使用ASCII安全版本
            error_msg = str(e).encode('ascii', 'ignore').decode('ascii')
        except:
            error_msg = "生成文档失败（编码错误）"
        
        # 打印错误到控制台（使用UTF-8编码）
        try:
            traceback.print_exc()
        except UnicodeEncodeError:
            # 如果traceback包含无法编码的字符，使用文件输出
            import io
            error_buffer = io.StringIO()
            traceback.print_exc(file=error_buffer)
            error_buffer.seek(0)
            safe_traceback = error_buffer.read().encode('ascii', 'ignore').decode('ascii')
            print(safe_traceback, file=sys.stderr)
        
        raise HTTPException(status_code=500, detail=error_msg)


# ==================== 访问日志 API ====================

@app.get("/api/logs")
async def get_access_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取访问日志"""
    try:
        from src.security.access_logger import AccessLog
        
        query = db.query(AccessLog)
        
        if user:
            query = query.filter(AccessLog.user == user)
        
        if action:
            query = query.filter(AccessLog.action == action)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(AccessLog.created_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                query = query.filter(AccessLog.created_at <= date_to_obj)
            except ValueError:
                pass
        
        total = query.count()
        offset = (page - 1) * page_size
        logs = query.order_by(AccessLog.created_at.desc()).offset(offset).limit(page_size).all()
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "action": log.action,
                "user": log.user,
                "filename": log.object_path.split('/')[-1] if log.object_path else "-",
                "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "-"
            })
        
        return {
            "logs": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询访问日志失败: {str(e)}")


@app.delete("/api/logs/clear")
async def clear_access_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清空所有访问日志（仅管理员）"""
    # 权限检查：只有admin可以清空访问日志
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限执行此操作，仅管理员可清空访问日志")
    
    try:
        from src.security.access_logger import AccessLog
        
        storage = get_storage_manager()
        
        # 1. 删除MySQL中的所有访问日志记录
        deleted_count = db.query(AccessLog).delete()
        
        # 2. 删除MinIO logs桶中的所有文件
        minio_deleted = 0
        try:
            if storage.client.bucket_exists('logs'):
                objects = list(storage.client.list_objects('logs', recursive=True))
                for obj in objects:
                    try:
                        storage.client.remove_object('logs', obj.object_name)
                        minio_deleted += 1
                    except Exception as e:
                        print(f"删除MinIO日志文件失败 {obj.object_name}: {e}")
        except Exception as e:
            print(f"删除MinIO logs桶文件失败: {e}")
        
        db.commit()
        
        return {
            "success": True,
            "message": "访问日志清空成功",
            "mysql_deleted": deleted_count,
            "minio_deleted": minio_deleted
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清空访问日志失败: {str(e)}")


# ==================== 用户管理 API（仅管理员） ====================

@app.get("/api/users")
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户列表（仅管理员）"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限访问用户列表，仅管理员可查看")
    
    try:
        query = db.query(User)
        total = query.count()
        
        offset = (page - 1) * page_size
        users = query.order_by(User.id).offset(offset).limit(page_size).all()
        
        result = []
        for user in users:
            result.append({
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "department": user.department,
                "display_name": user.display_name or user.username
            })
        
        return {
            "users": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


# ==================== 一键清空所有数据 API ====================

@app.delete("/api/system/clear-all")
async def clear_all_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """一键清空所有数据（文件、模板、生成的文档、访问日志）
    
    删除内容：
    - 所有文件（documents表 + MinIO documents桶中的文件）
    - 所有模板（templates表 + MinIO templates桶中的文件）
    - 所有生成的文档（generated_documents表 + MinIO generated-documents桶中的文件）
    - 所有访问日志（access_logs表 + MinIO logs桶中的文件）
    
    保留内容：
    - 所有MinIO桶（不删除桶本身）
    - 用户表（users表）
    """
    # 权限检查：只有admin可以清空所有数据
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限执行此操作，仅管理员可清空所有数据")
    
    try:
        from src.storage.database import GeneratedDocumentMetadata
        from src.security.access_logger import AccessLog
        
        storage = get_storage_manager()
        access_logger = get_access_logger()
        
        stats = {
            'documents': {'mysql': 0, 'minio': 0},
            'templates': {'mysql': 0, 'minio': 0},
            'generated_documents': {'mysql': 0, 'minio': 0},
            'access_logs': {'mysql': 0, 'minio': 0}
        }
        
        # 1. 删除所有文件（documents表）- 不依赖状态，删除所有记录
        print("[清空] 开始删除所有文件...")
        all_docs = db.query(DocumentMetadata).all()
        stats['documents']['mysql'] = len(all_docs)
        
        for doc in all_docs:
            try:
                if doc.minio_path and doc.bucket:
                    storage.client.remove_object(doc.bucket, doc.minio_path)
                    stats['documents']['minio'] += 1
            except Exception as e:
                print(f"删除MinIO文件失败 {doc.minio_path}: {e}")
        
        deleted_docs = db.query(DocumentMetadata).delete()
        db.commit()
        stats['documents']['mysql'] = deleted_docs
        
        # 2. 删除所有模板（templates表）
        print("[清空] 开始删除所有模板...")
        all_templates = db.query(TemplateMetadata).all()
        stats['templates']['mysql'] = len(all_templates)
        
        for tpl in all_templates:
            try:
                if tpl.minio_path and tpl.bucket:
                    storage.client.remove_object(tpl.bucket, tpl.minio_path)
                    stats['templates']['minio'] += 1
            except Exception as e:
                print(f"删除MinIO模板失败 {tpl.minio_path}: {e}")
        
        deleted_templates = db.query(TemplateMetadata).delete()
        db.commit()
        stats['templates']['mysql'] = deleted_templates
        
        # 3. 删除所有生成的文档（generated_documents表）
        print("[清空] 开始删除所有生成的文档...")
        all_gen_docs = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.status == 'active').all()
        stats['generated_documents']['mysql'] = len(all_gen_docs)
        
        for gen_doc in all_gen_docs:
            try:
                if gen_doc.minio_path and gen_doc.bucket:
                    storage.client.remove_object(gen_doc.bucket, gen_doc.minio_path)
                    stats['generated_documents']['minio'] += 1
            except Exception as e:
                print(f"删除MinIO生成的文档失败 {gen_doc.minio_path}: {e}")
        
        deleted_gen_docs = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.status == 'active').delete()
        db.commit()
        stats['generated_documents']['mysql'] = deleted_gen_docs
        
        # 4. 记录清空操作日志（在删除日志之前记录）
        try:
            access_logger.log(
                action='clear_all_data',
                object_path='all',
                user=current_user.username,
                bucket='system',
                user_role=current_user.role,
                user_department=current_user.department,
                details={
                    'stats': stats,
                    'total_deleted': {
                        'mysql': sum(s['mysql'] for s in stats.values()),
                        'minio': sum(s['minio'] for s in stats.values())
                    }
                }
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        # 5. 删除所有访问日志（access_logs表）
        print("[清空] 开始删除所有访问日志...")
        all_logs = db.query(AccessLog).all()
        stats['access_logs']['mysql'] = len(all_logs)
        
        # 删除MinIO logs桶中的所有文件
        try:
            if storage.client.bucket_exists('logs'):
                objects = list(storage.client.list_objects('logs', recursive=True))
                for obj in objects:
                    try:
                        storage.client.remove_object('logs', obj.object_name)
                        stats['access_logs']['minio'] += 1
                    except Exception as e:
                        print(f"删除MinIO日志文件失败 {obj.object_name}: {e}")
        except Exception as e:
            print(f"删除MinIO logs桶文件失败: {e}")
        
        deleted_logs = db.query(AccessLog).delete()
        db.commit()
        stats['access_logs']['mysql'] = deleted_logs
        
        total_mysql = sum(s['mysql'] for s in stats.values())
        total_minio = sum(s['minio'] for s in stats.values())
        
        return {
            "success": True,
            "message": f"清空完成：已删除 {total_mysql} 条MySQL记录，{total_minio} 个MinIO文件",
            "stats": stats,
            "total": {
                "mysql": total_mysql,
                "minio": total_minio
            }
        }
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"清空所有数据失败: {str(e)}")


# ==================== 同步检查 API ====================

@app.get("/api/system/check-config")
async def check_config(
    current_user: User = Depends(get_current_user),
):
    """检查后端配置（MinIO和MySQL）- 仅管理员"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="无权限检查配置，仅管理员可查看")
    
    result = {
        'mysql': {'status': 'unknown', 'message': ''},
        'minio': {'status': 'unknown', 'message': ''},
        'overall': {'status': 'unknown', 'message': ''}
    }
    
    try:
        from src.utils.file_utils import load_config
        from pathlib import Path
        
        # 加载配置文件
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        if not config_path.exists():
            config_path = Path(__file__).parent / "config" / "config.yaml"
        
        config = load_config(str(config_path))
        
        # 检查MySQL配置
        mysql_config = config.get('mysql', {})
        if mysql_config:
            try:
                from src.storage.database import get_db_session
                from sqlalchemy import text
                # 尝试连接数据库
                with get_db_session(config_path=str(config_path)) as test_db:
                    test_db.execute(text("SELECT 1"))
                result['mysql'] = {
                    'status': 'ok',
                    'message': 'MySQL连接正常',
                    'config': {
                        'host': mysql_config.get('host', 'N/A'),
                        'port': mysql_config.get('port', 'N/A'),
                        'database': mysql_config.get('database', 'N/A'),
                        'user': mysql_config.get('user', 'N/A')
                    }
                }
            except Exception as e:
                result['mysql'] = {
                    'status': 'error',
                    'message': f'MySQL连接失败: {str(e)}',
                    'config': {
                        'host': mysql_config.get('host', 'N/A'),
                        'port': mysql_config.get('port', 'N/A'),
                        'database': mysql_config.get('database', 'N/A')
                    }
                }
        else:
            result['mysql'] = {'status': 'error', 'message': 'MySQL配置不存在'}
        
        # 检查MinIO配置
        minio_config = config.get('minio', {})
        if minio_config:
            try:
                from src.storage.storage_manager import StorageManager
                storage = StorageManager(config_path=str(config_path))
                # 尝试列出bucket（简单连接测试）
                buckets = storage.client.list_buckets()
                result['minio'] = {
                    'status': 'ok',
                    'message': f'MinIO连接正常，找到{len(buckets)}个桶',
                    'config': {
                        'endpoint': minio_config.get('endpoint', 'N/A'),
                        'buckets': list(minio_config.get('buckets', {}).values())
                    }
                }
            except Exception as e:
                result['minio'] = {
                    'status': 'error',
                    'message': f'MinIO连接失败: {str(e)}',
                    'config': {
                        'endpoint': minio_config.get('endpoint', 'N/A')
                    }
                }
        else:
            result['minio'] = {'status': 'error', 'message': 'MinIO配置不存在'}
        
        # 总体状态
        if result['mysql']['status'] == 'ok' and result['minio']['status'] == 'ok':
            result['overall'] = {'status': 'ok', 'message': '所有配置检查通过'}
        elif result['mysql']['status'] == 'error' and result['minio']['status'] == 'error':
            result['overall'] = {'status': 'error', 'message': 'MySQL和MinIO配置都有问题'}
        else:
            result['overall'] = {'status': 'warning', 'message': '部分配置有问题'}
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置检查失败: {str(e)}")


@app.get("/api/system/check-sync")
async def check_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查数据库同步情况（MySQL vs MinIO）
    
    检查内容：
    - 文件（documents表 vs MinIO documents桶）
    - 模板（templates表 vs MinIO templates桶）
    - 生成的文档（generated_documents表 vs MinIO generated-documents桶）
    """
    try:
        from src.storage.database import GeneratedDocumentMetadata
        from src.storage.minio_client import MinioClient
        from src.storage.utils import load_config
        from pathlib import Path
        
        storage = get_storage_manager()
        config_path = str(backend_root / "config" / "config.yaml")
        minio_client = MinioClient(config_path)
        
        sync_status = {
            'is_synced': True,
            'details': {
                'documents': {'synced': True, 'mysql_only': [], 'minio_only': []},
                'templates': {'synced': True, 'mysql_only': [], 'minio_only': []},
                'generated_documents': {'synced': True, 'mysql_only': [], 'minio_only': []}
            },
            'summary': {
                'documents': {'mysql_count': 0, 'minio_count': 0, 'synced_count': 0},
                'templates': {'mysql_count': 0, 'minio_count': 0, 'synced_count': 0},
                'generated_documents': {'mysql_count': 0, 'minio_count': 0, 'synced_count': 0}
            }
        }
        
        # 1. 检查文件同步情况
        print("[同步检查] 检查文件同步情况...")
        all_docs = db.query(DocumentMetadata).filter(DocumentMetadata.status == 'active').all()
        mysql_doc_paths = {doc.minio_path: {'id': doc.id, 'filename': doc.filename, 'bucket': doc.bucket} 
                          for doc in all_docs if doc.minio_path}
        sync_status['summary']['documents']['mysql_count'] = len(all_docs)
        
        # 获取MinIO中的文件
        if minio_client.client.bucket_exists('documents'):
            minio_objects = list(minio_client.client.list_objects('documents', recursive=True))
            minio_doc_paths = {obj.object_name for obj in minio_objects}
            sync_status['summary']['documents']['minio_count'] = len(minio_doc_paths)
            
            mysql_paths_set = set(mysql_doc_paths.keys())
            synced_paths = mysql_paths_set & minio_doc_paths
            mysql_only = mysql_paths_set - minio_doc_paths
            minio_only = minio_doc_paths - mysql_paths_set
            
            sync_status['summary']['documents']['synced_count'] = len(synced_paths)
            
            if mysql_only or minio_only:
                sync_status['is_synced'] = False
                sync_status['details']['documents']['synced'] = False
                sync_status['details']['documents']['mysql_only'] = [
                    {'path': path, 'id': info['id'], 'filename': info['filename']} 
                    for path, info in mysql_doc_paths.items() if path in mysql_only
                ]
                sync_status['details']['documents']['minio_only'] = [
                    {'path': path} for path in minio_only
                ]
        
        # 2. 检查模板同步情况
        print("[同步检查] 检查模板同步情况...")
        all_templates = db.query(TemplateMetadata).filter(TemplateMetadata.is_latest == True).all()
        mysql_template_paths = {tpl.minio_path: {'id': tpl.id, 'template_name': tpl.template_name, 'bucket': tpl.bucket} 
                               for tpl in all_templates if tpl.minio_path}
        sync_status['summary']['templates']['mysql_count'] = len(all_templates)
        
        # 获取MinIO中的模板文件
        if minio_client.client.bucket_exists('templates'):
            minio_objects = list(minio_client.client.list_objects('templates', recursive=True))
            minio_template_paths = {obj.object_name for obj in minio_objects}
            sync_status['summary']['templates']['minio_count'] = len(minio_template_paths)
            
            mysql_paths_set = set(mysql_template_paths.keys())
            synced_paths = mysql_paths_set & minio_template_paths
            mysql_only = mysql_paths_set - minio_template_paths
            minio_only = minio_template_paths - mysql_paths_set
            
            sync_status['summary']['templates']['synced_count'] = len(synced_paths)
            
            if mysql_only or minio_only:
                sync_status['is_synced'] = False
                sync_status['details']['templates']['synced'] = False
                sync_status['details']['templates']['mysql_only'] = [
                    {'path': path, 'id': info['id'], 'template_name': info['template_name']} 
                    for path, info in mysql_template_paths.items() if path in mysql_only
                ]
                sync_status['details']['templates']['minio_only'] = [
                    {'path': path} for path in minio_only
                ]
        
        # 3. 检查生成的文档同步情况
        print("[同步检查] 检查生成的文档同步情况...")
        all_gen_docs = db.query(GeneratedDocumentMetadata).filter(GeneratedDocumentMetadata.status == 'active').all()
        mysql_gen_doc_paths = {doc.minio_path: {'id': doc.id, 'filename': doc.filename, 'bucket': doc.bucket} 
                              for doc in all_gen_docs if doc.minio_path}
        sync_status['summary']['generated_documents']['mysql_count'] = len(all_gen_docs)
        
        # 获取MinIO中的生成的文档文件
        if minio_client.client.bucket_exists('generated-documents'):
            minio_objects = list(minio_client.client.list_objects('generated-documents', recursive=True))
            minio_gen_doc_paths = {obj.object_name for obj in minio_objects}
            sync_status['summary']['generated_documents']['minio_count'] = len(minio_gen_doc_paths)
            
            mysql_paths_set = set(mysql_gen_doc_paths.keys())
            synced_paths = mysql_paths_set & minio_gen_doc_paths
            mysql_only = mysql_paths_set - minio_gen_doc_paths
            minio_only = minio_gen_doc_paths - mysql_paths_set
            
            sync_status['summary']['generated_documents']['synced_count'] = len(synced_paths)
            
            if mysql_only or minio_only:
                sync_status['is_synced'] = False
                sync_status['details']['generated_documents']['synced'] = False
                sync_status['details']['generated_documents']['mysql_only'] = [
                    {'path': path, 'id': info['id'], 'filename': info['filename']} 
                    for path, info in mysql_gen_doc_paths.items() if path in mysql_only
                ]
                sync_status['details']['generated_documents']['minio_only'] = [
                    {'path': path} for path in minio_only
                ]
        
        return sync_status
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"检查同步情况失败: {str(e)}")


# ==================== 图片管理 API ====================

@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    alt: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    file_tags: Optional[str] = Form(None),  # JSON格式的关联文件ID列表
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传图片（存MinIO，元数据存MySQL）"""
    try:
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式，支持的格式: {', '.join(allowed_extensions)}")
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 解析标签
        tags_dict = {}
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            for i, tag in enumerate(tag_list):
                tags_dict[f"tag_{i}"] = tag
        
        # 获取内容类型
        content_type = get_content_type(file.filename)
        
        # 上传到MinIO（使用 images 分类）
        storage = get_storage_manager()
        metadata = {
            "author": current_user.username,
            "department": current_user.department,
            "user_role": current_user.role,
            "description": description or "",
            "alt": alt or file.filename,
        }
        
        result = storage.upload_bytes(
            data=file_content,
            filename=file.filename,
            category="images",  # 使用 images 分类
            content_type=content_type,
            metadata=metadata,
            tags=tags_dict
        )
        
        # 处理关联文件ID列表
        file_tags_list = []
        if file_tags:
            try:
                import json
                file_tags_list = json.loads(file_tags)
                if not isinstance(file_tags_list, list):
                    file_tags_list = []
            except:
                file_tags_list = []
        
        # 如果有关联文件，更新数据库记录的file_tags字段
        if file_tags_list and result.get('doc_id'):
            from src.storage.database import DocumentMetadata
            doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == result.get('doc_id')).first()
            if doc:
                doc.file_tags = file_tags_list
                db.commit()
        
        # 从统一配置文件获取数据库信息
        config = load_config(str(backend_root / "config" / "config.yaml"))
        mysql_db = config.get('mysql', {}).get('database', 'unknown')
        
        return {
            "success": True,
            "message": "图片上传成功",
            "filename": file.filename,
            "alt": alt or file.filename,
            "minio_bucket": storage.buckets['images'],
            "minio_path": result['path'],
            "url": f"/api/images/{result.get('doc_id')}/download",  # 提供下载URL
            "mysql_id": result.get('doc_id'),
            "mysql_info": {
                "table": "documents",
                "database": mysql_db,
                "record_id": result.get('doc_id')
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片上传失败: {str(e)}")


@app.get("/api/images")
async def get_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取图片列表（只返回图片类型的文件）"""
    try:
        # 查询图片类型的文件
        query = db.query(DocumentMetadata).filter(
            DocumentMetadata.status == 'active',
            DocumentMetadata.category == 'images'
        )
        
        # 关键词搜索（文件名）
        if keyword:
            query = query.filter(
                DocumentMetadata.filename.like(f"%{keyword}%")
            )
        
        # 总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        docs = query.order_by(DocumentMetadata.created_at.desc()).offset(offset).limit(page_size).all()
        
        # 转换为响应格式
        images = []
        for doc in docs:
            tags_list = []
            if doc.tags:
                if isinstance(doc.tags, dict):
                    tags_list = list(doc.tags.values())
                elif isinstance(doc.tags, list):
                    tags_list = doc.tags
            
            images.append({
                "id": doc.id,
                "filename": doc.filename,
                "alt": doc.description or doc.filename,  # 使用 description 作为 alt
                "url": f"/api/images/{doc.id}/download",
                "upload_time": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else "-",
                "tags": tags_list,
                "uploader": doc.created_by or "系统",
                "file_size": doc.file_size,
                "description": doc.description
            })
        
        return {
            "images": images,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询图片列表失败: {str(e)}")


@app.get("/api/images/{image_id}/download")
async def download_image(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载图片"""
    doc = db.query(DocumentMetadata).filter(
        DocumentMetadata.id == image_id,
        DocumentMetadata.category == 'images'
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    try:
        storage = get_storage_manager()
        file_data = storage.download_bytes(
            path=doc.minio_path,
            bucket=doc.bucket,
            version_id=doc.version_id,
            user=current_user.username,
            user_role=current_user.role,
            user_department=current_user.department
        )
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=doc.content_type or "image/jpeg",
            headers={
                "Content-Disposition": f'inline; filename="{doc.filename}"'  # inline 用于在浏览器中显示
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载图片失败: {str(e)}")


# ==================== 系统管理 ====================

@app.post("/api/system/restart")
async def restart_backend(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    重启后端服务器
    需要管理员权限
    """
    # 验证token
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        user_role = payload.get("role", "user")
        
        # 检查是否为管理员
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限"
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token已过期"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Token"
        )
    
    # 调用重启脚本
    import subprocess
    import platform
    
    backend_dir = Path(__file__).parent
    restart_script = backend_dir / "restart_backend.ps1"
    
    try:
        if platform.system() == "Windows":
            # Windows: 使用PowerShell执行脚本
            process = subprocess.Popen(
                ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(restart_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(backend_dir),
                creationflags=subprocess.CREATE_NO_WINDOW,  # 不显示窗口
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            # 等待一小段时间，检查是否有立即错误
            import time
            time.sleep(0.5)
            if process.poll() is not None:
                # 进程已结束，可能有错误
                stdout, stderr = process.communicate()
                error_msg = stderr.strip() if stderr else stdout.strip()
                if error_msg:
                    return {
                        "status": "error",
                        "message": f"重启脚本执行失败: {error_msg}"
                    }
            # 不等待进程完成，让它异步执行
            return {
                "status": "success",
                "message": "后端服务器正在重启，请稍候几秒后刷新页面"
            }
        else:
            # Linux/Mac: 使用bash脚本（如果需要）
            return {
                "status": "error",
                "message": "当前系统不支持自动重启，请手动重启后端"
            }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return {
            "status": "error",
            "message": f"重启失败: {str(e)}\n详细信息: {error_detail[:200]}"
        }


# ==================== 根路径 ====================

@app.get("/")
async def root():
    """根路径"""
    return {"message": "文件管理系统 API", "status": "running"}


if __name__ == "__main__":
    import uvicorn
    import sys
    import io
    
    # 设置标准输出和错误输出为UTF-8编码，避免GBK编码错误
    if sys.platform == 'win32':
        # Windows系统：设置控制台编码为UTF-8
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            # 如果reconfigure失败，使用包装器
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
