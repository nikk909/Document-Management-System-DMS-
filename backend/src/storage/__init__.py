"""
存储管理模块
提供 MinIO 对象存储和 MySQL 元数据管理功能
"""

from .storage_manager import StorageManager
from .metadata_manager import MetadataManager
from .minio_client import MinioClient
from .database import DatabaseManager

# 模板元数据管理器（可选）
try:
    from .template_metadata_manager import TemplateMetadataManager
    __all__ = [
        'StorageManager',
        'MetadataManager',
        'MinioClient',
        'DatabaseManager',
        'TemplateMetadataManager',
    ]
except ImportError:
    __all__ = [
        'StorageManager',
        'MetadataManager',
        'MinioClient',
        'DatabaseManager',
    ]

