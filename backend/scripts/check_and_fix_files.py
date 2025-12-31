"""
检查和修复文件分类问题
1. 检查数据库中的文件
2. 检查MinIO中的文件路径
3. 修复未移动的文件
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session
from src.storage.storage_manager import StorageManager
from minio.commonconfig import CopySource
from sqlalchemy import text

def check_and_fix():
    """检查和修复文件"""
    config_path = os.path.join(backend_root, "config", "config.yaml")
    db = get_db_session(config_path=config_path)
    storage = StorageManager()
    
    try:
        print("=" * 50)
        print("检查数据库中的文件...")
        print("=" * 50)
        
        # 查询所有文件
        result = db.execute(
            text("SELECT id, filename, category, minio_path, bucket FROM documents ORDER BY id")
        )
        files = result.fetchall()
        
        print(f"\n数据库中的文件总数: {len(files)}")
        print("\n文件列表:")
        print("-" * 80)
        
        files_to_fix = []
        
        for row in files:
            file_id, filename, category, minio_path, bucket = row
            print(f"ID: {file_id:3d} | 文件名: {filename:20s} | 分类: {category or 'None':10s} | 路径: {minio_path or 'None'}")
            
            # 检查需要修复的文件
            if minio_path and minio_path.startswith("documents/"):
                files_to_fix.append({
                    'id': file_id,
                    'filename': filename,
                    'category': category or '未分类',
                    'old_path': minio_path,
                    'bucket': bucket or storage.bucket
                })
        
        if files_to_fix:
            print(f"\n找到 {len(files_to_fix)} 个需要修复的文件（路径仍为documents/开头）")
            print("\n开始修复...")
            print("-" * 80)
            
            for file_info in files_to_fix:
                try:
                    old_path = file_info['old_path']
                    new_category = file_info['category'] if file_info['category'] != 'documents' else '未分类'
                    
                    # 构建新路径
                    if old_path.startswith("documents/"):
                        path_parts = old_path.split('/', 1)
                        if len(path_parts) > 1:
                            date_and_filename = path_parts[1]
                            new_path = f"{new_category}/{date_and_filename}"
                        else:
                            continue
                    else:
                        continue
                    
                    old_bucket = file_info['bucket'] or storage.bucket
                    dest_bucket = storage._get_bucket_for_category(new_category)
                    
                    # 更新分类（如果还是documents）
                    if file_info['category'] == 'documents' or not file_info['category']:
                        db.execute(
                            text("UPDATE documents SET category = :category WHERE id = :id"),
                            {"category": new_category, "id": file_info['id']}
                        )
                    
                    # 尝试移动MinIO文件
                    try:
                        try:
                            # 检查源文件是否存在
                            storage.client.stat_object(old_bucket, old_path)
                            
                            # 复制到新路径
                            copy_source = CopySource(
                                bucket_name=old_bucket,
                                object_name=old_path
                            )
                            storage.client.copy_object(
                                bucket_name=dest_bucket,
                                object_name=new_path,
                                source=copy_source
                            )
                            
                            # 删除旧文件
                            storage.client.remove_object(old_bucket, old_path)
                            
                            # 更新数据库
                            db.execute(
                                text("UPDATE documents SET minio_path = :new_path, bucket = :bucket, category = :category WHERE id = :id"),
                                {"new_path": new_path, "bucket": dest_bucket, "category": new_category, "id": file_info['id']}
                            )
                            
                            print(f"  [OK] {file_info['filename']}: {old_path} -> {new_path}")
                        except Exception as e:
                            # 源文件不存在，只更新数据库
                            print(f"  [WARN] 源文件不存在 {old_path}，只更新数据库: {str(e)[:50]}")
                            # 更新路径和分类（即使MinIO文件不存在）
                            db.execute(
                                text("UPDATE documents SET minio_path = :new_path, bucket = :bucket, category = :category WHERE id = :id"),
                                {"new_path": new_path, "bucket": dest_bucket, "category": new_category, "id": file_info['id']}
                            )
                    except Exception as e:
                        print(f"  [ERROR] 移动文件失败 {file_info['filename']}: {str(e)[:100]}")
                        
                except Exception as e:
                    print(f"  [ERROR] 处理文件 {file_info['filename']} 失败: {str(e)[:100]}")
            
            # 提交更改
            db.commit()
            print(f"\n已提交所有更改")
        else:
            print("\n没有需要修复的文件")
        
        # 重新查询并显示最终状态
        print("\n" + "=" * 50)
        print("最终文件列表:")
        print("=" * 50)
        result = db.execute(
            text("SELECT id, filename, category, minio_path, bucket FROM documents ORDER BY id")
        )
        files = result.fetchall()
        
        for row in files:
            file_id, filename, category, minio_path, bucket = row
            print(f"ID: {file_id:3d} | 文件名: {filename:20s} | 分类: {category or 'None':10s} | 路径: {minio_path or 'None'}")
        
        # 检查分类统计
        print("\n" + "=" * 50)
        print("分类统计:")
        print("=" * 50)
        result = db.execute(
            text("SELECT category, COUNT(*) as count FROM documents GROUP BY category")
        )
        stats = result.fetchall()
        for category, count in stats:
            print(f"分类: {category or 'None':15s} | 文件数: {count}")
            
    except Exception as e:
        print(f"\n[ERROR] 检查失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    check_and_fix()

