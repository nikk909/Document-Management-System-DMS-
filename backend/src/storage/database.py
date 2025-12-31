# -*- coding: utf-8 -*-
"""
数据库连接和模型定义
使用 SQLAlchemy 管理文档元数据
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, JSON, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .utils import load_mysql_config

Base = declarative_base()

# 导入访问日志模型（延迟导入，避免循环依赖）
def _import_access_log():
    """延迟导入访问日志模型"""
    try:
        from ..security.access_logger import AccessLog
        return AccessLog
    except ImportError:
        return None


class TemplateMetadata(Base):
    """
    模板元数据表
    
    存储模板的元数据信息，实际文件存储在 MinIO 中
    """
    __tablename__ = 'templates'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 模板基本信息
    template_name = Column(String(255), nullable=False, index=True, comment='模板名称')
    minio_path = Column(String(500), nullable=False, comment='MinIO 存储路径')
    bucket = Column(String(100), nullable=False, comment='MinIO 桶名称')
    version_id = Column(String(100), comment='MinIO 版本 ID')
    
    # 文件属性
    filename = Column(String(255), nullable=False, comment='文件名')
    file_size = Column(Integer, comment='文件大小（字节）')
    content_type = Column(String(100), comment='MIME 类型')
    format_type = Column(String(20), index=True, comment='模板格式（word/pdf/html）')
    
    # 版本信息
    version = Column(Integer, nullable=False, index=True, comment='版本号')
    is_latest = Column(Boolean, default=False, index=True, comment='是否最新版本')
    
    # 分类和标签
    category = Column(String(50), index=True, comment='分类（财务报表/人事合同等，保留字段用于兼容）')
    # 注意：template_type字段已从模型中移除，因为数据库表中不存在此列
    # 如果需要此功能，请先执行数据库迁移添加此列
    tags = Column(JSON, comment='标签（字典格式）')
    
    # 变更信息
    change_log = Column(Text, comment='变更日志')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment='创建时间')
    created_by = Column(String(100), comment='创建者')
    
    # 索引
    __table_args__ = (
        Index('idx_template_name_version', 'template_name', 'version'),
        Index('idx_category_format', 'category', 'format_type'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'template_name': self.template_name,
            'minio_path': self.minio_path,
            'bucket': self.bucket,
            'version_id': self.version_id,
            'filename': self.filename,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'format_type': self.format_type,
            'version': self.version,
            'is_latest': self.is_latest,
            'category': self.category,
            'tags': self.tags,
            'change_log': self.change_log,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
        }


class User(Base):
    """
    用户表
    
    存储用户信息和认证数据
    """
    __tablename__ = 'users'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='用户ID')
    
    # 用户基本信息
    username = Column(String(100), nullable=False, unique=True, index=True, comment='用户名')
    password_hash = Column(String(255), nullable=False, comment='密码哈希值')
    role = Column(String(50), nullable=False, default='user', index=True, comment='角色：admin/user')
    department = Column(String(100), nullable=False, default='default', index=True, comment='部门')
    display_name = Column(String(100), comment='显示名称')
    
    # 注意：数据库表中没有 created_at 和 updated_at 字段，所以不在这里定义
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}', department='{self.department}')>"


class DocumentMetadata(Base):
    """
    文档元数据表
    
    存储文档的元数据信息，实际文件存储在 MinIO 中
    """
    __tablename__ = 'documents'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 文件基本信息
    filename = Column(String(255), nullable=False, comment='文件名')
    minio_path = Column(String(500), nullable=False, comment='MinIO 存储路径')
    bucket = Column(String(100), nullable=False, comment='MinIO 桶名称')
    version_id = Column(String(100), comment='MinIO 版本 ID')
    
    # 文件属性
    file_size = Column(Integer, comment='文件大小（字节）')
    content_type = Column(String(100), comment='MIME 类型')
    
    # 元数据字段
    department = Column(String(100), index=True, comment='部门')
    author = Column(String(100), index=True, comment='作者')
    doc_type = Column(String(50), index=True, comment='文档类型')
    doc_date = Column(String(20), index=True, comment='文档日期（如 2024-05）')
    description = Column(Text, comment='描述')
    
    # 分类信息
    category = Column(String(50), index=True, comment='分类（reports/contracts/notes等）')
    
    # 注意：file_tags字段已从模型中移除，因为数据库表中不存在此列
    # 如果需要此功能，请先执行数据库迁移添加此列
    
    # 标签（JSON 格式存储）
    tags = Column(JSON, comment='标签（字典格式）')
    
    # 状态信息
    status = Column(String(20), default='active', index=True, comment='状态（active/archived/deleted）')
    is_readonly = Column(Boolean, default=False, index=True, comment='是否只读')
    is_archived = Column(Boolean, default=False, index=True, comment='是否归档')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    created_by = Column(String(100), comment='创建者')
    
    # 索引（提高查询性能）
    __table_args__ = (
        Index('idx_department_date', 'department', 'doc_date'),
        Index('idx_status_archived', 'status', 'is_archived'),
        Index('idx_category_date', 'category', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'filename': self.filename,
            'minio_path': self.minio_path,
            'bucket': self.bucket,
            'version_id': self.version_id,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'department': self.department,
            'author': self.author,
            'doc_type': self.doc_type,
            'doc_date': self.doc_date,
            'description': self.description,
            'category': self.category,
            'tags': self.tags,
            # 'file_tags': self.file_tags,  # 已移除：数据库表中不存在此列
            'status': self.status,
            'is_readonly': self.is_readonly,
            'is_archived': self.is_archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


class GeneratedDocumentMetadata(Base):
    """
    生成的文档元数据表
    
    专门存储通过模板生成的文档（PDF/Word/HTML），按格式类型分开存储
    """
    __tablename__ = 'generated_documents'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 文件基本信息
    filename = Column(String(255), nullable=False, comment='文件名')
    minio_path = Column(String(500), nullable=False, comment='MinIO 存储路径')
    bucket = Column(String(100), nullable=False, comment='MinIO 桶名称')
    version_id = Column(String(100), comment='MinIO 版本 ID')
    
    # 文件属性
    file_size = Column(Integer, comment='文件大小（字节）')
    content_type = Column(String(100), comment='MIME 类型')
    format_type = Column(String(20), nullable=False, index=True, comment='格式类型（pdf/word/html）')
    
    # 模板信息
    template_id = Column(Integer, index=True, comment='使用的模板ID')
    template_name = Column(String(255), index=True, comment='使用的模板名称')
    
    # 元数据字段
    department = Column(String(100), index=True, comment='部门')
    author = Column(String(100), index=True, comment='作者/生成人')
    description = Column(Text, comment='描述')
    
    # 标签（JSON 格式存储）
    tags = Column(JSON, comment='标签（字典格式）')
    
    # 状态信息
    status = Column(String(20), default='active', index=True, comment='状态（active/archived/deleted）')
    is_archived = Column(Boolean, default=False, index=True, comment='是否归档')
    is_masked = Column(Boolean, default=False, index=True, comment='是否脱敏')
    category = Column(String(50), index=True, comment='分类')
    
    # 权限控制（黑名单，JSON格式存储）
    blocked_users = Column(JSON, comment='禁止下载的用户列表（用户名数组）')
    blocked_departments = Column(JSON, comment='禁止下载的部门列表（部门数组）')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    created_by = Column(String(100), comment='创建者')
    
    # 索引（提高查询性能）
    __table_args__ = (
        Index('idx_format_type_date', 'format_type', 'created_at'),
        Index('idx_template_id', 'template_id'),
        Index('idx_status_archived', 'status', 'is_archived'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'filename': self.filename,
            'minio_path': self.minio_path,
            'bucket': self.bucket,
            'version_id': self.version_id,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'format_type': self.format_type,
            'template_id': self.template_id,
            'template_name': self.template_name,
            'department': self.department,
            'author': self.author,
            'description': self.description,
            'tags': self.tags,
            'status': self.status,
            'is_archived': self.is_archived,
            'is_masked': self.is_masked,
            'blocked_users': self.blocked_users,
            'blocked_departments': self.blocked_departments,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }


class DatabaseManager:
    """
    数据库管理器
    
    负责创建数据库连接、会话管理和表初始化
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化数据库管理器
        
        参数:
            config_path: 统一配置文件路径（如果为None，使用默认路径 config/config.yaml）
        """
        # 如果没有提供配置路径，使用默认的统一配置文件
        if config_path is None:
            from pathlib import Path
            backend_root = Path(__file__).parent.parent.parent
            config_path = str(backend_root / "config" / "config.yaml")
        
        config = load_mysql_config(config_path)
        mysql_config = config.get('mysql', {})
        
        # 构建连接字符串
        self.connection_string = (
            f"mysql+pymysql://{mysql_config['user']}:{mysql_config['password']}"
            f"@{mysql_config['host']}:{mysql_config['port']}"
            f"/{mysql_config['database']}?charset={mysql_config['charset']}"
        )
        
        # 创建引擎（带连接池）
        self.engine = create_engine(
            self.connection_string,
            poolclass=QueuePool,
            pool_size=mysql_config.get('pool_size', 5),
            max_overflow=mysql_config.get('max_overflow', 10),
            pool_timeout=mysql_config.get('pool_timeout', 30),
            pool_recycle=mysql_config.get('pool_recycle', 3600),
            echo=False  # 设置为 True 可以看到 SQL 语句
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )
    
    def get_session(self) -> Session:
        """
        获取数据库会话
        
        返回:
            Session: SQLAlchemy 会话对象
        """
        return self.SessionLocal()
    
    def create_tables(self):
        """
        创建所有表（如果不存在）
        """
        # 导入所有模型（包括访问日志表和模板表）
        try:
            from ..security.access_logger import AccessLog
            # 确保 AccessLog 表也被创建
        except ImportError:
            pass
        
        # 确保 TemplateMetadata 表也被创建
        # TemplateMetadata 已经在当前文件中定义，会自动创建
        
        Base.metadata.create_all(self.engine)
        print("数据库表创建成功！")
        print("  已创建表: documents, templates, generated_documents, access_logs")
        # 修复 AUTO_INCREMENT
        self.fix_auto_increment()
    
    def fix_auto_increment(self):
        """
        修复 AUTO_INCREMENT 值
        确保 AUTO_INCREMENT 从正确的值开始：
        - 如果表为空，从 1 开始
        - 如果表有数据，从最大 ID + 1 开始
        """
        try:
            with self.engine.connect() as conn:
                # 检查表是否存在
                result = conn.execute(text("""
                    SELECT COUNT(*) as table_exists 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'documents'
                """))
                row = result.fetchone()
                if not row or row[0] == 0:
                    print("表 documents 不存在，跳过 AUTO_INCREMENT 修复")
                    return
                
                # 检查表中是否有数据
                result = conn.execute(text("SELECT MAX(id) as max_id FROM documents"))
                row = result.fetchone()
                max_id = row[0] if row and row[0] is not None else 0
                
                # 设置 AUTO_INCREMENT
                if max_id == 0:
                    # 表为空，设置 AUTO_INCREMENT 从 1 开始
                    conn.execute(text("ALTER TABLE documents AUTO_INCREMENT = 1"))
                    conn.commit()
                    print(f"AUTO_INCREMENT 已设置为 1（表为空）")
                else:
                    # 表有数据，设置 AUTO_INCREMENT 从 max_id + 1 开始
                    next_id = max_id + 1
                    conn.execute(text(f"ALTER TABLE documents AUTO_INCREMENT = {next_id}"))
                    conn.commit()
                    print(f"AUTO_INCREMENT 已设置为 {next_id}（当前最大 ID: {max_id}）")
        except Exception as e:
            print(f"AUTO_INCREMENT 修复失败: {e}")
    
    def drop_tables(self):
        """
        删除所有表（谨慎使用！）
        """
        Base.metadata.drop_all(self.engine)
        print("数据库表已删除！")
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        返回:
            bool: 连接是否成功
        """
        try:
            with self.engine.connect() as conn:
                # SQLAlchemy 2.0 需要使用 text() 包装 SQL 字符串
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False


# 全局数据库管理器实例（延迟初始化）
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(config_path: str = None) -> DatabaseManager:
    """
    获取全局数据库管理器实例（单例模式）
    
    参数:
        config_path: MySQL 配置文件路径
    
    返回:
        DatabaseManager: 数据库管理器实例
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(config_path)
    return _db_manager


def get_db_session(config_path: str = None) -> Session:
    """
    获取数据库会话（快捷函数）
    
    参数:
        config_path: MySQL 配置文件路径
    
    返回:
        Session: SQLAlchemy 会话对象
    """
    manager = get_db_manager(config_path)
    return manager.get_session()

