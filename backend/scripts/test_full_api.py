# -*- coding: utf-8 -*-
"""
完整测试API功能（直接调用函数）
"""
import sys
import os
import asyncio

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'

async def test_all():
    """测试所有功能"""
    from sqlalchemy import text
    from src.storage.database import get_db_session
    from src.storage.categories import get_categories, load_categories
    from src.storage import categories as cat_module
    
    config_path = os.path.join(backend_root, "config", "config.yaml")
    
    print("=" * 70)
    print("1. Test Categories Module")
    print("=" * 70)
    
    # Reset cache
    cat_module._categories = []
    
    cats = load_categories()
    print(f"   Categories: {cats}")
    
    print("\n" + "=" * 70)
    print("2. Test Database Queries")
    print("=" * 70)
    
    db = get_db_session(config_path=config_path)
    
    # Test file categories
    print("\n   File categories:")
    try:
        result = db.execute(text("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL AND category != ''"))
        file_cats = [row[0] for row in result if row[0]]
        for cat in file_cats:
            print(f"     - {cat}")
    except Exception as e:
        print(f"     Error: {e}")
    
    # Test template categories
    print("\n   Template categories:")
    try:
        result = db.execute(text("SELECT DISTINCT category FROM templates WHERE category IS NOT NULL AND category != ''"))
        template_cats = [row[0] for row in result if row[0]]
        for cat in template_cats:
            print(f"     - {cat}")
    except Exception as e:
        print(f"     Error: {e}")
    
    # Test template info (correct column names)
    print("\n   Templates:")
    try:
        result = db.execute(text("SELECT id, template_name, minio_path, bucket, format_type FROM templates LIMIT 5"))
        for row in result:
            print(f"     ID: {row[0]}, Name: {row[1]}, Format: {row[4]}")
    except Exception as e:
        print(f"     Error: {e}")
    
    print("\n" + "=" * 70)
    print("3. Test MinIO Storage")
    print("=" * 70)
    
    try:
        from src.storage.storage_manager import StorageManager
        storage = StorageManager()
        
        # List documents bucket
        print("\n   Documents bucket:")
        objects = list(storage.client.list_objects('documents', recursive=True))
        for obj in objects[:5]:
            print(f"     - {obj.object_name}")
        
        # List templates bucket
        print("\n   Templates bucket:")
        objects = list(storage.client.list_objects('templates', recursive=True))
        for obj in objects[:5]:
            print(f"     - {obj.object_name}")
    except Exception as e:
        print(f"   Error: {e}")
    
    db.close()
    print("\n" + "=" * 70)
    print("Tests Complete")
    print("=" * 70)

if __name__ == '__main__':
    asyncio.run(test_all())

