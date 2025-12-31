# -*- coding: utf-8 -*-
"""
文档元数据管理器
使用 SQLAlchemy 进行元数据的增删改查
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .database import DocumentMetadata, GeneratedDocumentMetadata, get_db_session


class MetadataManager:
    """
    文档元数据管理器
    
    提供文档元数据的 CRUD 操作和高级查询功能
    """
    
    def __init__(self, session: Session = None):
        """
        初始化元数据管理器
        
        参数:
            session: 数据库会话，如果为 None 则自动创建
        """
        self.session = session or get_db_session()
        self._auto_close = session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._auto_close:
            if exc_type:
                self.session.rollback()
            else:
                # 检查是否有未提交的更改
                # 注意：update_document/add_document/delete_document 已经提交了，这里主要是处理其他可能的更改
                try:
                    if self.session.dirty or self.session.new or self.session.deleted:
                        self.session.commit()
                except Exception as e:
                    # 如果已经提交过，这里可能会报错，忽略即可
                    pass
            self.session.close()
    
    def add_document(
        self,
        filename: str,
        minio_path: str,
        bucket: str,
        department: str = None,
        author: str = None,
        doc_type: str = None,
        doc_date: str = None,
        description: str = None,
        category: str = None,
        tags: Dict = None,
        file_size: int = None,
        content_type: str = None,
        version_id: str = None,
        created_by: str = None,
        **kwargs
    ) -> DocumentMetadata:
        """
        添加文档元数据
        
        参数:
            filename: 文件名
            minio_path: MinIO 存储路径
            bucket: MinIO 桶名称
            department: 部门
            author: 作者
            doc_type: 文档类型
            doc_date: 文档日期（如 "2024-05"）
            description: 描述
            category: 分类
            tags: 标签（字典）
            file_size: 文件大小
            content_type: MIME 类型
            version_id: MinIO 版本 ID
            created_by: 创建者
            **kwargs: 其他字段
        
        返回:
            DocumentMetadata: 创建的文档元数据对象
        """
        doc = DocumentMetadata(
            filename=filename,
            minio_path=minio_path,
            bucket=bucket,
            department=department,
            author=author,
            doc_type=doc_type,
            doc_date=doc_date,
            description=description,
            category=category,
            tags=tags or {},
            file_size=file_size,
            content_type=content_type,
            version_id=version_id,
            created_by=created_by,
            **kwargs
        )
        
        self.session.add(doc)
        
        # 立即提交，确保数据真正保存到数据库并获取 ID
        try:
            self.session.commit()
            self.session.refresh(doc)
        except Exception as e:
            self.session.rollback()
            print(f"添加文档失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return doc
    
    def get_document(self, doc_id: int) -> Optional[DocumentMetadata]:
        """
        根据 ID 获取文档元数据
        
        参数:
            doc_id: 文档 ID
        
        返回:
            DocumentMetadata 或 None
        """
        # 使用 expire_on_commit=False 确保读取最新数据
        doc = self.session.query(DocumentMetadata).filter(
            DocumentMetadata.id == doc_id
        ).first()
        if doc:
            # 刷新对象，确保获取最新数据
            self.session.refresh(doc)
        return doc
    
    def get_document_by_path(self, minio_path: str, bucket: str = None) -> Optional[DocumentMetadata]:
        """
        根据 MinIO 路径获取文档元数据
        
        参数:
            minio_path: MinIO 存储路径
            bucket: 桶名称（可选）
        
        返回:
            DocumentMetadata 或 None
        """
        query = self.session.query(DocumentMetadata).filter(
            DocumentMetadata.minio_path == minio_path
        )
        if bucket:
            query = query.filter(DocumentMetadata.bucket == bucket)
        doc = query.first()
        if doc:
            # 刷新对象，确保获取最新数据
            self.session.refresh(doc)
        return doc
    
    def update_document(self, doc_id: int, **kwargs) -> Optional[DocumentMetadata]:
        """
        更新文档元数据
        
        参数:
            doc_id: 文档 ID
            **kwargs: 要更新的字段
        
        返回:
            DocumentMetadata 或 None
        """
        doc = self.get_document(doc_id)
        if not doc:
            return None
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(doc, key):
                # 确保 Boolean 字段正确设置
                if isinstance(value, bool):
                    setattr(doc, key, value)
                elif value is None:
                    # 允许设置为 None
                    setattr(doc, key, None)
                else:
                    setattr(doc, key, value)
        
        doc.updated_at = datetime.now()
        
        # 立即提交更改，确保数据真正保存到数据库
        # 即使使用上下文管理器，我们也需要立即提交，因为后续操作可能依赖这个更新
        try:
            self.session.commit()
            self.session.refresh(doc)
        except Exception as e:
            self.session.rollback()
            print(f"更新文档失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return doc
    
    def delete_document(self, doc_id: int, soft_delete: bool = False) -> bool:
        """
        删除文档元数据
        
        参数:
            doc_id: 文档 ID
            soft_delete: 是否软删除（标记为 deleted 状态），默认 False（硬删除）
        
        返回:
            bool: 是否成功
        """
        doc = self.get_document(doc_id)
        if not doc:
            return False
        
        if soft_delete:
            doc.status = 'deleted'
            doc.updated_at = datetime.now()
        else:
            # 硬删除：直接从数据库中删除
            self.session.delete(doc)
        
        # 立即提交，确保删除操作真正执行
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            print(f"删除文档失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return True
    
    def delete_all_documents(self, confirm: bool = False) -> int:
        """
        删除表中所有数据（危险操作！）
        
        参数:
            confirm: 是否确认删除，必须为 True 才能执行
        
        返回:
            int: 删除的记录数
        """
        if not confirm:
            raise ValueError("必须设置 confirm=True 才能删除所有数据！")
        
        count = self.session.query(DocumentMetadata).count()
        self.session.query(DocumentMetadata).delete()
        self.session.commit()
        return count
    
    def search_by_metadata(
        self,
        department: str = None,
        author: str = None,
        doc_type: str = None,
        doc_date: str = None,
        category: str = None,
        status: str = 'active',
        **kwargs
    ) -> List[DocumentMetadata]:
        """
        按元数据搜索文档
        
        参数:
            department: 部门
            author: 作者
            doc_type: 文档类型
            doc_date: 文档日期
            category: 分类
            status: 状态（默认 'active'）
            **kwargs: 其他字段条件
        
        返回:
            List[DocumentMetadata]: 匹配的文档列表
        """
        query = self.session.query(DocumentMetadata)
        
        # 构建查询条件
        conditions = []
        if department:
            conditions.append(DocumentMetadata.department == department)
        if author:
            conditions.append(DocumentMetadata.author == author)
        if doc_type:
            conditions.append(DocumentMetadata.doc_type == doc_type)
        if doc_date:
            conditions.append(DocumentMetadata.doc_date == doc_date)
        if category:
            conditions.append(DocumentMetadata.category == category)
        if status:
            conditions.append(DocumentMetadata.status == status)
        
        # 其他字段条件
        for key, value in kwargs.items():
            if hasattr(DocumentMetadata, key):
                conditions.append(getattr(DocumentMetadata, key) == value)
        
        if conditions:
            query = query.filter(and_(*conditions))
        
        return query.order_by(DocumentMetadata.created_at.desc()).all()
    
    def search_by_tags(self, tags: Dict[str, str]) -> List[DocumentMetadata]:
        """
        按标签搜索文档
        
        参数:
            tags: 标签字典，如 {'priority': 'high', 'status': 'approved'}
        
        返回:
            List[DocumentMetadata]: 匹配的文档列表
        """
        query = self.session.query(DocumentMetadata)
        
        # JSON 字段查询（MySQL 5.7+ 支持）
        for key, value in tags.items():
            # 使用 JSON_EXTRACT 或 JSON_CONTAINS
            query = query.filter(
                func.json_extract(DocumentMetadata.tags, f'$.{key}') == value
            )
        
        return query.order_by(DocumentMetadata.created_at.desc()).all()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        返回:
            Dict: 统计信息
        """
        total = self.session.query(func.count(DocumentMetadata.id)).scalar()
        
        by_department = self.session.query(
            DocumentMetadata.department,
            func.count(DocumentMetadata.id)
        ).group_by(DocumentMetadata.department).all()
        
        by_category = self.session.query(
            DocumentMetadata.category,
            func.count(DocumentMetadata.id)
        ).group_by(DocumentMetadata.category).all()
        
        by_status = self.session.query(
            DocumentMetadata.status,
            func.count(DocumentMetadata.id)
        ).group_by(DocumentMetadata.status).all()
        
        return {
            'total_documents': total,
            'by_department': dict(by_department),
            'by_category': dict(by_category),
            'by_status': dict(by_status),
        }


