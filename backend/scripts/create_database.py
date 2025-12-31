#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建数据库脚本
用于初始化文档元数据管理数据库
"""

import sys
from pathlib import Path

# Add backend root to Python path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from sqlalchemy import create_engine, text
from src.storage.utils import load_mysql_config


def create_database():
    """创建数据库"""
    print("=" * 60)
    print("创建存储数据库")
    print("=" * 60)
    
    # 加载配置
    config_path = backend_root / "config" / "config.yaml"
    mysql_config = load_mysql_config(str(config_path))
    
    # 连接到 MySQL 服务器（不指定数据库）
    server_url = (
        f"mysql+pymysql://{mysql_config['mysql']['user']}:{mysql_config['mysql']['password']}"
        f"@{mysql_config['mysql']['host']}:{mysql_config['mysql']['port']}"
    )
    
    engine = create_engine(server_url, echo=False)
    
    try:
        with engine.connect() as conn:
            # 创建数据库（如果不存在）
            database_name = mysql_config['mysql']['database']
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                            f"DEFAULT CHARACTER SET utf8mb4 "
                            f"DEFAULT COLLATE utf8mb4_unicode_ci"))
            conn.commit()
            print(f"[SUCCESS] 数据库 '{database_name}' 创建成功！")
            
            # 测试连接
            conn.execute(text(f"USE `{database_name}`"))
            conn.execute(text("SELECT 1"))
            print(f"[SUCCESS] 数据库连接测试成功！")
            
    except Exception as e:
        print(f"[ERROR] 创建数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        engine.dispose()
    
    return True


if __name__ == '__main__':
    success = create_database()
    if success:
        print("\n" + "=" * 60)
        print("数据库创建完成！")
        print("=" * 60)
        print("\n下一步：运行 python scripts/init_storage_db.py 初始化表结构")
    else:
        print("\n" + "=" * 60)
        print("数据库创建失败，请检查配置和 MySQL 服务状态")
        print("=" * 60)
        sys.exit(1)

