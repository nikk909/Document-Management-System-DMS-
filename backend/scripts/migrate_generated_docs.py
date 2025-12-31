# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, text
import yaml
import os
from pathlib import Path

def migrate():
    # 获取 backend 目录
    backend_root = Path(__file__).parent.parent
    config_path = backend_root / "config" / "config.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    mysql_config = config['mysql']
    url = f"mysql+pymysql://{mysql_config['user']}:{mysql_config['password']}@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}"
    
    engine = create_engine(url)
    
    with engine.connect() as conn:
        print("检查 generated_documents 表的列...")
        result = conn.execute(text("SHOW COLUMNS FROM generated_documents"))
        columns = [row[0] for row in result]
        
        if 'category' not in columns:
            print("正在添加 category 列...")
            conn.execute(text("ALTER TABLE generated_documents ADD COLUMN category VARCHAR(50) DEFAULT NULL AFTER is_masked"))
            conn.execute(text("ALTER TABLE generated_documents ADD INDEX idx_generated_category (category)"))
            print("category 列添加成功。")
        else:
            print("category 列已存在。")
        
        conn.commit()

if __name__ == "__main__":
    migrate()

