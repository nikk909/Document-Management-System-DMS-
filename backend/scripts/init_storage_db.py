"""
初始化存储数据库
创建必要的表和索引
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import DatabaseManager

def main():
    print("=" * 60)
    print("初始化存储数据库")
    print("=" * 60)
    
    try:
        db_manager = DatabaseManager()
        
        # 测试连接
        print("\n[1/2] 测试数据库连接...")
        if db_manager.test_connection():
            print("[OK] 数据库连接成功！")
        else:
            print("[ERROR] 数据库连接失败！")
            print("   请检查 config/config.yaml 配置")
            return
        
        # 创建表
        print("\n[2/2] 创建数据库表...")
        db_manager.create_tables()
        print("[OK] 数据库表创建成功！")
        
        print("\n" + "=" * 60)
        print("数据库初始化完成！")
        print("=" * 60)
        print(f"表名: documents, templates, access_logs")
        print("\n提示：")
        print("  - 如果表已存在，不会重复创建")
        print("  - AUTO_INCREMENT 已自动修复")
        
    except Exception as e:
        print(f"\n[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

