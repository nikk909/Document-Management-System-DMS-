# -*- coding: utf-8 -*-
import sys
import os
import io
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from src.storage.storage_manager import StorageManager
from src.storage.metadata_manager import MetadataManager
from src.storage.template_metadata_manager import TemplateMetadataManager
from src.storage.database import get_db_session, User, text
import bcrypt

def bootstrap():
    print("[INFO] 正在启动系统一键初始化...")
    
    # 1. 初始化数据库表
    print("--- 1. 初始化数据库表 ---")
    try:
        from src.storage.database import DatabaseManager
        db_mgr = DatabaseManager()
        db_mgr.create_tables()
        print("[OK] 数据库表已就绪。")
    except Exception as e:
        print(f"[ERROR] 初始化表失败: {e}")

    # 2. 创建默认管理员
    print("--- 2. 创建默认管理员 ---")
    with get_db_session() as db:
        admin = db.query(User).filter(User.username == 'admin').first()
        if not admin:
            hashed = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin = User(username='admin', password=hashed, role='admin', department='IT', display_name='系统管理员')
            db.add(admin)
            db.commit()
            print("[OK] 默认管理员 admin/admin 已创建。")
        else:
            print("[INFO] 管理员已存在。")

    storage = StorageManager()
    testdata_dir = backend_root.parent / "testdata"
    
    # 3. 导入原始数据文件
    print("--- 3. 导入数据文件 ---")
    # 查找包含文件列表的目录（MinIO 导出的目录名可能包含时间戳）
    files_list_dir = None
    for item in testdata_dir.iterdir():
        if item.is_dir() and "files_list" in item.name:
            files_list_dir = item
            break
    
    if files_list_dir:
        # 递归遍历分类目录
        for category_dir in files_list_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                # 递归查找所有文件
                for file_path in category_dir.glob("**/*.*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.json', '.csv', '.jpg', '.png']:
                        try:
                            with open(file_path, 'rb') as f:
                                data = f.read()
                            
                            storage.upload_bytes(
                                data=data,
                                filename=file_path.name,
                                category=category,
                                metadata={"author": "admin", "department": "IT"}
                            )
                            print(f"[OK] 已上传数据文件: {file_path.name} (分类: {category})")
                        except Exception as e:
                            print(f"[ERROR] 上传 {file_path.name} 失败: {e}")
    else:
        # 退回到旧的 input 目录逻辑
        input_path = testdata_dir / "input"
        if input_path.exists():
            for file_path in input_path.glob("*.*"):
                if file_path.suffix.lower() in ['.json', '.csv', '.jpg', '.png']:
                    try:
                        with open(file_path, 'rb') as f:
                            data = f.read()
                        
                        category = "脱敏测试" if "test4" in file_path.name else "基础测试"
                        storage.upload_bytes(
                            data=data,
                            filename=file_path.name,
                            category=category,
                            metadata={"author": "admin", "department": "IT"}
                        )
                        print(f"[OK] 已上传数据文件: {file_path.name}")
                    except Exception as e:
                        print(f"[ERROR] 上传 {file_path.name} 失败: {e}")
    
    # 4. 导入模板
    print("--- 4. 导入模板文件 ---")
    template_path = testdata_dir / "templates" / "templates"
    if not template_path.exists():
        template_path = testdata_dir / "template" # 旧路径兼容
        
    if template_path.exists():
        # MinIO 导出的模板可能按照日期存放，我们需要提取模板名称
        # 假设格式为: templates/templates/{year}/{month}/{day}/{filename}
        # 或者旧格式: template/{template_name}/{category}/{filename}
        
        for file_path in template_path.glob("**/*.*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.docx', '.html', '.pdf']:
                try:
                    # 尝试从文件名中提取模板名称（如 test1_20251229_173332.docx -> test1）
                    filename = file_path.name
                    if "_" in filename:
                        template_name = filename.split("_")[0]
                    else:
                        template_name = file_path.stem
                    
                    # 分类逻辑
                    category = "基础测试" if "test1" in template_name or "test2" in template_name else "未分类"
                    if "test4" in template_name:
                        category = "脱敏测试"
                    
                    with open(file_path, 'rb') as f:
                        file_content = f.read()
                    
                    from src.storage.template_metadata_manager import TemplateMetadataManager
                    with TemplateMetadataManager() as tmgr:
                        ext = file_path.suffix.lower()
                        format_type = 'word' if ext == '.docx' else ext[1:]
                        
                        # 构建 MinIO 路径
                        minio_path = f"templates/{template_name}/{filename}"
                        bucket = "templates"
                        
                        # 上传到 MinIO
                        storage.client.put_object(
                            bucket, minio_path, io.BytesIO(file_content), len(file_content)
                        )
                        
                        # 保存元数据
                        tmgr.add_template(
                            template_name=template_name,
                            filename=filename,
                            minio_path=minio_path,
                            bucket=bucket,
                            format_type=format_type,
                            category=category,
                            version=1,
                            is_latest=True,
                            created_by="admin"
                        )
                    print(f"[OK] 已上传模板: {filename} (名称: {template_name}, 分类: {category})")
                except Exception as e:
                    print(f"[ERROR] 上传模板 {file_path.name} 失败: {e}")
    
    # 5. 导入图片
    print("--- 5. 导入图片库 ---")
    image_path = testdata_dir / "images" / "images"
    if image_path.exists():
        for file_path in image_path.glob("**/*.*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    
                    storage.upload_bytes(
                        data=data,
                        filename=file_path.name,
                        category="images",
                        metadata={"author": "admin", "department": "IT"}
                    )
                    print(f"[OK] 已上传图片: {file_path.name}")
                except Exception as e:
                    print(f"[ERROR] 上传图片 {file_path.name} 失败: {e}")

    print("\n[SUCCESS] 系统一键初始化完成！")

if __name__ == "__main__":
    bootstrap()
