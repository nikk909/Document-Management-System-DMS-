# -*- coding: utf-8 -*-
"""
直接测试API功能
"""
import sys
import os
import traceback

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

def test_categories_api():
    """测试分类API"""
    print("=" * 70)
    print("测试分类API")
    print("=" * 70)
    
    try:
        from src.storage.categories import get_categories, add_category, load_categories
        from src.storage import categories as cat_module
        
        # 重置缓存
        cat_module._categories = []
        
        print("\n1. 加载分类:")
        cats = load_categories()
        print(f"   分类列表: {cats}")
        
        print("\n2. 获取分类:")
        cats = get_categories()
        print(f"   分类列表: {cats}")
        
        print("\n3. 检查分类文件:")
        from src.storage.categories import CATEGORIES_FILE
        print(f"   文件路径: {CATEGORIES_FILE}")
        print(f"   文件存在: {os.path.exists(CATEGORIES_FILE)}")
        
        if os.path.exists(CATEGORIES_FILE):
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   文件内容:\n{content}")
    except Exception as e:
        print(f"错误: {e}")
        traceback.print_exc()

def test_database_categories():
    """测试数据库分类查询"""
    print("\n" + "=" * 70)
    print("测试数据库分类查询")
    print("=" * 70)
    
    try:
        from src.storage.database import get_db_session
        from sqlalchemy import text
        
        config_path = os.path.join(backend_root, "config", "config.yaml")
        db = get_db_session(config_path=config_path)
        
        print("\n1. 查询文件分类:")
        file_result = db.execute(text("SELECT DISTINCT category FROM documents WHERE category IS NOT NULL AND category != ''"))
        file_cats = [row[0] for row in file_result if row[0]]
        print(f"   文件分类: {file_cats}")
        
        print("\n2. 查询模板分类:")
        template_result = db.execute(text("SELECT DISTINCT category FROM templates WHERE category IS NOT NULL AND category != ''"))
        template_cats = [row[0] for row in template_result if row[0]]
        print(f"   模板分类: {template_cats}")
        
        db.close()
    except Exception as e:
        print(f"错误: {e}")
        traceback.print_exc()

def test_document_generation():
    """测试文档生成功能"""
    print("\n" + "=" * 70)
    print("测试文档生成")
    print("=" * 70)
    
    try:
        from src.storage.database import get_db_session
        from sqlalchemy import text
        
        config_path = os.path.join(backend_root, "config", "config.yaml")
        db = get_db_session(config_path=config_path)
        
        # 获取test1.json的信息
        print("\n1. 获取数据文件test1.json:")
        result = db.execute(text("SELECT id, filename, minio_path, bucket FROM documents WHERE filename = 'test1.json'"))
        row = result.fetchone()
        if row:
            print(f"   ID: {row[0]}, 文件名: {row[1]}, 路径: {row[2]}, Bucket: {row[3]}")
        else:
            print("   未找到test1.json")
        
        # 获取test1模板的信息
        print("\n2. 获取模板test1:")
        result = db.execute(text("SELECT id, name, minio_path, bucket, supported_formats FROM templates WHERE name LIKE 'test1%'"))
        rows = result.fetchall()
        for row in rows:
            print(f"   ID: {row[0]}, 名称: {row[1]}, 路径: {row[2]}, Bucket: {row[3]}, 格式: {row[4]}")
        
        db.close()
    except Exception as e:
        print(f"错误: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    test_categories_api()
    test_database_categories()
    test_document_generation()

