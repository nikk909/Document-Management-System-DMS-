"""
批量更新分类脚本
将MySQL和MinIO中的分类统一更新：
- documents -> 未分类
- 脱敏测试 -> 未分类
- 财务报表 -> 未分类（模板）
- 其他不需要的分类 -> 未分类
"""
import sys
import os

# 添加backend目录到路径
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_root)

from src.storage.database import get_db_session
from src.storage.storage_manager import StorageManager
from minio.commonconfig import CopySource
from sqlalchemy import text

def update_categories():
    """批量更新分类"""
    # 分类映射：旧分类 -> 新分类（文件和模板通用）
    category_mapping = {
        'documents': '未分类',
        '脱敏测试': '未分类',
        '财务报表': '未分类',
        '人事合同': '未分类',
        '产品数据': '未分类'
    }
    
    # 获取配置文件路径
    config_path = os.path.join(backend_root, "config", "config.yaml")
    
    # 初始化存储
    storage = StorageManager()
    
    print("开始批量更新分类...")
    print(f"分类映射: {category_mapping}")
    
    total_updated = 0
    total_failed = 0
    
    # 获取数据库会话
    db = get_db_session(config_path=config_path)
    
    try:
        # 遍历每个需要更新的分类
        for old_category, new_category in category_mapping.items():
            print(f"\n处理分类: {old_category} -> {new_category}")
            
            # 使用原始SQL查询，避免ORM模型字段不匹配问题
            result = db.execute(
                text("SELECT id, filename, minio_path, bucket, category FROM documents WHERE category = :category"),
                {"category": old_category}
            )
            files_to_update = result.fetchall()
            
            print(f"找到 {len(files_to_update)} 个文件需要更新")
            
            for row in files_to_update:
                try:
                    file_id = row[0]
                    filename = row[1]
                    old_path = row[2]
                    old_bucket = row[3] or storage.bucket
                    
                    # 更新数据库分类（使用SQL直接更新）
                    db.execute(
                        text("UPDATE documents SET category = :new_category WHERE id = :file_id"),
                        {"new_category": new_category, "file_id": file_id}
                    )
                    
                    # 如果MinIO路径存在，需要移动文件
                    if old_path and old_path.startswith(f"{old_category}/"):
                        # 构建新的MinIO路径
                        path_parts = old_path.split('/', 1)
                        if len(path_parts) > 1:
                            date_and_filename = path_parts[1]
                            new_path = f"{new_category}/{date_and_filename}"
                            
                            # 获取目标bucket
                            dest_bucket = storage._get_bucket_for_category(new_category)
                            
                            # 在MinIO中移动文件
                            try:
                                # 检查源文件是否存在
                                try:
                                    storage.client.stat_object(old_bucket, old_path)
                                    
                                    # 复制文件到新路径
                                    copy_source = CopySource(
                                        bucket_name=old_bucket,
                                        object_name=old_path
                                    )
                                    storage.client.copy_object(
                                        bucket_name=dest_bucket,
                                        object_name=new_path,
                                        source=copy_source
                                    )
                                    
                                    # 复制成功后删除旧文件
                                    storage.client.remove_object(old_bucket, old_path)
                                    
                                    # 更新数据库路径和bucket
                                    db.execute(
                                        text("UPDATE documents SET minio_path = :new_path, bucket = :bucket WHERE id = :file_id"),
                                        {"new_path": new_path, "bucket": dest_bucket, "file_id": file_id}
                                    )
                                    
                                    print(f"  [OK] 文件 {filename} 已移动: {old_path} -> {new_path}")
                                except Exception as e:
                                    # 源文件不存在，只更新数据库分类，保持原路径
                                    print(f"  [WARN] 源文件不存在 {old_path}，只更新数据库分类: {e}")
                                    # minio_path不允许NULL，所以保持原路径不变
                            except Exception as e:
                                print(f"  [ERROR] MinIO移动失败 {filename}: {e}")
                                # 即使MinIO移动失败，也更新数据库分类（已在上面更新）
                        else:
                            # 路径格式不正确，只更新分类（已在上面更新）
                            print(f"  [WARN] 路径格式不正确 {old_path}，只更新数据库分类")
                    else:
                        # 没有MinIO路径或路径格式不匹配，只更新分类（已在上面更新）
                        print(f"  [WARN] 无MinIO路径或路径不匹配 {old_path}，只更新数据库分类")
                    
                    total_updated += 1
                except Exception as e:
                    filename_show = filename if 'filename' in locals() else 'unknown'
                    print(f"  [ERROR] 更新文件 {file_id} ({filename_show}) 失败: {e}")
                    total_failed += 1
            
            # 提交当前分类的更改
            try:
                db.commit()
                print(f"已提交 {old_category} -> {new_category} 的更改")
            except Exception as e:
                db.rollback()
                print(f"提交失败: {e}")
                raise
        
        # 处理模板分类更新
        print(f"\n开始处理模板分类...")
        template_total = 0
        template_failed = 0
        
        for old_category, new_category in category_mapping.items():
            if old_category in ['documents']:  # documents只用于文件，跳过
                continue
                
            print(f"\n处理模板分类: {old_category} -> {new_category}")
            
            # 查询模板
            result = db.execute(
                text("SELECT id, template_name, minio_path, bucket, category FROM templates WHERE category = :category"),
                {"category": old_category}
            )
            templates_to_update = result.fetchall()
            
            print(f"找到 {len(templates_to_update)} 个模板需要更新")
            
            for row in templates_to_update:
                try:
                    template_id = row[0]
                    template_name = row[1]
                    old_path = row[2]
                    old_bucket = row[3] or storage.bucket
                    
                    # 更新数据库分类
                    db.execute(
                        text("UPDATE templates SET category = :new_category WHERE id = :template_id"),
                        {"new_category": new_category, "template_id": template_id}
                    )
                    
                    # 如果MinIO路径存在，需要移动文件
                    # 模板路径格式可能是：templates/日期/文件名 或 分类/日期/文件名
                    if old_path:
                        # 如果路径以分类开头，直接替换
                        if old_path.startswith(f"{old_category}/"):
                            path_parts = old_path.split('/', 1)
                            if len(path_parts) > 1:
                                date_and_filename = path_parts[1]
                                new_path = f"{new_category}/{date_and_filename}"
                        # 如果路径中包含分类（如 templates/分类/日期/文件名），替换分类部分
                        elif f"/{old_category}/" in old_path:
                            new_path = old_path.replace(f"/{old_category}/", f"/{new_category}/")
                        else:
                            new_path = None
                        
                        if new_path:
                            
                            # 模板通常在templates bucket中
                            if old_bucket == 'templates' or 'template' in old_bucket.lower():
                                dest_bucket = 'templates'
                            else:
                                dest_bucket = storage._get_bucket_for_category(new_category)
                            
                            try:
                                try:
                                    storage.client.stat_object(old_bucket, old_path)
                                    
                                    copy_source = CopySource(
                                        bucket_name=old_bucket,
                                        object_name=old_path
                                    )
                                    storage.client.copy_object(
                                        bucket_name=dest_bucket,
                                        object_name=new_path,
                                        source=copy_source
                                    )
                                    
                                    storage.client.remove_object(old_bucket, old_path)
                                    
                                    db.execute(
                                        text("UPDATE templates SET minio_path = :new_path, bucket = :bucket WHERE id = :template_id"),
                                        {"new_path": new_path, "bucket": dest_bucket, "template_id": template_id}
                                    )
                                    
                                    print(f"  [OK] 模板 {template_name} 已移动: {old_path} -> {new_path}")
                                except Exception as e:
                                    print(f"  [WARN] 源文件不存在 {old_path}，只更新数据库分类: {e}")
                            except Exception as e:
                                    print(f"  [ERROR] MinIO移动失败 {template_name}: {e}")
                        else:
                            print(f"  [WARN] 无法确定新路径，只更新数据库分类")
                    else:
                        print(f"  [WARN] 无MinIO路径，只更新数据库分类")
                    
                    template_total += 1
                except Exception as e:
                    template_name_show = template_name if 'template_name' in locals() else 'unknown'
                    print(f"  [ERROR] 更新模板 {template_id} ({template_name_show}) 失败: {e}")
                    template_failed += 1
            
            # 提交模板更改
            try:
                db.commit()
                print(f"已提交模板分类 {old_category} -> {new_category} 的更改")
            except Exception as e:
                db.rollback()
                print(f"提交失败: {e}")
        
        print(f"\n批量更新完成！")
        print(f"文件 - 成功更新: {total_updated} 个，失败: {total_failed} 个")
        print(f"模板 - 成功更新: {template_total} 个，失败: {template_failed} 个")
    finally:
        db.close()
    
    # 更新分类列表（添加"未分类"到分类列表）
    try:
        from src.storage.categories import add_category, get_categories
        if '未分类' not in get_categories():
            add_category('未分类')
            print("\n已添加'未分类'到分类列表")
    except Exception as e:
        print(f"\n更新分类列表失败: {e}")

if __name__ == '__main__':
    try:
        update_categories()
    except Exception as e:
        print(f"\n脚本执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

