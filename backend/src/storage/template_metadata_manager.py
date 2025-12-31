# -*- coding: utf-8 -*-
"""
模板元数据管理器
管理模板在数据库中的元数据信息
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .database import TemplateMetadata, get_db_session


class TemplateMetadataManager:
    """
    模板元数据管理器
    
    使用上下文管理器管理数据库会话
    """
    
    def __init__(self, session: Session = None, config_path: str = None):
        """
        初始化模板元数据管理器
        
        Args:
            session: 数据库会话（可选，如果不提供则自动创建）
            config_path: 配置文件路径（仅在自动创建会话时使用）
        """
        self.session = session
        self.config_path = config_path
        self._own_session = session is None
    
    def __enter__(self):
        """进入上下文管理器"""
        if self._own_session:
            self.session = get_db_session(self.config_path)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        # 如果使用的是外部会话，不自动提交或关闭
        if self._own_session and self.session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()
            self.session = None
        # 如果使用外部会话，只清理引用，不关闭会话
        elif not self._own_session:
            self.session = None
    
    def add_template(
        self,
        template_name: str,
        minio_path: str,
        bucket: str,
        filename: str,
        format_type: str,
        version: int,
        file_size: int = None,
        content_type: str = None,
        version_id: str = None,
        category: str = None,
        template_type: str = None,
        tags: Dict = None,
        change_log: str = None,
        created_by: str = None,
        is_latest: bool = True
    ) -> TemplateMetadata:
        """
        添加模板元数据
        
        Args:
            template_name: 模板名称
            minio_path: MinIO 存储路径
            bucket: MinIO 桶名称
            filename: 文件名
            format_type: 模板格式（word/pdf/html）
            version: 版本号
            file_size: 文件大小
            content_type: MIME 类型
            version_id: MinIO 版本 ID
            category: 分类
            tags: 标签
            change_log: 变更日志
            created_by: 创建者
            is_latest: 是否最新版本
        
        Returns:
            TemplateMetadata 对象
        """
        # 如果是新版本，将旧版本标记为非最新
        if is_latest:
            self.session.query(TemplateMetadata).filter(
                and_(
                    TemplateMetadata.template_name == template_name,
                    TemplateMetadata.format_type == format_type,
                    TemplateMetadata.is_latest == True
                )
            ).update({'is_latest': False})
        
        template = TemplateMetadata(
            template_name=template_name,
            minio_path=minio_path,
            bucket=bucket,
            filename=filename,
            format_type=format_type,
            version=version,
            file_size=file_size,
            content_type=content_type,
            version_id=version_id,
            category=category,
            # template_type 已从数据库表中移除
            tags=tags or {},
            change_log=change_log,
            created_by=created_by,
            is_latest=is_latest,
            created_at=datetime.now()
        )
        
        self.session.add(template)
        self.session.flush()
        self.session.refresh(template)
        return template
    
    def get_template(
        self,
        template_name: str,
        version: int = None,
        format_type: str = None,
        is_latest: bool = None
    ) -> Optional[TemplateMetadata]:
        """
        获取模板元数据
        
        Args:
            template_name: 模板名称
            version: 版本号（None 表示最新版本）
            format_type: 格式类型（可选）
            is_latest: 是否最新版本（如果 version 为 None 且 is_latest 为 True，返回最新版本）
        
        Returns:
            TemplateMetadata 对象或 None
        """
        query = self.session.query(TemplateMetadata).filter(
            TemplateMetadata.template_name == template_name
        )
        
        if format_type:
            query = query.filter(TemplateMetadata.format_type == format_type)
        
        if version is not None:
            query = query.filter(TemplateMetadata.version == version)
        elif is_latest is None or is_latest:
            query = query.filter(TemplateMetadata.is_latest == True)
        
        return query.first()
    
    def get_template_versions(
        self,
        template_name: str,
        format_type: str = None
    ) -> List[TemplateMetadata]:
        """
        获取模板的所有版本
        
        Args:
            template_name: 模板名称
            format_type: 格式类型（可选）
        
        Returns:
            版本列表
        """
        query = self.session.query(TemplateMetadata).filter(
            TemplateMetadata.template_name == template_name
        )
        
        if format_type:
            query = query.filter(TemplateMetadata.format_type == format_type)
        
        return query.order_by(TemplateMetadata.version.desc()).all()
    
    def search_templates(
        self,
        category: str = None,
        format_type: str = None,
        template_name: str = None
    ) -> List[TemplateMetadata]:
        """
        搜索模板
        
        Args:
            category: 分类
            format_type: 格式类型
            template_name: 模板名称（模糊匹配）
        
        Returns:
            模板列表
        """
        query = self.session.query(TemplateMetadata).filter(
            TemplateMetadata.is_latest == True
        )
        
        if category:
            query = query.filter(TemplateMetadata.category == category)
        
        if format_type:
            query = query.filter(TemplateMetadata.format_type == format_type)
        
        if template_name:
            query = query.filter(TemplateMetadata.template_name.like(f'%{template_name}%'))
        
        return query.all()
    
    def update_template(
        self,
        template_id: int,
        **kwargs
    ) -> Optional[TemplateMetadata]:
        """
        更新模板元数据
        
        Args:
            template_id: 模板 ID
            **kwargs: 要更新的字段
        
        Returns:
            更新后的 TemplateMetadata 对象
        """
        template = self.session.query(TemplateMetadata).filter(
            TemplateMetadata.id == template_id
        ).first()
        
        if not template:
            return None
        
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.created_at = datetime.now()
        self.session.flush()
        self.session.refresh(template)
        return template
    
    def delete_template(self, template_id: int, soft_delete: bool = True) -> bool:
        """
        删除模板元数据
        
        Args:
            template_id: 模板 ID
            soft_delete: 是否软删除（默认 True，只标记删除）
        
        Returns:
            是否成功
        """
        template = self.session.query(TemplateMetadata).filter(
            TemplateMetadata.id == template_id
        ).first()
        
        if not template:
            return False
        
        if soft_delete:
            # 软删除：标记为删除
            template.is_latest = False
            # 可以添加 deleted_at 字段
        else:
            # 硬删除：从数据库删除
            self.session.delete(template)
        
        return True

