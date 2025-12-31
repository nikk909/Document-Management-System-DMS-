# -*- coding: utf-8 -*-
"""
访问日志记录器
记录所有文件操作：上传、下载、修改、删除
支持存储到数据库和 MinIO（logs桶）
"""

import json
import io
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index, text, and_, func

from ..storage.database import Base, get_db_session
from ..storage.utils import load_config

# 访问日志表模型
class AccessLog(Base):
    """
    访问日志表
    记录所有文档操作
    """
    __tablename__ = 'access_logs'
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 操作信息
    action = Column(String(50), nullable=False, index=True, comment='操作类型')
    object_path = Column(String(500), nullable=False, index=True, comment='对象路径')
    bucket = Column(String(100), comment='桶名称')
    
    # 用户信息
    user = Column(String(100), nullable=False, index=True, comment='操作用户')
    user_role = Column(String(50), index=True, comment='用户角色')
    user_department = Column(String(100), index=True, comment='用户部门')
    
    # 操作详情
    details = Column(JSON, comment='操作详情（JSON格式）')
    ip_address = Column(String(50), comment='IP地址')
    user_agent = Column(String(500), comment='用户代理')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment='操作时间')
    
    # 索引
    __table_args__ = (
        Index('idx_action_time', 'action', 'created_at'),
        Index('idx_user_time', 'user', 'created_at'),
        Index('idx_path_time', 'object_path', 'created_at'),
    )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'action': self.action,
            'object_path': self.object_path,
            'bucket': self.bucket,
            'user': self.user,
            'user_role': self.user_role,
            'user_department': self.user_department,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AccessLogger:
    """
    访问日志记录器
    
    记录所有文件操作：上传、下载、修改、删除
    日志同时存储在数据库（MySQL）和MinIO（logs桶）
    """
    
    def __init__(self, session=None, config_path: str = None):
        """
        初始化访问日志记录器
        
        Args:
            session: 数据库会话（可选，默认自动创建）
            config_path: MinIO配置文件路径（可选）
        """
        self.session = session
        self.config_path = config_path
        
        # 初始化MinIO客户端（延迟加载）
        self._minio_client = None
        self._logs_bucket = None
    
    def _get_session(self):
        """获取数据库会话"""
        if self.session:
            return self.session
        return get_db_session()
    
    def _get_minio_client(self):
        """获取MinIO客户端（延迟初始化）"""
        if self._minio_client is None:
            try:
                from minio import Minio
                config = load_config(self.config_path)
                minio_config = config.get('minio', {})
                
                endpoint = minio_config.get('endpoint', 'localhost:9000')
                access_key = minio_config.get('access_key', 'minioadmin')
                secret_key = minio_config.get('secret_key', 'minioadmin')
                secure = minio_config.get('secure', False)
                
                self._minio_client = Minio(
                    endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=secure
                )
                
                # 获取logs桶名称
                buckets_config = minio_config.get('buckets', {})
                self._logs_bucket = buckets_config.get('logs', 'logs')
                
                # 确保logs桶存在
                if not self._minio_client.bucket_exists(self._logs_bucket):
                    self._minio_client.make_bucket(self._logs_bucket)
            except Exception as e:
                print(f"初始化MinIO客户端失败（日志将只存储到数据库）: {e}")
                self._minio_client = None
        
        return self._minio_client
    
    def log(
        self,
        action: str,
        object_path: str,
        user: str,
        bucket: str = None,
        user_role: str = None,
        user_department: str = None,
        details: Dict = None,
        ip_address: str = None,
        user_agent: str = None
    ):
        """
        记录一条访问日志
        
        Args:
            action: 操作类型 (upload, download, modify, delete, archive, view)
            object_path: 操作的对象路径
            user: 操作用户
            bucket: 操作的桶
            user_role: 用户角色
            user_department: 用户部门
            details: 额外详情
            ip_address: IP地址
            user_agent: 用户代理
        """
        session = self._get_session()
        log_timestamp = datetime.now()
        
        try:
            # 1. 存储到MySQL数据库
            log_entry = AccessLog(
                action=action,
                object_path=object_path,
                bucket=bucket,
                user=user,
                user_role=user_role,
                user_department=user_department,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=log_timestamp
            )
            
            session.add(log_entry)
            session.commit()
            
            # 获取日志ID（用于MinIO存储）
            log_id = log_entry.id
            
            # 2. 同步存储到MinIO logs桶
            try:
                minio_client = self._get_minio_client()
                if minio_client and self._logs_bucket:
                    # 构建日志文件路径：logs/YYYY/MM/DD/log_ID.json
                    log_date = log_timestamp
                    log_path = f"logs/{log_date.year}/{log_date.month:02d}/{log_date.day:02d}/log_{log_id}.json"
                    
                    # 构建日志JSON内容
                    log_data = {
                        "id": log_id,
                        "action": action,
                        "object_path": object_path,
                        "bucket": bucket,
                        "user": user,
                        "user_role": user_role,
                        "user_department": user_department,
                        "details": details or {},
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "created_at": log_timestamp.isoformat()
                    }
                    
                    # 上传到MinIO
                    log_json = json.dumps(log_data, ensure_ascii=False, indent=2)
                    log_bytes = log_json.encode('utf-8')
                    
                    minio_client.put_object(
                        bucket_name=self._logs_bucket,
                        object_name=log_path,
                        data=io.BytesIO(log_bytes),
                        length=len(log_bytes),
                        content_type='application/json'
                    )
            except Exception as e:
                # MinIO存储失败不影响MySQL存储
                print(f"同步日志到MinIO失败（MySQL已保存）: {e}")
        except Exception as e:
            session.rollback()
            print(f"记录访问日志失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 如果会话是我们创建的，需要关闭
            if not self.session:
                session.close()
    
    def get_logs(
        self,
        year: int = None,
        month: int = None,
        day: int = None,
        action: str = None,
        user: str = None,
        object_path: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        查询访问日志
        
        Args:
            year: 年份过滤
            month: 月份过滤
            day: 日期过滤
            action: 操作类型过滤
            user: 用户过滤
            object_path: 对象路径过滤（模糊匹配）
            limit: 返回数量限制
        
        Returns:
            日志条目列表
        """
        session = self._get_session()
        
        try:
            from sqlalchemy import and_, func
            
            query = session.query(AccessLog)
            
            # 构建查询条件
            conditions = []
            
            if year:
                if month and day:
                    start_date = datetime(year, month, day)
                    end_date = datetime(year, month, day, 23, 59, 59)
                    conditions.append(and_(
                        AccessLog.created_at >= start_date,
                        AccessLog.created_at <= end_date
                    ))
                elif month:
                    start_date = datetime(year, month, 1)
                    if month == 12:
                        end_date = datetime(year + 1, 1, 1)
                    else:
                        end_date = datetime(year, month + 1, 1)
                    conditions.append(and_(
                        AccessLog.created_at >= start_date,
                        AccessLog.created_at < end_date
                    ))
                else:
                    start_date = datetime(year, 1, 1)
                    end_date = datetime(year + 1, 1, 1)
                    conditions.append(and_(
                        AccessLog.created_at >= start_date,
                        AccessLog.created_at < end_date
                    ))
            
            if action:
                conditions.append(AccessLog.action == action)
            
            if user:
                conditions.append(AccessLog.user == user)
            
            if object_path:
                conditions.append(AccessLog.object_path.like(f'%{object_path}%'))
            
            if conditions:
                query = query.filter(and_(*conditions))
            
            # 按时间倒序排列，限制数量
            logs = query.order_by(AccessLog.created_at.desc()).limit(limit).all()
            
            return [log.to_dict() for log in logs]
        except Exception as e:
            print(f"查询访问日志失败: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if not self.session:
                session.close()
    
    def get_object_history(self, object_path: str, limit: int = 100) -> List[Dict]:
        """
        获取某个对象的完整操作历史
        
        Args:
            object_path: 对象路径
            limit: 返回数量限制
        
        Returns:
            日志条目列表
        """
        return self.get_logs(object_path=object_path, limit=limit)
    
    def get_user_activity(self, user: str, limit: int = 100) -> List[Dict]:
        """
        获取某个用户的所有操作记录
        
        Args:
            user: 用户名
            limit: 返回数量限制
        
        Returns:
            日志条目列表
        """
        return self.get_logs(user=user, limit=limit)
    
    def get_statistics(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """
        获取访问统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            统计信息字典
        """
        session = self._get_session()
        
        try:
            from sqlalchemy import and_, func
            
            query = session.query(AccessLog)
            
            if start_date:
                query = query.filter(AccessLog.created_at >= start_date)
            if end_date:
                query = query.filter(AccessLog.created_at <= end_date)
            
            # 按操作类型统计
            action_stats = session.query(
                AccessLog.action,
                func.count(AccessLog.id)
            ).filter(
                and_(
                    *(AccessLog.created_at >= start_date if start_date else True,
                      AccessLog.created_at <= end_date if end_date else True)
                ) if start_date or end_date else True
            ).group_by(AccessLog.action).all()
            
            # 按用户统计
            user_stats = session.query(
                AccessLog.user,
                func.count(AccessLog.id)
            ).filter(
                and_(
                    *(AccessLog.created_at >= start_date if start_date else True,
                      AccessLog.created_at <= end_date if end_date else True)
                ) if start_date or end_date else True
            ).group_by(AccessLog.user).order_by(func.count(AccessLog.id).desc()).limit(10).all()
            
            return {
                'total_logs': query.count(),
                'by_action': dict(action_stats),
                'top_users': dict(user_stats),
            }
        except Exception as e:
            print(f"获取访问统计失败: {e}")
            import traceback
            traceback.print_exc()
            return {}
        finally:
            if not self.session:
                session.close()

