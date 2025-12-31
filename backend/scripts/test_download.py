# -*- coding: utf-8 -*-
"""
测试下载功能
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session
from src.storage.storage_manager import StorageManager
from sqlalchemy import text

def test_download():
    """测试下载"""
    config_path = os.path.join(backend_root, "config", "config.yaml")
    db = get_db_session(config_path=config_path)
    storage = StorageManager()
    
    try:
        print("=" * 70)
        print("测试下载功能")
        print("=" * 70)
        
        # 获取test4.csv的信息
        result = db.execute(text("SELECT id, filename, minio_path, bucket, version_id FROM documents WHERE filename = 'test4.csv'"))
        row = result.fetchone()
        
        if not row:
            print("找不到test4.csv")
            return
        
        file_id, filename, minio_path, bucket, version_id = row
        
        print(f"\n数据库记录:")
        print(f"  ID: {file_id}")
        print(f"  文件名: {filename}")
        print(f"  路径: {minio_path}")
        print(f"  路径(repr): {repr(minio_path)}")
        print(f"  Bucket: {bucket}")
        print(f"  VersionID: {version_id}")
        
        # 检查MinIO中bucket的所有文件
        print(f"\nMinIO中 '{bucket}' bucket的文件:")
        objects = list(storage.client.list_objects(bucket, recursive=True))
        for obj in objects:
            print(f"  {repr(obj.object_name)}")
            
            # 检查是否匹配
            if obj.object_name == minio_path:
                print(f"    -> 与数据库路径匹配!")
        
        # 尝试下载（不指定version_id）
        print(f"\n尝试下载(不指定version_id):")
        try:
            response = storage.client.get_object(bucket, minio_path)
            data = response.read()
            response.close()
            response.release_conn()
            print(f"  成功! 数据大小: {len(data)} 字节")
        except Exception as e:
            print(f"  失败: {e}")
        
        # 尝试下载（指定version_id）
        print(f"\n尝试下载(指定version_id={version_id}):")
        try:
            response = storage.client.get_object(bucket, minio_path, version_id=version_id)
            data = response.read()
            response.close()
            response.release_conn()
            print(f"  成功! 数据大小: {len(data)} 字节")
        except Exception as e:
            print(f"  失败: {e}")
        
        # 检查版本信息
        print(f"\n检查文件版本:")
        try:
            versions = list(storage.client.list_objects(bucket, prefix=minio_path, include_version=True))
            print(f"  找到 {len(versions)} 个版本")
            for v in versions:
                print(f"    版本ID: {v.version_id}, 是否最新: {v.is_latest}")
        except Exception as e:
            print(f"  失败: {e}")
            
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    test_download()

