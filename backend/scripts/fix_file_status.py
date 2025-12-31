"""
修复文件状态字段
确保所有文件的status为'active'
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session
from sqlalchemy import text

def fix_status():
    """修复文件状态"""
    config_path = os.path.join(backend_root, "config", "config.yaml")
    db = get_db_session(config_path=config_path)
    
    try:
        print("检查文件状态...")
        
        # 查询所有文件的状态
        result = db.execute(
            text("SELECT id, filename, status FROM documents")
        )
        files = result.fetchall()
        
        print(f"\n文件总数: {len(files)}")
        print("\n当前状态:")
        print("-" * 60)
        
        files_to_fix = []
        for row in files:
            file_id, filename, status = row
            status_display = status if status else 'NULL'
            print(f"ID: {file_id:3d} | 文件名: {filename:20s} | 状态: {status_display}")
            if not status or status != 'active':
                files_to_fix.append(file_id)
        
        if files_to_fix:
            print(f"\n找到 {len(files_to_fix)} 个需要修复的文件")
            print("开始修复...")
            
            # 批量更新状态
            db.execute(
                text("UPDATE documents SET status = 'active' WHERE id IN :ids OR status IS NULL OR status != 'active'"),
                {"ids": tuple(files_to_fix)}
            )
            
            # 或者逐个更新（更安全）
            for file_id in files_to_fix:
                db.execute(
                    text("UPDATE documents SET status = 'active' WHERE id = :id"),
                    {"id": file_id}
                )
            
            db.commit()
            print(f"已修复 {len(files_to_fix)} 个文件的状态")
        else:
            print("\n所有文件状态正常，无需修复")
        
        # 再次查询确认
        print("\n修复后的状态:")
        print("-" * 60)
        result = db.execute(
            text("SELECT id, filename, status FROM documents")
        )
        files = result.fetchall()
        for row in files:
            file_id, filename, status = row
            print(f"ID: {file_id:3d} | 文件名: {filename:20s} | 状态: {status or 'NULL'}")
        
    except Exception as e:
        print(f"\n[ERROR] 修复失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    fix_status()

