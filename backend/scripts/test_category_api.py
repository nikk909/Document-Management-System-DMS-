"""
测试分类管理API
"""
import sys
import os

backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.categories import get_categories, add_category, load_categories

def test_categories():
    """测试分类管理"""
    print("=" * 60)
    print("测试分类管理")
    print("=" * 60)
    
    # 强制重新加载
    from src.storage import categories
    categories._categories = []  # 清空缓存
    
    print("\n1. 加载分类:")
    cats = load_categories()
    print(f"  分类: {cats}")
    
    print("\n2. 获取分类:")
    cats = get_categories()
    print(f"  分类: {cats}")
    
    print("\n3. 添加测试分类:")
    result = add_category("测试分类")
    print(f"  添加结果: {result}")
    
    cats = get_categories()
    print(f"  更新后分类: {cats}")
    
    # 检查文件
    from src.storage.categories import CATEGORIES_FILE
    print(f"\n4. 分类文件路径: {CATEGORIES_FILE}")
    print(f"  文件是否存在: {os.path.exists(CATEGORIES_FILE)}")
    
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"  文件内容: {content}")

if __name__ == '__main__':
    test_categories()

