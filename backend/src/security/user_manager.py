# -*- coding: utf-8 -*-
"""
用户管理模块
- 用户登录验证
- 用户信息管理
"""

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class User:
    """用户信息类"""
    username: str      # 用户名
    role: str          # 角色（admin/user）
    department: str   # 部门
    display_name: str   # 显示名称
    
    def __str__(self):
        return f"{self.display_name}({self.username}) - {self.role}@{self.department}"


class UserManager:
    """用户管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化用户管理器
        
        Args:
            config_path: 用户配置文件路径，默认为 src/security/users.yaml
        """
        if config_path is None:
            # 默认配置文件路径（从 security 目录向上到 backend 目录）
            backend_root = Path(__file__).parent.parent.parent
            config_path = backend_root / 'src' / 'security' / 'users.yaml'
        
        self.config_path = Path(config_path)
        self._users: Dict[str, dict] = {}
        self._roles: Dict[str, dict] = {}
        self._current_user: Optional[User] = None
        
        self._load_config()
    
    def _load_config(self):
        """加载用户配置"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"用户配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 加载用户
        for user in config.get('users', []):
            self._users[user['username']] = user
        
        # 加载角色定义
        self._roles = config.get('roles', {})
    
    def login(self, username: str, password: str) -> Optional[User]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            登录成功返回 User 对象，失败返回 None
        """
        user_data = self._users.get(username)
        
        if user_data is None:
            return None
        
        if user_data.get('password') != password:
            return None
        
        # 创建用户对象
        user = User(
            username=user_data['username'],
            role=user_data['role'],
            department=user_data['department'],
            display_name=user_data.get('display_name', username)
        )
        
        self._current_user = user
        return user
    
    def logout(self):
        """用户登出"""
        self._current_user = None
    
    def get_current_user(self) -> Optional[User]:
        """获取当前登录用户"""
        return self._current_user
    
    def get_user(self, username: str) -> Optional[User]:
        """获取指定用户信息（不含密码）"""
        user_data = self._users.get(username)
        if user_data is None:
            return None
        
        return User(
            username=user_data['username'],
            role=user_data['role'],
            department=user_data['department'],
            display_name=user_data.get('display_name', username)
        )
    
    def list_users(self) -> List[User]:
        """列出所有用户"""
        users = []
        for user_data in self._users.values():
            users.append(User(
                username=user_data['username'],
                role=user_data['role'],
                department=user_data['department'],
                display_name=user_data.get('display_name', user_data['username'])
            ))
        return users
    
    def get_role_permissions(self, role: str) -> List[str]:
        """获取角色的权限列表"""
        role_data = self._roles.get(role, {})
        return role_data.get('permissions', [])

