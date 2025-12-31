"""
检查并修复MinIO中的文件路径
找出数据库中的路径与MinIO实际文件不匹配的情况
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session
from src.storage.storage_manager import StorageManager
from sqlalchemy import text

def check_minio_files():
    """检查MinIO中的文件"""
    config_path = os.path.join(backend_root, "config", "config.yaml")
    db = get_db_session(config_path=config_path)
    storage = StorageManager()
    
    try:
        print("=" * 70)
        print("检查MinIO中的文件与数据库记录是否匹配")
        print("=" * 70)
        
        # 获取所有bucket
        all_buckets = list(storage.buckets.values())
        print(f"\n已配置的Bucket: {all_buckets}")
        
        # 列出每个bucket中的所有文件
        print("\n" + "=" * 70)
        print("MinIO中的实际文件:")
        print("=" * 70)
        
        minio_files = {}  # {path: bucket}
        
        for bucket in all_buckets:
            try:
                objects = list(storage.client.list_objects(bucket, recursive=True))
                print(f"\nBucket '{bucket}': {len(objects)} 个文件")
                for obj in objects[:20]:  # 只显示前20个
                    print(f"  - {obj.object_name}")
                    minio_files[obj.object_name] = bucket
                if len(objects) > 20:
                    print(f"  ... 还有 {len(objects) - 20} 个文件")
            except Exception as e:
                print(f"\nBucket '{bucket}': 列出文件失败: {e}")
        
        # 从数据库获取文件记录
        print("\n" + "=" * 70)
        print("数据库中的文件记录:")
        print("=" * 70)
        
        result = db.execute(
            text("SELECT id, filename, category, minio_path, bucket FROM documents ORDER BY id")
        )
        db_files = result.fetchall()
        
        print(f"\n数据库中共有 {len(db_files)} 条记录")
        
        # 检查每个数据库记录
        print("\n" + "=" * 70)
        print("匹配检查:")
        print("=" * 70)
        
        matched = 0
        not_found = 0
        wrong_bucket = 0
        
        for row in db_files:
            file_id, filename, category, minio_path, db_bucket = row
            
            if not minio_path:
                print(f"[无路径] ID: {file_id}, 文件名: {filename}")
                not_found += 1
                continue
            
            # 检查文件是否在MinIO中存在
            if minio_path in minio_files:
                actual_bucket = minio_files[minio_path]
                if actual_bucket == db_bucket:
                    print(f"[OK] ID: {file_id}, 路径: {minio_path}, Bucket: {db_bucket}")
                    matched += 1
                else:
                    print(f"[Bucket不匹配] ID: {file_id}, 路径: {minio_path}")
                    print(f"    数据库Bucket: {db_bucket}, 实际Bucket: {actual_bucket}")
                    wrong_bucket += 1
                    
                    # 更新数据库中的bucket
                    db.execute(
                        text("UPDATE documents SET bucket = :bucket WHERE id = :id"),
                        {"bucket": actual_bucket, "id": file_id}
                    )
                    print(f"    已更新数据库Bucket为: {actual_bucket}")
            else:
                # 尝试在所有bucket中查找
                found = False
                for bucket in all_buckets:
                    try:
                        storage.client.stat_object(bucket, minio_path)
                        print(f"[找到] ID: {file_id}, 路径: {minio_path}, 实际Bucket: {bucket}")
                        
                        # 更新数据库
                        db.execute(
                            text("UPDATE documents SET bucket = :bucket WHERE id = :id"),
                            {"bucket": bucket, "id": file_id}
                        )
                        print(f"    已更新数据库Bucket为: {bucket}")
                        matched += 1
                        found = True
                        break
                    except:
                        pass
                
                if not found:
                    print(f"[未找到] ID: {file_id}, 文件名: {filename}, 路径: {minio_path}, 数据库Bucket: {db_bucket}")
                    not_found += 1
        
        # 提交更改
        db.commit()
        
        print("\n" + "=" * 70)
        print("统计结果:")
        print("=" * 70)
        print(f"匹配: {matched}")
        print(f"Bucket不匹配(已修复): {wrong_bucket}")
        print(f"文件未找到: {not_found}")
        
    except Exception as e:
        print(f"\n[ERROR] 检查失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    check_minio_files()

