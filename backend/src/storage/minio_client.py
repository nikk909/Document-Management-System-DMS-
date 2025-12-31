"""
MinIO 客户端封装
提供基础的对象存储操作：上传、下载、删除、列表
"""

import os
import io
from pathlib import Path
from typing import List, Optional, BinaryIO
from datetime import datetime

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource

from .utils import load_config, ensure_dir, get_content_type, format_size


class MinioClient:
    """
    MinIO 客户端类
    封装 MinIO Python SDK，提供简化的 API
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化 MinIO 客户端
        
        参数:
            config_path: 配置文件路径，默认使用 config/config.yaml
        """
        # 加载配置
        self.config = load_config(config_path)
        minio_config = self.config['minio']
        
        # 创建 MinIO 客户端
        self.client = Minio(
            endpoint=minio_config['endpoint'],
            access_key=minio_config['access_key'],
            secret_key=minio_config['secret_key'],
            secure=minio_config['secure']
        )
        
        # 默认桶名称
        self.default_bucket = minio_config['default_bucket']
        
        print(f"[OK] MinIO 客户端初始化成功")
        print(f"   端点: {minio_config['endpoint']}")
        print(f"   默认桶: {self.default_bucket}")
    
    # ==================== 桶操作 ====================
    
    def create_bucket(self, bucket_name: str = None) -> bool:
        """
        创建存储桶
        
        参数:
            bucket_name: 桶名称，默认使用配置中的 default_bucket
        
        返回:
            bool: 是否创建成功
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            # 检查桶是否已存在
            if self.client.bucket_exists(bucket_name):
                print(f"[INFO]  桶 '{bucket_name}' 已存在")
                return True
            
            # 创建桶
            self.client.make_bucket(bucket_name)
            print(f"[OK] 桶 '{bucket_name}' 创建成功")
            return True
            
        except S3Error as e:
            print(f"[ERROR] 创建桶失败: {e}")
            return False
    
    def delete_bucket(self, bucket_name: str = None) -> bool:
        """
        删除存储桶（桶必须为空）
        
        参数:
            bucket_name: 桶名称
        
        返回:
            bool: 是否删除成功
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            self.client.remove_bucket(bucket_name)
            print(f"[OK] 桶 '{bucket_name}' 删除成功")
            return True
            
        except S3Error as e:
            print(f"[ERROR] 删除桶失败: {e}")
            return False
    
    def list_buckets(self) -> List[str]:
        """
        列出所有存储桶
        
        返回:
            List[str]: 桶名称列表
        """
        try:
            buckets = self.client.list_buckets()
            bucket_names = [bucket.name for bucket in buckets]
            
            print(f"📦 共有 {len(bucket_names)} 个桶:")
            for name in bucket_names:
                print(f"   - {name}")
            
            return bucket_names
            
        except S3Error as e:
            print(f"[ERROR] 列出桶失败: {e}")
            return []
    
    def bucket_exists(self, bucket_name: str = None) -> bool:
        """
        检查桶是否存在
        
        参数:
            bucket_name: 桶名称
        
        返回:
            bool: 是否存在
        """
        bucket_name = bucket_name or self.default_bucket
        return self.client.bucket_exists(bucket_name)
    
    # ==================== 文件操作 ====================
    
    def upload_file(
        self,
        file_path: str,
        object_name: str = None,
        bucket_name: str = None,
        metadata: dict = None
    ) -> bool:
        """
        上传本地文件到 MinIO
        
        参数:
            file_path: 本地文件路径
            object_name: 对象名称（MinIO 中的文件名），默认使用本地文件名
            bucket_name: 桶名称，默认使用 default_bucket
            metadata: 自定义元数据
        
        返回:
            bool: 是否上传成功
        """
        bucket_name = bucket_name or self.default_bucket
        object_name = object_name or Path(file_path).name
        
        try:
            # 确保桶存在
            self.create_bucket(bucket_name)
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            content_type = get_content_type(file_path)
            
            # 上传文件
            result = self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
                metadata=metadata
            )
            
            print(f"[OK] 文件上传成功")
            print(f"   对象名: {object_name}")
            print(f"   大小: {format_size(file_size)}")
            print(f"   ETag: {result.etag}")
            print(f"   版本ID: {result.version_id or '无（未启用版本控制）'}")
            
            return True
            
        except S3Error as e:
            print(f"[ERROR] 上传文件失败: {e}")
            return False
        except FileNotFoundError:
            print(f"[ERROR] 本地文件不存在: {file_path}")
            return False
    
    def upload_data(
        self,
        data: bytes,
        object_name: str,
        bucket_name: str = None,
        content_type: str = "application/octet-stream",
        metadata: dict = None
    ) -> bool:
        """
        上传字节数据到 MinIO
        
        参数:
            data: 字节数据
            object_name: 对象名称
            bucket_name: 桶名称
            content_type: MIME 类型
            metadata: 自定义元数据
        
        返回:
            bool: 是否上传成功
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            # 确保桶存在
            self.create_bucket(bucket_name)
            
            # 创建字节流
            data_stream = io.BytesIO(data)
            data_length = len(data)
            
            # 上传数据
            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data_stream,
                length=data_length,
                content_type=content_type,
                metadata=metadata
            )
            
            print(f"[OK] 数据上传成功")
            print(f"   对象名: {object_name}")
            print(f"   大小: {format_size(data_length)}")
            print(f"   版本ID: {result.version_id or '无'}")
            
            return True
            
        except S3Error as e:
            print(f"[ERROR] 上传数据失败: {e}")
            return False
    
    def download_file(
        self,
        object_name: str,
        file_path: str = None,
        bucket_name: str = None,
        version_id: str = None
    ) -> bool:
        """
        从 MinIO 下载文件到本地
        
        参数:
            object_name: 对象名称
            file_path: 本地保存路径，默认保存到 downloads 目录
            bucket_name: 桶名称
            version_id: 版本 ID（可选，用于下载特定版本）
        
        返回:
            bool: 是否下载成功
        """
        bucket_name = bucket_name or self.default_bucket
        
        # 默认下载路径
        if file_path is None:
            download_dir = self.config.get('download_dir', './downloads')
            ensure_dir(download_dir)
            file_path = os.path.join(download_dir, object_name)
        
        # 确保目标目录存在
        ensure_dir(os.path.dirname(file_path) or '.')
        
        try:
            # 下载文件
            self.client.fget_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                version_id=version_id
            )
            
            print(f"[OK] 文件下载成功")
            print(f"   对象名: {object_name}")
            print(f"   保存到: {file_path}")
            if version_id:
                print(f"   版本ID: {version_id}")
            
            return True
            
        except S3Error as e:
            print(f"[ERROR] 下载文件失败: {e}")
            return False
    
    def download_data(
        self,
        object_name: str,
        bucket_name: str = None,
        version_id: str = None
    ) -> Optional[bytes]:
        """
        从 MinIO 下载文件内容为字节
        
        参数:
            object_name: 对象名称
            bucket_name: 桶名称
            version_id: 版本 ID（可选）
        
        返回:
            bytes: 文件内容，失败返回 None
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            response = self.client.get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                version_id=version_id
            )
            
            data = response.read()
            response.close()
            response.release_conn()
            
            print(f"[OK] 数据下载成功: {object_name} ({format_size(len(data))})")
            return data
            
        except S3Error as e:
            print(f"[ERROR] 下载数据失败: {e}")
            return None
    
    def copy_object(
        self,
        source_bucket: str,
        source_object: str,
        dest_bucket: str,
        dest_object: str,
        source_version_id: str = None
    ) -> bool:
        """
        复制 MinIO 中的对象
        
        参数:
            source_bucket: 源桶名称
            source_object: 源对象名称
            dest_bucket: 目标桶名称
            dest_object: 目标对象名称
            source_version_id: 源对象版本ID（可选）
        
        返回:
            bool: 是否复制成功
        """
        try:
            # 创建复制源
            copy_source = CopySource(
                bucket_name=source_bucket,
                object_name=source_object,
                version_id=source_version_id
            )
            
            # 执行复制
            result = self.client.copy_object(
                bucket_name=dest_bucket,
                object_name=dest_object,
                source=copy_source
            )
            
            print(f"[OK] 对象复制成功")
            print(f"   源: {source_bucket}/{source_object}")
            print(f"   目标: {dest_bucket}/{dest_object}")
            if result.version_id:
                print(f"   版本ID: {result.version_id}")
            
            return True
            
        except S3Error as e:
            print(f"[ERROR] 复制对象失败: {e}")
            return False
    
    def move_object(
        self,
        source_bucket: str,
        source_object: str,
        dest_bucket: str,
        dest_object: str,
        source_version_id: str = None
    ) -> bool:
        """
        移动 MinIO 中的对象（复制后删除）
        
        参数:
            source_bucket: 源桶名称
            source_object: 源对象名称
            dest_bucket: 目标桶名称
            dest_object: 目标对象名称
            source_version_id: 源对象版本ID（可选）
        
        返回:
            bool: 是否移动成功
        """
        try:
            # 先复制
            if self.copy_object(source_bucket, source_object, dest_bucket, dest_object, source_version_id):
                # 复制成功后删除源对象
                if self.delete_file(source_object, source_bucket, source_version_id):
                    print(f"[OK] 对象移动成功")
                    return True
                else:
                    print(f"[WARN]  复制成功但删除源对象失败，请手动清理")
                    return False
            else:
                return False
                
        except Exception as e:
            print(f"[ERROR] 移动对象失败: {e}")
            return False
    
    def delete_file(
        self,
        object_name: str,
        bucket_name: str = None,
        version_id: str = None
    ) -> bool:
        """
        删除 MinIO 中的文件
        
        参数:
            object_name: 对象名称
            bucket_name: 桶名称
            version_id: 版本 ID（可选，删除特定版本）
        
        返回:
            bool: 是否删除成功
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            self.client.remove_object(
                bucket_name=bucket_name,
                object_name=object_name,
                version_id=version_id
            )
            
            print(f"[OK] 文件删除成功: {object_name}")
            if version_id:
                print(f"   版本ID: {version_id}")
            
            return True
            
        except S3Error as e:
            print(f"[ERROR] 删除文件失败: {e}")
            return False
    
    def list_files(
        self,
        bucket_name: str = None,
        prefix: str = "",
        recursive: bool = True
    ) -> List[dict]:
        """
        列出桶中的所有文件
        
        参数:
            bucket_name: 桶名称
            prefix: 前缀过滤
            recursive: 是否递归列出子目录
        
        返回:
            List[dict]: 文件信息列表
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            objects = self.client.list_objects(
                bucket_name=bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            
            file_list = []
            print(f"📁 桶 '{bucket_name}' 中的文件:")
            
            for obj in objects:
                file_info = {
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'etag': obj.etag,
                    'is_dir': obj.is_dir
                }
                file_list.append(file_info)
                
                if obj.is_dir:
                    print(f"   📂 {obj.object_name}")
                else:
                    print(f"   📄 {obj.object_name} ({format_size(obj.size)})")
            
            if not file_list:
                print("   (空)")
            
            return file_list
            
        except S3Error as e:
            print(f"[ERROR] 列出文件失败: {e}")
            return []
    
    def file_exists(
        self,
        object_name: str,
        bucket_name: str = None
    ) -> bool:
        """
        检查文件是否存在
        
        参数:
            object_name: 对象名称
            bucket_name: 桶名称
        
        返回:
            bool: 是否存在
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error:
            return False
    
    def get_file_info(
        self,
        object_name: str,
        bucket_name: str = None,
        version_id: str = None
    ) -> Optional[dict]:
        """
        获取文件详细信息
        
        参数:
            object_name: 对象名称
            bucket_name: 桶名称
            version_id: 版本 ID（可选）
        
        返回:
            dict: 文件信息，失败返回 None
        """
        bucket_name = bucket_name or self.default_bucket
        
        try:
            stat = self.client.stat_object(
                bucket_name=bucket_name,
                object_name=object_name,
                version_id=version_id
            )
            
            info = {
                'name': stat.object_name,
                'size': stat.size,
                'size_formatted': format_size(stat.size),
                'last_modified': stat.last_modified,
                'etag': stat.etag,
                'content_type': stat.content_type,
                'version_id': stat.version_id,
                'metadata': stat.metadata
            }
            
            print(f"📋 文件信息: {object_name}")
            print(f"   大小: {info['size_formatted']}")
            print(f"   修改时间: {info['last_modified']}")
            print(f"   类型: {info['content_type']}")
            print(f"   版本ID: {info['version_id'] or '无'}")
            
            return info
            
        except S3Error as e:
            print(f"[ERROR] 获取文件信息失败: {e}")
            return None
    
    # ==================== 批量操作 ====================
    
    def upload_directory(
        self,
        local_dir: str,
        prefix: str = "",
        bucket_name: str = None
    ) -> int:
        """
        上传整个目录到 MinIO
        
        参数:
            local_dir: 本地目录路径
            prefix: 对象名前缀
            bucket_name: 桶名称
        
        返回:
            int: 成功上传的文件数量
        """
        bucket_name = bucket_name or self.default_bucket
        success_count = 0
        
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_path = os.path.join(root, file)
                # 计算相对路径
                relative_path = os.path.relpath(local_path, local_dir)
                object_name = os.path.join(prefix, relative_path).replace("\\", "/")
                
                if self.upload_file(local_path, object_name, bucket_name):
                    success_count += 1
        
        print(f"[EXPORT] 目录上传完成: {success_count} 个文件")
        return success_count
    
    def clear_bucket(self, bucket_name: str = None) -> int:
        """
        清空桶中所有文件
        
        参数:
            bucket_name: 桶名称
        
        返回:
            int: 删除的文件数量
        """
        bucket_name = bucket_name or self.default_bucket
        delete_count = 0
        
        try:
            objects = self.client.list_objects(bucket_name, recursive=True)
            
            for obj in objects:
                self.client.remove_object(bucket_name, obj.object_name)
                delete_count += 1
                print(f"   删除: {obj.object_name}")
            
            print(f"[DELETE]  桶清空完成: 删除了 {delete_count} 个文件")
            return delete_count
            
        except S3Error as e:
            print(f"[ERROR] 清空桶失败: {e}")
            return delete_count

