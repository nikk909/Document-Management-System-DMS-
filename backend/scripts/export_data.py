# -*- coding: utf-8 -*-
import sys
import os
import io
from pathlib import Path
import json

# 添加项目根目录到路径
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from src.storage.storage_manager import StorageManager
from src.storage.metadata_manager import MetadataManager, GeneratedDocumentMetadataManager
from src.storage.template_metadata_manager import TemplateMetadataManager
from src.storage.database import get_db_session, DocumentMetadata, TemplateMetadata, GeneratedDocumentMetadata

def export_to_testdata():
    print("[INFO] 正在将系统数据导出到 @testdata...")
    
    testdata_path = backend_root.parent / "testdata"
    input_path = testdata_path / "input"
    template_path = testdata_path / "template"
    
    # 创建目录
    input_path.mkdir(parents=True, exist_ok=True)
    template_path.mkdir(parents=True, exist_ok=True)
    
    storage = StorageManager()
    
    with get_db_session() as db:
        # 1. 导出原始数据文件 (DocumentMetadata)
        print("--- 1. 导出原始数据文件 ---")
        docs = db.query(DocumentMetadata).filter(DocumentMetadata.status == 'active').all()
        for doc in docs:
            try:
                content = storage.download_bytes(doc.minio_path, bucket=doc.bucket)
                if content:
                    file_out = input_path / doc.filename
                    with open(file_out, 'wb') as f:
                        f.write(content)
                    print(f"[OK] 导出文件: {doc.filename}")
            except Exception as e:
                print(f"[ERROR] 导出文件失败 {doc.filename}: {e}")

        # 2. 导出模板 (TemplateMetadata)
        print("--- 2. 导出模板 ---")
        templates = db.query(TemplateMetadata).filter(TemplateMetadata.is_latest == True).all()
        for tpl in templates:
            try:
                content = storage.download_bytes(tpl.minio_path, bucket=tpl.bucket)
                if content:
                    # 根据分类和格式创建目录
                    cat_name = tpl.category or "未分类"
                    fmt_name = tpl.format_type or "unknown"
                    
                    target_dir = template_path / tpl.template_name / cat_name
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    file_out = target_dir / tpl.filename
                    with open(file_out, 'wb') as f:
                        f.write(content)
                    print(f"[OK] 导出模板: {tpl.template_name} ({tpl.format_type})")
            except Exception as e:
                print(f"[ERROR] 导出模板失败 {tpl.template_name}: {e}")

    print("\n[SUCCESS] 导出完成！所有文件已保存至 @testdata 文件夹。")

if __name__ == "__main__":
    export_to_testdata()

