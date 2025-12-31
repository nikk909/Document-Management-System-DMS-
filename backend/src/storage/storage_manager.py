# -*- coding: utf-8 -*-
"""
=============================================================================
MinIO 统一存储管理器（混合架构：MinIO + SQLAlchemy）
=============================================================================

存储格式: {category}/{year}/{month}/{day}/{filename}
+ 文件存储: MinIO 对象存储
+ 元数据存储: MySQL（通过 SQLAlchemy）

使用方法:
    from src.storage.storage_manager import StorageManager
    
    storage = StorageManager()
    
    # 上传文档（文件存 MinIO，元数据存数据库）
    result = storage.upload(
        content="文档内容",
        filename="report.txt",
        category="reports",
        metadata={"department": "finance", "author": "Alice"},
        tags={"priority": "high", "confidential": "yes"}
    )
    
    # 按类型查询（从数据库查询）
    docs = storage.query_by_category("reports")
    
    # 按时间查询（从数据库查询）
    docs = storage.query_by_date(2025, 1)
    
    # 按标签查询（从数据库查询）
    docs = storage.query_by_tag("priority", "high")
    
    # 版本回退
    storage.rollback(path, version_id)
"""

import io
from datetime import datetime
from typing import List, Dict, Optional

from minio import Minio
from minio.commonconfig import ENABLED, Tags
from minio.versioningconfig import VersioningConfig

from .utils import load_config
from .metadata_manager import MetadataManager
from ..security.access_logger import AccessLogger


