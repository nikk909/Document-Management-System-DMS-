"""
测试文件查询逻辑
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session, DocumentMetadata
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

def test_query():
    """测试查询"""
    config_path = os.path.join(backend_root, "config", "config.yaml")
    db = get_db_session(config_path=config_path)
    
    try:
        print("=" * 60)
        print("测试文件查询逻辑")
        print("=" * 60)
        
        # 模拟API的查询逻辑
        query = db.query(DocumentMetadata).filter(
            DocumentMetadata.status == 'active'
        ).filter(
            DocumentMetadata.category != 'templates'
        ).filter(
            DocumentMetadata.category != 'generated_documents'
        ).filter(
            DocumentMetadata.category != 'images'  # 图片在图片管理中显示
        )
        
        # 执行查询
        total = query.count()
        files = query.order_by(DocumentMetadata.created_at.desc()).limit(10).all()
        
        print(f"\n查询结果:")
        print(f"总数: {total}")
        print(f"返回文件数: {len(files)}")
        print("\n文件列表:")
        print("-" * 60)
        
        for doc in files:
            print(f"ID: {doc.id:3d} | 文件名: {doc.filename:20s} | 分类: {doc.category or 'None':10s} | 状态: {doc.status}")
        
        # 检查所有文件
        print("\n所有文件（包括被排除的）:")
        print("-" * 60)
        all_files = db.query(DocumentMetadata).all()
        for doc in all_files:
            excluded = " [被排除]" if doc.category in ['templates', 'generated_documents', 'images'] else ""
            print(f"ID: {doc.id:3d} | 文件名: {doc.filename:20s} | 分类: {doc.category or 'None':10s} | 状态: {doc.status}{excluded}")
        
    except Exception as e:
        print(f"\n[ERROR] 查询失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    test_query()

