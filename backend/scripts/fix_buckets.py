"""
修复数据库中的bucket值
确保bucket与分类和路径匹配
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session
from src.storage.storage_manager import StorageManager
from sqlalchemy import text

def fix_buckets():
    """修复bucket值"""
    config_path = os.path.join(backend_root, "config", "config.yaml")
    db = get_db_session(config_path=config_path)
    storage = StorageManager()
    
    try:
        print("=" * 60)
        print("修复数据库中的bucket值")
        print("=" * 60)
        
        # 查询所有文件
        result = db.execute(
            text("SELECT id, filename, category, minio_path, bucket FROM documents ORDER BY id")
        )
        files = result.fetchall()
        
        print(f"\n文件总数: {len(files)}")
        print("\n检查和修复bucket:")
        print("-" * 60)
        
        updated = 0
        for row in files:
            file_id, filename, category, minio_path, bucket = row
            category = category or '未分类'
            
            # 根据分类确定正确的bucket
            correct_bucket = storage._get_bucket_for_category(category)
            
            # 检查bucket是否需要更新
            if bucket != correct_bucket:
                print(f"ID: {file_id:3d} | 文件名: {filename:20s} | 分类: {category:10s} | Bucket: {bucket or 'None':15s} -> {correct_bucket}")
                
                db.execute(
                    text("UPDATE documents SET bucket = :bucket WHERE id = :id"),
                    {"bucket": correct_bucket, "id": file_id}
                )
                updated += 1
            else:
                print(f"ID: {file_id:3d} | 文件名: {filename:20s} | 分类: {category:10s} | Bucket: {bucket or 'None':15s} [OK]")
        
        # 查询所有模板
        result = db.execute(
            text("SELECT id, template_name, category, minio_path, bucket FROM templates ORDER BY id")
        )
        templates = result.fetchall()
        
        print(f"\n模板总数: {len(templates)}")
        print("\n检查和修复模板bucket:")
        print("-" * 60)
        
        template_updated = 0
        for row in templates:
            template_id, template_name, category, minio_path, bucket = row
            category = category or '未分类'
            
            # 模板通常使用templates bucket
            correct_bucket = 'templates'
            
            if bucket != correct_bucket:
                print(f"ID: {template_id:3d} | 名称: {template_name:20s} | 分类: {category:10s} | Bucket: {bucket or 'None':15s} -> {correct_bucket}")
                
                db.execute(
                    text("UPDATE templates SET bucket = :bucket WHERE id = :id"),
                    {"bucket": correct_bucket, "id": template_id}
                )
                template_updated += 1
            else:
                print(f"ID: {template_id:3d} | 名称: {template_name:20s} | 分类: {category:10s} | Bucket: {bucket or 'None':15s} [OK]")
        
        # 提交更改
        if updated > 0 or template_updated > 0:
            db.commit()
            print(f"\n已修复 {updated} 个文件的bucket和 {template_updated} 个模板的bucket")
        else:
            print("\n所有bucket值都正确，无需修复")
        
    except Exception as e:
        print(f"\n[ERROR] 修复失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    fix_buckets()

