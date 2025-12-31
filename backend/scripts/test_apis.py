"""
测试API是否正常工作
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session, DocumentMetadata, TemplateMetadata
from sqlalchemy import text

def test_apis():
    """测试API查询"""
    config_path = os.path.join(backend_root, "config", "config.yaml")
    db = get_db_session(config_path=config_path)
    
    try:
        print("=" * 60)
        print("测试图片API查询")
        print("=" * 60)
        
        # 测试图片查询
        query = db.query(DocumentMetadata).filter(
            DocumentMetadata.status == 'active',
            DocumentMetadata.category == 'images'
        )
        
        total = query.count()
        images = query.order_by(DocumentMetadata.created_at.desc()).limit(10).all()
        
        print(f"\n图片总数: {total}")
        print(f"返回图片数: {len(images)}")
        for img in images:
            print(f"  ID: {img.id}, 文件名: {img.filename}, 分类: {img.category}")
        
        print("\n" + "=" * 60)
        print("测试模板API查询")
        print("=" * 60)
        
        # 测试模板查询
        query = db.query(TemplateMetadata).filter(TemplateMetadata.is_latest == True)
        total = query.count()
        templates = query.order_by(TemplateMetadata.template_name, TemplateMetadata.created_at.desc()).limit(10).all()
        
        print(f"\n模板总数: {total}")
        print(f"返回模板数: {len(templates)}")
        for tpl in templates:
            print(f"  ID: {tpl.id}, 名称: {tpl.template_name}, 分类: {tpl.category or 'None'}, 版本: v{tpl.version}")
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    test_apis()