class StorageManager:
    """
    MinIO 统一存储管理器（混合架构）
    
    架构说明:
    - 文件存储: MinIO 对象存储
    - 元数据存储: MySQL（通过 SQLAlchemy）
    
    存储路径格式: {category}/{year}/{month}/{day}/{filename}
    支持: 类型分类、时间分类、标签分类、版本控制
    """
    
    # 预定义的文档分类
    CATEGORIES = ['reports', 'contracts', 'configs', 'notes', 'archives', 'templates', 'images']
    
    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket: str = None,
        secure: bool = None,
        auto_create: bool = True,
        config_path: str = None
    ):
        """
        初始化存储管理器
        
        参数:
            endpoint: MinIO 服务器地址（默认从配置文件读取）
            access_key: 访问密钥（默认从配置文件读取）
            secret_key: 秘密密钥（默认从配置文件读取）
            bucket: 存储桶名称（默认从配置文件读取，如果为None则根据category动态选择）
            secure: 是否使用 HTTPS（默认从配置文件读取）
            auto_create: 是否自动创建桶
            config_path: 配置文件路径
        """
        # 从配置文件加载默认值
        config = load_config(config_path)
        minio_config = config.get('minio', {})
        
        # 使用传入参数或配置文件中的值
        endpoint = endpoint or minio_config.get('endpoint', 'localhost:9000')
        access_key = access_key or minio_config.get('access_key', 'minioadmin')
        secret_key = secret_key or minio_config.get('secret_key', 'minioadmin')
        secure = secure if secure is not None else minio_config.get('secure', False)
        
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        # 加载桶配置
        buckets_config = minio_config.get('buckets', {})
        self.buckets = {
            'documents': buckets_config.get('documents', 'documents'),
            'templates': buckets_config.get('templates', 'templates'),
            'generated_documents': buckets_config.get('generated_documents', 'generated-documents'),
            'logs': buckets_config.get('logs', 'logs'),
            'images': buckets_config.get('images', 'images'),
        }
        
        # 默认桶（用于向后兼容）
        self.bucket = bucket or minio_config.get('default_bucket', 'documents')
        self.config_path = config_path  # 保存配置路径，用于 MetadataManager
        
        # 初始化访问日志记录器
        self.access_logger = AccessLogger(session=None)
        
        if auto_create:
            self._ensure_all_buckets()
    
    def _ensure_all_buckets(self):
        """确保所有桶存在并启用版本控制"""
        for bucket_name in self.buckets.values():
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                self.client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
        
        # 也确保默认桶存在
        if self.bucket and not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            self.client.set_bucket_versioning(self.bucket, VersioningConfig(ENABLED))
    
    def _get_bucket_for_category(self, category: str) -> str:
        """
        根据分类获取对应的桶名称
        
        参数:
            category: 文件分类（documents, templates, generated_documents, logs, images等）
        
        返回:
            桶名称
        """
        # 模板相关
        if category == 'templates' or 'template' in category.lower():
            return self.buckets['templates']
        # 生成的文档相关
        elif category == 'generated_documents' or 'generated' in category.lower():
            return self.buckets['generated_documents']
        # 日志相关
        elif category == 'logs' or 'log' in category.lower() or category == 'access_logs':
            return self.buckets['logs']
        # 图片相关
        elif category == 'images' or 'image' in category.lower():
            return self.buckets['images']
        # 默认使用文档桶
        else:
            return self.buckets['documents']
    
    def _build_path(self, filename: str, category: str, date: datetime = None, format_type: str = None) -> str:
        """
        构建存储路径
        
        参数:
            filename: 文件名
            category: 分类
            date: 日期
            format_type: 格式类型（仅用于生成的文档，pdf/word/html）
        """
        if date is None:
            date = datetime.now()
        
        # 对于生成的文档，按格式类型分开存储
        if category == 'generated_documents' and format_type:
            return f"{format_type}/{date.year}/{date.month:02d}/{date.day:02d}/{filename}"
        else:
            return f"{category}/{date.year}/{date.month:02d}/{date.day:02d}/{filename}"
    
    # =========================================================================
    # 上传操作
    # =========================================================================
    
    def upload(
        self,
        content: str,
        filename: str,
        category: str,
        date: datetime = None,
        metadata: Dict = None,
        tags: Dict = None
    ) -> Dict:
        """
        上传文档（文件存 MinIO，元数据存数据库）
        
        参数:
            content: 文档内容（字符串）
            filename: 文件名
            category: 分类 (reports, contracts, configs, notes, archives)
            date: 日期，默认为当前日期
            metadata: 元数据字典 {"department": "...", "author": "..."}
            tags: 标签字典 {"priority": "high", "confidential": "yes"}
        
        返回:
            {"path": "...", "version_id": "...", "size": ..., "doc_id": ...}
        """
        if date is None:
            date = datetime.now()
        
        path = self._build_path(filename, category, date)
        data = content.encode('utf-8')
        
        # 处理 metadata：MinIO metadata 只支持 US-ASCII 字符
        safe_metadata = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, str):
                    try:
                        v.encode('ascii')
                        safe_metadata[k] = v
                    except UnicodeEncodeError:
                        # 非 ASCII 字符，跳过（存储在 SQL 中）
                        pass
                else:
                    safe_metadata[k] = str(v)
        
        # 处理 tags：MinIO tags 值也只支持 US-ASCII 字符
        minio_tags = None
        if tags:
            minio_tags = Tags(for_object=True)
            for k, v in tags.items():
                v_str = str(v)
                try:
                    v_str.encode('ascii')
                    minio_tags[k] = v_str
                except UnicodeEncodeError:
                    # 非 ASCII 字符，使用 URL 编码
                    import urllib.parse
                    encoded_value = urllib.parse.quote(v_str, safe='')
                    minio_tags[k] = encoded_value
        
        # 1. 上传文件到 MinIO
        result = self.client.put_object(
            bucket_name=self.bucket,
            object_name=path,
            data=io.BytesIO(data),
            length=len(data),
            content_type='text/plain',
            metadata=safe_metadata,  # 只包含 ASCII 字符
            tags=minio_tags
        )
        
        # 2. 保存元数据到数据库
        doc_date = date.strftime('%Y-%m')  # 格式：2024-05
        doc_id = None
        try:
            with MetadataManager() as mgr:
                doc = mgr.add_document(
                    filename=filename,
                    minio_path=path,
                    bucket=self.bucket,
                    department=metadata.get('department') if metadata else None,
                    author=metadata.get('author') if metadata else None,
                    doc_type=metadata.get('doc_type') if metadata else None,
                    doc_date=doc_date,
                    description=metadata.get('description') if metadata else None,
                    category=category,
                    tags=tags or {},
                    file_size=len(data),
                    content_type='text/plain',
                    version_id=result.version_id,
                    created_by=metadata.get('author') if metadata else None
                )
                # 在上下文内部获取 doc.id，避免 DetachedInstanceError
                doc_id = doc.id if doc else None
        except Exception as e:
            # 如果数据库操作失败，记录错误但不影响文件上传
            # 可以考虑回滚 MinIO 操作，但这里先记录错误
            print(f"警告：元数据保存失败（文件已上传到 MinIO）: {e}")
        
        # 3. 记录访问日志
        try:
            self.access_logger.log(
                action='upload',
                object_path=path,
                user=metadata.get('author', 'system') if metadata else 'system',
                bucket=self.bucket,
                user_role=metadata.get('user_role') if metadata else None,
                user_department=metadata.get('department') if metadata else None,
                details={
                    'filename': filename,
                    'category': category,
                    'file_size': len(data),
                    'version_id': result.version_id,
                    'doc_id': doc_id
                }
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return {
            'path': path,
            'version_id': result.version_id,
            'size': len(data),
            'category': category,
            'date': date.strftime('%Y-%m-%d'),
            'doc_id': doc_id  # 数据库文档 ID
        }
    
    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        category: str,
        content_type: str = 'application/octet-stream',
        date: datetime = None,
        metadata: Dict = None,
        tags: Dict = None,
        format_type: str = None
    ) -> Dict:
        """
        上传二进制数据（文件存 MinIO，元数据存数据库）
        
        参数:
            data: 二进制数据
            filename: 文件名
            category: 分类
            content_type: MIME 类型
            date: 日期
            metadata: 元数据字典（注意：MinIO metadata 只支持 US-ASCII 字符）
            tags: 标签字典（注意：MinIO tags 值只支持 US-ASCII 字符）
        
        返回:
            {"path": "...", "version_id": "...", "size": ..., "doc_id": ...}
        """
        if date is None:
            date = datetime.now()
        
        path = self._build_path(filename, category, date)
        
        # 处理 metadata：MinIO metadata 只支持 US-ASCII 字符
        safe_metadata = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, str):
                    try:
                        # 检查是否为 ASCII
                        v.encode('ascii')
                        safe_metadata[k] = v
                    except UnicodeEncodeError:
                        # 非 ASCII 字符，跳过（存储在 SQL 中）
                        pass
                else:
                    safe_metadata[k] = str(v)
        
        # 处理 tags：MinIO tags 值也只支持 US-ASCII 字符
        minio_tags = None
        if tags:
            minio_tags = Tags(for_object=True)
            for k, v in tags.items():
                v_str = str(v)
                try:
                    # 检查是否为 ASCII
                    v_str.encode('ascii')
                    minio_tags[k] = v_str
                except UnicodeEncodeError:
                    # 非 ASCII 字符，使用 URL 编码或只保留键
                    import urllib.parse
                    # 使用 URL 编码存储非 ASCII 字符
                    encoded_value = urllib.parse.quote(v_str, safe='')
                    minio_tags[k] = encoded_value
        
        # 根据category选择对应的桶
        bucket_name = self._get_bucket_for_category(category)
        
        # 1. 上传文件到 MinIO
        result = self.client.put_object(
            bucket_name=bucket_name,
            object_name=path,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
            metadata=safe_metadata,  # 只包含 ASCII 字符
            tags=minio_tags
        )
        
        # 2. 保存元数据到数据库
        doc_date = date.strftime('%Y-%m')
        doc_id = None
        try:
            # 如果是模板，跳过保存到documents表（模板应该通过TemplateMetadataManager保存到templates表）
            if category == 'templates' or 'template' in category.lower():
                # 模板的元数据应该由调用者通过TemplateMetadataManager保存，这里只上传文件到MinIO
                doc_id = None
            # 如果是生成的文档，使用 GeneratedDocumentMetadataManager
            elif (category == 'generated_documents' or format_type in ['pdf', 'word', 'html']) and format_type:
                from .metadata_manager import GeneratedDocumentMetadataManager
                with GeneratedDocumentMetadataManager() as mgr:
                    # 处理 template_id：可能是整数或字符串
                    template_id_value = 0
                    if metadata and metadata.get('template_id'):
                        template_id_raw = metadata.get('template_id')
                        try:
                            template_id_value = int(template_id_raw) if isinstance(template_id_raw, (int, str)) and str(template_id_raw).strip() else 0
                        except (ValueError, TypeError):
                            template_id_value = 0
                    
                    # 处理 template_name：确保不为空
                    template_name_value = metadata.get('template_name', '') if metadata else ''
                    if not template_name_value or template_name_value.strip() == '':
                        template_name_value = '未知模板'
                    
                    doc = mgr.add_generated_document(
                        filename=filename,
                        minio_path=path,
                        bucket=bucket_name,
                        format_type=format_type,
                        template_id=template_id_value,
                        template_name=template_name_value,
                        department=metadata.get('department') if metadata else None,
                        author=metadata.get('author') if metadata else None,
                        description=metadata.get('description') if metadata else None,
                        tags=tags or {},
                        file_size=len(data),
                        content_type=content_type,
                        version_id=result.version_id,
                        created_by=metadata.get('author') if metadata else None,
                        category=category,
                        is_masked=metadata.get('is_masked', False) if metadata else False
                    )
                    doc_id = doc.id if doc else None
            else:
                # 普通文档使用 MetadataManager
                with MetadataManager() as mgr:
                    doc = mgr.add_document(
                        filename=filename,
                        minio_path=path,
                        bucket=bucket_name,
                        department=metadata.get('department') if metadata else None,
                        author=metadata.get('author') if metadata else None,
                        doc_type=metadata.get('doc_type') if metadata else None,
                        doc_date=doc_date,
                        description=metadata.get('description') if metadata else None,
                        category=category,
                        tags=tags or {},
                        file_size=len(data),
                        content_type=content_type,
                        version_id=result.version_id,
                        created_by=metadata.get('author') if metadata else None
                    )
                    doc_id = doc.id if doc else None
        except Exception as e:
            print(f"警告：元数据保存失败（文件已上传到 MinIO）: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. 记录访问日志
        try:
            self.access_logger.log(
                action='upload',
                object_path=path,
                user=metadata.get('author', 'system') if metadata else 'system',
                bucket=self.bucket,
                user_role=metadata.get('user_role') if metadata else None,
                user_department=metadata.get('department') if metadata else None,
                details={
                    'filename': filename,
                    'category': category,
                    'file_size': len(data),
                    'version_id': result.version_id,
                    'doc_id': doc_id,
                    'content_type': content_type
                }
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return {
            'path': path,
            'version_id': result.version_id,
            'size': len(data),
            'doc_id': doc_id
        }
    
    # =========================================================================
    # 下载操作
    # =========================================================================
    
    def download(self, path: str, version_id: str = None, user: str = 'system',
                 user_role: str = None, user_department: str = None) -> str:
        """
        下载文档内容（字符串）
        
        参数:
            path: 文档路径
            version_id: 版本 ID（可选）
            user: 下载用户（用于日志记录）
            user_role: 用户角色
            user_department: 用户部门
        """
        response = self.client.get_object(self.bucket, path, version_id=version_id)
        content = response.read().decode('utf-8')
        response.close()
        response.release_conn()
        
        # 记录访问日志
        try:
            self.access_logger.log(
                action='download',
                object_path=path,
                user=user,
                bucket=self.bucket,
                user_role=user_role,
                user_department=user_department,
                details={'version_id': version_id}
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return content
    
    def download_bytes(self, path: str, bucket: str = None, version_id: str = None, user: str = 'system',
                      user_role: str = None, user_department: str = None) -> bytes:
        """
        下载二进制数据
        
        参数:
            path: 文档路径
            bucket: 桶名称（如果为None，则从数据库查询或使用默认桶）
            version_id: 版本 ID（可选）
            user: 下载用户（用于日志记录）
            user_role: 用户角色
            user_department: 用户部门
        """
        # 如果没有指定bucket，尝试从数据库查询或根据path推断
        if bucket is None:
            try:
                with MetadataManager() as mgr:
                    # 尝试从数据库查询（不指定bucket，查询所有）
                    doc = mgr.get_document_by_path(path, bucket=None)
                    if doc and doc.bucket:
                        bucket = doc.bucket
                    else:
                        # 根据path推断category，然后选择bucket
                        path_parts = path.split('/')
                        if path_parts:
                            category = path_parts[0]
                            bucket = self._get_bucket_for_category(category)
                        else:
                            bucket = self.bucket
            except Exception as e:
                print(f"无法从数据库获取bucket，根据path推断: {e}")
                # 根据path推断category
                path_parts = path.split('/')
                if path_parts:
                    category = path_parts[0]
                    bucket = self._get_bucket_for_category(category)
                else:
                    bucket = self.bucket
        
        response = self.client.get_object(bucket, path, version_id=version_id)
        data = response.read()
        response.close()
        response.release_conn()
        
        # 记录访问日志
        try:
            self.access_logger.log(
                action='download',
                object_path=path,
                user=user,
                bucket=bucket,
                user_role=user_role,
                user_department=user_department,
                details={'version_id': version_id, 'content_type': 'binary'}
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return data
    
    # =========================================================================
    # 查询操作
    # =========================================================================
    
    def query_by_category(self, category: str) -> List[str]:
        """
        按类型查询（从数据库查询）
        
        参数:
            category: 分类名称
        
        返回:
            List[str]: 文档路径列表（去重）
        """
        try:
            with MetadataManager() as mgr:
                docs = mgr.search_by_metadata(category=category, status='active')
                # 去重：使用 set 保持顺序
                seen = set()
                result = []
                for doc in docs:
                    if doc.minio_path not in seen:
                        seen.add(doc.minio_path)
                        result.append(doc.minio_path)
                return result
        except Exception as e:
            print(f"数据库查询失败，回退到 MinIO 查询: {e}")
            # 回退到 MinIO 查询
            objects = self.client.list_objects(self.bucket, prefix=f"{category}/", recursive=True)
            return [obj.object_name for obj in objects]
    
    def query_by_date(self, year: int, month: int = None, day: int = None) -> List[str]:
        """
        按日期查询（从数据库查询）
        
        参数:
            year: 年份
            month: 月份（可选）
            day: 日期（可选，暂不支持精确到天）
        
        返回:
            List[str]: 文档路径列表
        """
        try:
            with MetadataManager() as mgr:
                # 构建日期字符串
                if month:
                    doc_date = f"{year}-{month:02d}"
                    docs = mgr.search_by_metadata(doc_date=doc_date, status='active')
                    # 去重
                    seen = set()
                    results = []
                    for doc in docs:
                        if doc.minio_path not in seen:
                            seen.add(doc.minio_path)
                            results.append(doc.minio_path)
                    return results
                else:
                    # 如果只指定年份，查询所有该年份的文档
                    # 简化：直接查询所有活跃文档，然后过滤
                    all_docs = mgr.search_by_metadata(status='active')
                    seen = set()
                    results = []
                    for doc in all_docs:
                        if doc.doc_date and doc.doc_date.startswith(str(year)):
                            if doc.minio_path not in seen:
                                seen.add(doc.minio_path)
                                results.append(doc.minio_path)
                    return results
        except Exception as e:
            print(f"数据库查询失败，回退到 MinIO 查询: {e}")
            # 回退到 MinIO 查询
            results = []
            for cat in self.CATEGORIES:
                if day and month:
                    prefix = f"{cat}/{year}/{month:02d}/{day:02d}/"
                elif month:
                    prefix = f"{cat}/{year}/{month:02d}/"
                else:
                    prefix = f"{cat}/{year}/"
                
                objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
                results.extend([obj.object_name for obj in objects])
            return results
    
    def query_by_tag(self, tag_key: str, tag_value: str) -> List[str]:
        """
        按标签查询（从数据库查询）
        
        参数:
            tag_key: 标签键
            tag_value: 标签值
        
        返回:
            List[str]: 文档路径列表
        """
        try:
            with MetadataManager() as mgr:
                docs = mgr.search_by_tags({tag_key: tag_value})
                # 过滤掉已删除的文档并去重
                seen = set()
                results = []
                for doc in docs:
                    if doc.status == 'active' and doc.minio_path not in seen:
                        seen.add(doc.minio_path)
                        results.append(doc.minio_path)
                return results
        except Exception as e:
            print(f"数据库查询失败，回退到 MinIO 查询: {e}")
            # 回退到 MinIO 查询
            results = []
            objects = self.client.list_objects(self.bucket, recursive=True)
            
            for obj in objects:
                try:
                    tags = self.client.get_object_tags(self.bucket, obj.object_name)
                    if tags and tags.get(tag_key) == tag_value:
                        results.append(obj.object_name)
                except:
                    pass
            
            return results
    
    def search(
        self,
        category: str = None,
        year: int = None,
        month: int = None,
        tag_filters: Dict = None
    ) -> List[Dict]:
        """
        综合搜索（从数据库查询）
        
        参数:
            category: 分类过滤
            year: 年份过滤
            month: 月份过滤
            tag_filters: 标签过滤 {"priority": "high"}
        
        返回:
            [{"path": "...", "size": ..., "tags": {...}, "doc_id": ...}, ...]
        """
        try:
            with MetadataManager() as mgr:
                # 构建查询条件
                doc_date = None
                if year and month:
                    doc_date = f"{year}-{month:02d}"
                elif year:
                    # 只指定年份，需要特殊处理
                    pass
                
                # 先按元数据查询
                if doc_date:
                    docs = mgr.search_by_metadata(
                        category=category,
                        doc_date=doc_date,
                        status='active'
                    )
                    # 去重
                    seen = set()
                    unique_docs = []
                    for doc in docs:
                        if doc.minio_path not in seen:
                            seen.add(doc.minio_path)
                            unique_docs.append(doc)
                    docs = unique_docs
                elif year:
                    # 只指定年份，查询所有活跃文档然后过滤
                    all_docs = mgr.search_by_metadata(
                        category=category,
                        status='active'
                    )
                    docs = [doc for doc in all_docs 
                           if doc.doc_date and doc.doc_date.startswith(str(year))]
                    # 去重
                    seen = set()
                    unique_docs = []
                    for doc in docs:
                        if doc.minio_path not in seen:
                            seen.add(doc.minio_path)
                            unique_docs.append(doc)
                    docs = unique_docs
                else:
                    docs = mgr.search_by_metadata(
                        category=category,
                        status='active'
                    )
                    # 去重
                    seen = set()
                    unique_docs = []
                    for doc in docs:
                        if doc.minio_path not in seen:
                            seen.add(doc.minio_path)
                            unique_docs.append(doc)
                    docs = unique_docs
                
                # 标签过滤
                if tag_filters:
                    filtered_docs = []
                    for doc in docs:
                        if doc.tags:
                            if all(doc.tags.get(k) == v for k, v in tag_filters.items()):
                                filtered_docs.append(doc)
                        docs = filtered_docs
                
                # 转换为返回格式（再次去重，确保结果唯一）
                seen_paths = set()
                results = []
                for doc in docs:
                    if doc.minio_path in seen_paths:
                        continue
                    seen_paths.add(doc.minio_path)
                    # 从 MinIO 获取文件大小和修改时间（如果需要）
                    try:
                        stat = self.client.stat_object(self.bucket, doc.minio_path)
                        file_size = stat.size
                        last_modified = stat.last_modified
                    except:
                        file_size = doc.file_size
                        last_modified = doc.updated_at
                    
                    results.append({
                        'path': doc.minio_path,
                        'size': file_size or doc.file_size or 0,
                        'last_modified': last_modified,
                        'tags': doc.tags or {},
                        'doc_id': doc.id,
                        'category': doc.category,
                        'department': doc.department,
                        'author': doc.author
                    })
                
                return results
        except Exception as e:
            print(f"数据库查询失败，回退到 MinIO 查询: {e}")
            # 回退到 MinIO 查询
            # 构建前缀
            if category and year and month:
                prefix = f"{category}/{year}/{month:02d}/"
            elif category and year:
                prefix = f"{category}/{year}/"
            elif category:
                prefix = f"{category}/"
            else:
                prefix = ""
            
            results = []
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            
            for obj in objects:
                tags = {}
                try:
                    t = self.client.get_object_tags(self.bucket, obj.object_name)
                    tags = dict(t) if t else {}
                except:
                    pass
                
                # 标签过滤
                if tag_filters:
                    if not all(tags.get(k) == v for k, v in tag_filters.items()):
                        continue
                
                results.append({
                    'path': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'tags': tags
                })
            
            return results
    
    # =========================================================================
    # 版本控制
    # =========================================================================
    
    def list_versions(self, path: str) -> List[Dict]:
        """列出文档的所有版本"""
        objects = self.client.list_objects(self.bucket, prefix=path, include_version=True)
        
        versions = []
        for obj in objects:
            if obj.object_name == path and not obj.is_delete_marker:
                versions.append({
                    'version_id': obj.version_id,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'is_latest': obj.is_latest
                })
        
        versions.sort(key=lambda x: x['last_modified'])
        return versions
    
    def rollback(self, path: str, version_id: str, user: str = 'system',
                 user_role: str = None, user_department: str = None) -> Dict:
        """
        回退到指定版本（更新 MinIO 和数据库）
        
        参数:
            path: 文档路径
            version_id: 要回退到的版本 ID
            user: 操作用户（用于日志记录）
            user_role: 用户角色
            user_department: 用户部门
        
        返回:
            Dict: 回退结果
        """
        old_content = self.download(path, version_id, user=user, 
                                   user_role=user_role, user_department=user_department)
        data = old_content.encode('utf-8')
        
        # 1. 在 MinIO 中创建新版本（回退）
        result = self.client.put_object(
            bucket_name=self.bucket,
            object_name=path,
            data=io.BytesIO(data),
            length=len(data)
        )
        
        # 2. 更新数据库中的版本 ID
        old_version_id = version_id
        try:
            with MetadataManager() as mgr:
                doc = mgr.get_document_by_path(path, self.bucket)
                if doc:
                    mgr.update_document(doc.id, version_id=result.version_id)
        except Exception as e:
            print(f"警告：数据库版本更新失败: {e}")
        
        # 3. 记录访问日志
        try:
            self.access_logger.log(
                action='rollback',
                object_path=path,
                user=user,
                bucket=self.bucket,
                user_role=user_role,
                user_department=user_department,
                details={
                    'old_version_id': old_version_id,
                    'new_version_id': result.version_id
                }
            )
        except Exception as e:
            print(f"记录访问日志失败: {e}")
        
        return {
            'path': path,
            'new_version_id': result.version_id,
            'rolled_back_from': version_id
        }
    
    # =========================================================================
    # 信息和统计
    # =========================================================================
    
    def get_info(self, path: str) -> Dict:
        """
        获取文档完整信息（优先从数据库读取）
        
        参数:
            path: 文档路径
        
        返回:
            Dict: 文档信息
        """
        # 优先从数据库读取
        try:
            with MetadataManager() as mgr:
                doc = mgr.get_document_by_path(path, self.bucket)
                if doc:
                    # 从 MinIO 获取文件统计信息
                    try:
                        stat = self.client.stat_object(self.bucket, path)
                        file_size = stat.size
                        last_modified = stat.last_modified
                        version_id = stat.version_id
                        content_type = stat.content_type
                    except:
                        file_size = doc.file_size
                        last_modified = doc.updated_at
                        version_id = doc.version_id
                        content_type = doc.content_type
                    
                    return {
                        'path': doc.minio_path,
                        'size': file_size,
                        'last_modified': last_modified,
                        'version_id': version_id,
                        'content_type': content_type,
                        'metadata': {
                            'department': doc.department,
                            'author': doc.author,
                            'doc_type': doc.doc_type,
                            'doc_date': doc.doc_date,
                            'description': doc.description
                        },
                        'tags': doc.tags or {},
                        'doc_id': doc.id,
                        'category': doc.category,
                        'status': doc.status,
                        'is_readonly': doc.is_readonly,
                        'is_archived': doc.is_archived
                    }
        except Exception as e:
            print(f"数据库查询失败，从 MinIO 读取: {e}")
        
        # 回退到 MinIO 查询
        stat = self.client.stat_object(self.bucket, path)
        
        try:
            tags = self.client.get_object_tags(self.bucket, path)
            tags_dict = dict(tags) if tags else {}
        except:
            tags_dict = {}
        
        metadata = {}
        for k, v in stat.metadata.items():
            if k.startswith('X-Amz-Meta-'):
                metadata[k.replace('X-Amz-Meta-', '').lower()] = v
        
        return {
            'path': path,
            'size': stat.size,
            'last_modified': stat.last_modified,
            'version_id': stat.version_id,
            'content_type': stat.content_type,
            'metadata': metadata,
            'tags': tags_dict
        }
    
    def get_stats(self) -> Dict:
        """
        获取存储统计（从数据库统计）
        
        返回:
            Dict: 统计信息
        """
        try:
            with MetadataManager() as mgr:
                stats_dict = mgr.get_statistics()
                
                # 计算总大小（需要从 MinIO 或数据库获取）
                total_size = 0
                with MetadataManager() as size_mgr:
                    docs = size_mgr.search_by_metadata(status='active')
                    for doc in docs:
                        if doc.file_size:
                            total_size += doc.file_size
                
                # 按年份统计
                by_year = {}
                with MetadataManager() as year_mgr:
                    all_docs = year_mgr.search_by_metadata(status='active')
                    for doc in all_docs:
                        if doc.doc_date:
                            year = doc.doc_date.split('-')[0]
                            by_year[year] = by_year.get(year, 0) + 1
                
                return {
                    'total_files': stats_dict['total_documents'],
                    'total_size': total_size,
                    'by_category': stats_dict['by_category'],
                    'by_year': by_year,
                    'by_department': stats_dict['by_department'],
                    'by_status': stats_dict['by_status']
                }
        except Exception as e:
            print(f"数据库统计失败，回退到 MinIO 统计: {e}")
            # 回退到 MinIO 统计
            stats = {
                'total_files': 0,
                'total_size': 0,
                'by_category': {},
                'by_year': {}
            }
            
            objects = list(self.client.list_objects(self.bucket, recursive=True))
            
            for obj in objects:
                stats['total_files'] += 1
                stats['total_size'] += obj.size
                
                parts = obj.object_name.split('/')
                if len(parts) >= 2:
                    category = parts[0]
                    year = parts[1] if len(parts) > 1 else 'unknown'
                    
                    stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
                    stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
            
            return stats
    
    def list_all(self) -> List[str]:
        """
        列出所有文档（从数据库查询）
        
        返回:
            List[str]: 所有文档路径列表
        """
        try:
            with MetadataManager() as mgr:
                docs = mgr.search_by_metadata(status='active')
                # 去重
                seen = set()
                results = []
                for doc in docs:
                    if doc.minio_path not in seen:
                        seen.add(doc.minio_path)
                        results.append(doc.minio_path)
                return results
        except Exception as e:
            print(f"数据库查询失败，回退到 MinIO 查询: {e}")
            # 回退到 MinIO 查询
            objects = self.client.list_objects(self.bucket, recursive=True)
            return [obj.object_name for obj in objects]
    
    # =========================================================================
    # 删除操作
    # =========================================================================
    
    def delete(self, path: str, version_id: str = None, user: str = 'system',
               user_role: str = None, user_department: str = None) -> bool:
        """
        删除文档（同时删除 MinIO 文件和数据库记录）
        
        参数:
            path: 文档路径
            version_id: 版本 ID（如果指定，只删除该版本）
            user: 删除用户（用于日志记录）
            user_role: 用户角色
            user_department: 用户部门
        
        返回:
            bool: 是否成功
        """
        # 如果指定了版本 ID，只删除 MinIO 中的该版本（不删除数据库记录）
        if version_id:
            try:
                self.client.remove_object(self.bucket, path, version_id=version_id)
                # 记录访问日志
                try:
                    self.access_logger.log(
                        action='delete',
                        object_path=path,
                        user=user,
                        bucket=self.bucket,
                        user_role=user_role,
                        user_department=user_department,
                        details={'version_id': version_id, 'delete_type': 'version'}
                    )
                except Exception as e:
                    print(f"记录访问日志失败: {e}")
                return True
            except:
                return False
        
        # 删除整个文档：先删除数据库记录，再删除 MinIO 文件
        try:
            # 1. 从数据库删除记录
            doc_id = None
            with MetadataManager() as mgr:
                doc = mgr.get_document_by_path(path, self.bucket)
                if doc:
                    doc_id = doc.id
                    mgr.delete_document(doc.id, soft_delete=False)
            
            # 2. 删除 MinIO 文件
            self.client.remove_object(self.bucket, path)
            
            # 3. 记录访问日志
            try:
                self.access_logger.log(
                    action='delete',
                    object_path=path,
                    user=user,
                    bucket=self.bucket,
                    user_role=user_role,
                    user_department=user_department,
                    details={'doc_id': doc_id, 'delete_type': 'full'}
                )
            except Exception as e:
                print(f"记录访问日志失败: {e}")
            
            return True
        except Exception as e:
            print(f"删除失败: {e}")
            return False
    
    def delete_all_versions(self, path: str) -> int:
        """删除文档的所有版本"""
        versions = self.list_versions(path)
        count = 0
        for v in versions:
            if self.delete(path, v['version_id']):
                count += 1
        return count

