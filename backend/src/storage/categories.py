"""
简单的分类存储机制
使用内存中的列表存储分类，便于同步
"""
from typing import List, Set
import json
import os

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 分类存储文件路径（保存在backend目录下）
CATEGORIES_FILE = os.path.join(BASE_DIR, "categories.json")

# 默认分类列表（只保留实际使用的分类，未分类作为第一个默认分类）
DEFAULT_CATEGORIES = ["未分类", "财务报表", "任务管理", "月度报表"]

# 排除的特殊分类（这些分类有单独的管理界面）
EXCLUDED_CATEGORIES = ['templates', 'generated_documents', 'images', 'documents']

# 需要删除的不再使用的分类
REMOVED_CATEGORIES = ['人事合同', '产品数据']

# 内存中的分类列表
_categories: List[str] = []


def load_categories() -> List[str]:
    """从文件加载分类列表，如果文件不存在则使用默认分类"""
    global _categories
    
    if _categories:
        return _categories
    
    # 尝试从文件加载
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _categories = data.get('categories', DEFAULT_CATEGORIES.copy())
        except Exception as e:
            print(f"加载分类文件失败: {e}，使用默认分类")
            _categories = DEFAULT_CATEGORIES.copy()
    else:
        # 使用默认分类
        _categories = DEFAULT_CATEGORIES.copy()
        save_categories()
    
    # 保存原始数量用于检测是否需要保存
    original_count = len(_categories)
    
    # 过滤排除的分类和已删除的分类
    _categories = [c for c in _categories if c not in EXCLUDED_CATEGORIES and c not in REMOVED_CATEGORIES]
    
    # 如果删除了分类，保存更新后的列表
    if len(_categories) != original_count:
        save_categories()
    
    return _categories


def save_categories():
    """保存分类列表到文件"""
    global _categories
    try:
        data = {'categories': _categories}
        with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存分类文件失败: {e}")


def get_categories() -> List[str]:
    """获取分类列表"""
    if not _categories:
        load_categories()
    return _categories.copy()


def add_category(category: str) -> bool:
    """添加分类"""
    global _categories
    
    if not _categories:
        load_categories()
    
    category = category.strip()
    
    # 验证分类名称
    if not category:
        return False
    
    # 排除特殊分类和已删除的分类
    if category in EXCLUDED_CATEGORIES or category in REMOVED_CATEGORIES:
        return False
    
    # 如果分类已存在，不重复添加
    if category not in _categories:
        _categories.append(category)
        _categories.sort()
        save_categories()
    
    return True


def remove_category(category: str) -> bool:
    """删除分类"""
    global _categories
    
    if not _categories:
        load_categories()
    
    if category in _categories:
        _categories.remove(category)
        save_categories()
        return True
    
    return False


def update_category(old_category: str, new_category: str) -> bool:
    """更新分类名称"""
    global _categories
    
    if not _categories:
        load_categories()
    
    new_category = new_category.strip()
    
    # 验证新分类名称
    if not new_category:
        return False
    
    # 排除特殊分类
    if new_category in EXCLUDED_CATEGORIES:
        return False
    
    # 如果旧分类存在，更新它
    if old_category in _categories:
        index = _categories.index(old_category)
        _categories[index] = new_category
        _categories.sort()
        save_categories()
        return True
    
    return False


def sync_from_database(db_categories: List[str]):
    """从数据库同步分类（只添加数据库中的分类，不移除已有分类）"""
    global _categories
    
    if not _categories:
        load_categories()
    
    # 获取当前数据库中实际使用的分类
    actual_categories = set()
    for cat in db_categories:
        if cat and cat not in EXCLUDED_CATEGORIES and cat not in REMOVED_CATEGORIES:
            actual_categories.add(cat)
    
    # 只添加数据库中的新分类，不移除已有分类（用户手动添加的分类应保留）
    changed = False
    for cat in actual_categories:
        if cat not in _categories:
            _categories.append(cat)
            changed = True
    
    if changed:
        _categories.sort()
        # 确保"未分类"在第一位
        if '未分类' in _categories:
            _categories.remove('未分类')
            _categories.insert(0, '未分类')
        save_categories()

