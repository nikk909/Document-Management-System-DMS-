# -*- coding: utf-8 -*-
"""
权限管理模块
- 角色定义
- 权限检查
"""

from enum import Enum
from typing import Optional, List
from dataclasses import dataclass


class Role(Enum):
    """角色枚举"""
    ADMIN = 'admin'
    USER = 'user'


class Permission(Enum):
    """权限枚举"""
    UPLOAD = 'upload'                    # 上传
    DOWNLOAD = 'download'                # 下载
    MODIFY = 'modify'                    # 修改
    DELETE = 'delete'                    # 删除
    VIEW_HISTORY = 'view_history'        # 查看历史版本
    VIEW_LOGS = 'view_logs'              # 查看访问日志
    MANAGE_PERMISSIONS = 'manage_permissions'  # 权限管理（设置脱敏、禁止下载、禁止查看）
    GENERATE_DOCUMENT = 'generate_document'    # 文档生成


# 角色权限映射
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.UPLOAD,
        Permission.DOWNLOAD,
        Permission.MODIFY,
        Permission.DELETE,
        Permission.VIEW_HISTORY,
        Permission.VIEW_LOGS,
        Permission.MANAGE_PERMISSIONS,
        Permission.GENERATE_DOCUMENT,
    ],
    Role.USER: [
        Permission.UPLOAD,
        Permission.DOWNLOAD,
        Permission.MODIFY,
        Permission.DELETE,
        Permission.GENERATE_DOCUMENT,
    ],
}


@dataclass
class DocumentInfo:
    """文档信息（用于权限检查）"""
    path: str
    owner: str = None           # 文档所有者
    department: str = None      # 所属部门
    is_encrypted: bool = False  # 是否加密
    is_archived: bool = False   # 是否归档


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self):
        pass
    
    def _get_role_enum(self, role: str) -> Optional[Role]:
        """将字符串角色转换为枚举"""
        try:
            return Role(role)
        except ValueError:
            return None
    
    def _has_permission(self, role: str, permission: Permission) -> bool:
        """检查角色是否有指定权限"""
        role_enum = self._get_role_enum(role)
        if role_enum is None:
            return False
        
        permissions = ROLE_PERMISSIONS.get(role_enum, [])
        return permission in permissions
    
    def can_upload(self, user_role: str, user_department: str, 
                   target_department: str = None) -> bool:
        """
        检查是否有上传权限
        
        Args:
            user_role: 用户角色
            user_department: 用户部门
            target_department: 目标部门（可选）
            
        Returns:
            是否有权限
        """
        if not self._has_permission(user_role, Permission.UPLOAD):
            return False
        
        # admin 可以上传到任何部门
        if user_role == 'admin':
            return True
        
        # 其他角色只能上传到自己部门
        if target_department and target_department != user_department:
            return False
        
        return True
    
    def can_download(self, user_role: str, user_department: str,
                     doc: DocumentInfo = None, 
                     is_masked_required: bool = False,
                     is_download_forbidden: bool = False) -> bool:
        """
        检查是否有下载权限
        
        Args:
            user_role: 用户角色
            user_department: 用户部门
            doc: 文档信息
            is_masked_required: 是否被要求只能下载脱敏文件（由管理员设置）
            is_download_forbidden: 是否被禁止下载（由管理员设置）
            
        Returns:
            是否有权限
        """
        # 如果没有下载权限，直接返回 False
        if not self._has_permission(user_role, Permission.DOWNLOAD):
            return False
        
        # admin 可以自行选择是否脱敏，不受限制
        if user_role == 'admin':
            return True
        
        # user 如果被管理员禁止下载，则无法下载
        if is_download_forbidden:
            return False
        
        # user 如果被要求脱敏，只能下载脱敏文件（这个在下载时处理，这里只检查是否有下载权限）
        return True
    
    def can_modify(self, user_role: str, user_department: str,
                   username: str, doc: DocumentInfo = None) -> bool:
        """
        检查是否有修改权限
        
        Args:
            user_role: 用户角色
            user_department: 用户部门
            username: 用户名
            doc: 文档信息
            
        Returns:
            是否有权限
        """
        if not self._has_permission(user_role, Permission.MODIFY):
            return False
        
        # 归档文件不能修改
        if doc and doc.is_archived:
            return False
        
        # admin 可以修改任何文档
        if user_role == 'admin':
            return True
        
        # user 只能修改自己创建的文档
        if user_role == 'user':
            if doc and doc.owner:
                return doc.owner == username
            return True
        
        return False
    
    def can_delete(self, user_role: str, user_department: str,
                   username: str, doc: DocumentInfo = None) -> bool:
        """
        检查是否有删除权限
        
        Args:
            user_role: 用户角色
            user_department: 用户部门
            username: 用户名
            doc: 文档信息
            
        Returns:
            是否有权限
        """
        if not self._has_permission(user_role, Permission.DELETE):
            return False
        
        # 归档文件不能删除
        if doc and doc.is_archived:
            return False
        
        # admin 可以删除任何文档
        if user_role == 'admin':
            return True
        
        # user 只能删除自己创建的文档
        if user_role == 'user':
            if doc and doc.owner:
                return doc.owner == username
            return True
        
        return False
    
    def can_view_history(self, user_role: str) -> bool:
        """
        检查是否可以查看历史版本
        
        Args:
            user_role: 用户角色
            
        Returns:
            是否有权限
        """
        return self._has_permission(user_role, Permission.VIEW_HISTORY)
    
    def can_view_logs(self, user_role: str) -> bool:
        """
        检查是否可以查看访问日志
        
        Args:
            user_role: 用户角色
            
        Returns:
            是否有权限
        """
        return self._has_permission(user_role, Permission.VIEW_LOGS)
    
    def can_manage_permissions(self, user_role: str) -> bool:
        """
        检查是否可以管理权限（设置脱敏、禁止下载、禁止查看）
        
        Args:
            user_role: 用户角色
            
        Returns:
            是否有权限
        """
        return self._has_permission(user_role, Permission.MANAGE_PERMISSIONS)
    
    def can_generate_document(self, user_role: str) -> bool:
        """
        检查是否可以生成文档
        
        Args:
            user_role: 用户角色
            
        Returns:
            是否有权限
        """
        return self._has_permission(user_role, Permission.GENERATE_DOCUMENT)
    
    def get_permissions(self, user_role: str) -> List[str]:
        """
        获取角色的所有权限
        
        Args:
            user_role: 用户角色
            
        Returns:
            权限列表
        """
        role_enum = self._get_role_enum(user_role)
        if role_enum is None:
            return []
        
        permissions = ROLE_PERMISSIONS.get(role_enum, [])
        return [p.value for p in permissions]
    
    def check_all_permissions(self, user_role: str, user_department: str,
                              username: str, doc: DocumentInfo = None) -> dict:
        """
        检查用户对文档的所有权限
        
        Args:
            user_role: 用户角色
            user_department: 用户部门
            username: 用户名
            doc: 文档信息
            
        Returns:
            权限字典
        """
        return {
            'upload': self.can_upload(user_role, user_department),
            'download': self.can_download(user_role, user_department, doc),
            'modify': self.can_modify(user_role, user_department, username, doc),
            'delete': self.can_delete(user_role, user_department, username, doc),
            'view_history': self.can_view_history(user_role),
            'view_logs': self.can_view_logs(user_role),
            'manage_permissions': self.can_manage_permissions(user_role),
            'generate_document': self.can_generate_document(user_role),
        }

