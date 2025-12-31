"""
安全功能模块
包含数据脱敏、权限控制、访问日志等功能
"""

from .data_masking import DataMasker, mask_text, mask_id_card, mask_phone, mask_email
from .permission import PermissionChecker, Role, Permission, DocumentInfo
from .user_manager import UserManager, User
from .access_logger import AccessLogger

__all__ = [
    'DataMasker',
    'mask_text',
    'mask_id_card',
    'mask_phone',
    'mask_email',
    'PermissionChecker',
    'Role',
    'Permission',
    'DocumentInfo',
    'UserManager',
    'User',
    'AccessLogger',
]