class GeneratedDocumentMetadataManager:
    """
    生成的文档元数据管理器
    
    专门管理通过模板生成的文档（PDF/Word/HTML）
    """
    
    def __init__(self, session: Session = None):
        """
        初始化生成的文档元数据管理器
        
        参数:
            session: 数据库会话，如果为 None 则自动创建
        """
        self.session = session or get_db_session()
        self._auto_close = session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._auto_close:
            if exc_type:
                self.session.rollback()
            else:
                try:
                    if self.session.dirty or self.session.new or self.session.deleted:
                        self.session.commit()
                except Exception as e:
                    pass
            self.session.close()
    
    def add_generated_document(
        self,
        filename: str,
        minio_path: str,
        bucket: str,
        format_type: str,
        template_id: int,
        template_name: str,
        department: str = None,
        author: str = None,
        description: str = None,
        tags: Dict = None,
        file_size: int = None,
        content_type: str = None,
        version_id: str = None,
        created_by: str = None,
        category: str = None,
        **kwargs
    ) -> GeneratedDocumentMetadata:
        """
        添加生成的文档元数据
        
        参数:
            filename: 文件名
            minio_path: MinIO 存储路径
            bucket: MinIO 桶名称
            format_type: 格式类型（pdf/word/html）
            template_id: 使用的模板ID
            template_name: 使用的模板名称
            department: 部门
            author: 作者/生成人
            description: 描述
            tags: 标签（字典）
            file_size: 文件大小
            content_type: MIME 类型
            version_id: MinIO 版本 ID
            created_by: 创建者
            category: 分类
            **kwargs: 其他字段
        
        返回:
            GeneratedDocumentMetadata: 创建的生成文档元数据对象
        """
        doc = GeneratedDocumentMetadata(
            filename=filename,
            minio_path=minio_path,
            bucket=bucket,
            format_type=format_type,
            template_id=template_id,
            template_name=template_name,
            department=department,
            author=author,
            description=description,
            tags=tags or {},
            file_size=file_size,
            content_type=content_type,
            version_id=version_id,
            created_by=created_by or author,
            category=category,
            status='active',
            is_archived=False
        )
        
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc
    
    def get_generated_document(self, doc_id: int) -> Optional[GeneratedDocumentMetadata]:
        """根据ID获取生成的文档"""
        return self.session.query(GeneratedDocumentMetadata).filter(
            GeneratedDocumentMetadata.id == doc_id
        ).first()
    
    def search_generated_documents(
        self,
        format_type: str = None,
        template_id: int = None,
        template_name: str = None,
        status: str = 'active',
        keyword: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        category: str = None
    ) -> List[GeneratedDocumentMetadata]:
        """
        搜索生成的文档
        
        参数:
            format_type: 格式类型过滤（pdf/word/html）
            template_id: 模板ID过滤
            template_name: 模板名称过滤
            status: 状态过滤
            keyword: 关键词搜索（文件名、描述、分类）
            date_from: 开始日期
            date_to: 结束日期
            category: 分类过滤
        
        返回:
            List[GeneratedDocumentMetadata]: 生成的文档列表
        """
        query = self.session.query(GeneratedDocumentMetadata)
        
        if status:
            query = query.filter(GeneratedDocumentMetadata.status == status)
        
        if format_type:
            query = query.filter(GeneratedDocumentMetadata.format_type == format_type)
        
        if category:
            query = query.filter(GeneratedDocumentMetadata.category == category)
        
        if template_id:
            query = query.filter(GeneratedDocumentMetadata.template_id == template_id)
        
        if template_name:
            query = query.filter(GeneratedDocumentMetadata.template_name.like(f"%{template_name}%"))
        
        if keyword:
            keyword_pattern = f"%{keyword}%"
            query = query.filter(
                or_(
                    GeneratedDocumentMetadata.filename.like(keyword_pattern),
                    GeneratedDocumentMetadata.description.like(keyword_pattern),
                    GeneratedDocumentMetadata.category.like(keyword_pattern),
                    GeneratedDocumentMetadata.template_name.like(keyword_pattern)
                )
            )
        
        if date_from:
            query = query.filter(GeneratedDocumentMetadata.created_at >= date_from)
        
        if date_to:
            query = query.filter(GeneratedDocumentMetadata.created_at <= date_to)
        
        return query.order_by(GeneratedDocumentMetadata.created_at.desc()).all()
    
    def delete_generated_document(self, doc_id: int) -> bool:
        """删除生成的文档（软删除）"""
        doc = self.get_generated_document(doc_id)
        if doc:
            doc.status = 'deleted'
            self.session.commit()
            return True
        return False
    
    def archive_generated_document(self, doc_id: int, archive: bool = True) -> bool:
        """归档/取消归档生成的文档"""
        doc = self.get_generated_document(doc_id)
        if doc:
            doc.is_archived = archive
            self.session.commit()
            return True
        return False

