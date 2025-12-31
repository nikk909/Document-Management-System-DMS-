"""
模板管理器
负责模板的上传、版本管理、加载等功能
支持混合存储：本地文件系统 + MinIO + SQL
"""
import json
import shutil
import io
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
from datetime import datetime
from src.models.data_models import TemplateMetadata, TemplateVersion
from src.utils.file_utils import generate_timestamp, ensure_directory, normalize_path

# 尝试导入存储模块
try:
    from src.storage.storage_manager import StorageManager
    from src.storage.template_metadata_manager import TemplateMetadataManager
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    StorageManager = None  # 设置为 None 以避免类型注解错误
    TemplateMetadataManager = None
    print("[WARN] 存储模块未找到，模板将仅保存到本地")

# 用于类型检查
if TYPE_CHECKING:
    from src.storage.storage_manager import StorageManager as StorageManagerType
else:
    StorageManagerType = Any


class TemplateManager:
    """
    模板管理器
    实现模板的版本管理，按 "模板名_版本号_时间戳" 命名
    """
    
    def __init__(
        self, 
        template_dir: Path,
        enable_storage: bool = True,
        storage_manager: Optional[StorageManagerType] = None
    ):
        """
        初始化模板管理器
        
        存储架构：
        - 本地文件系统：templateFile/templates/（作为缓存/备份）
        - MinIO：模板文件对象存储（支持版本控制）
        - SQL：模板元数据（便于查询和管理）
        
        Args:
            template_dir: 模板根目录路径（本地文件系统）
            enable_storage: 是否启用 MinIO + SQL 存储
            storage_manager: 存储管理器实例（可选，如果不提供则自动创建）
        """
        self.template_dir = ensure_directory(template_dir)
        self.metadata_dir = ensure_directory(self.template_dir / "metadata")
        
        # 存储功能
        self.enable_storage = enable_storage and STORAGE_AVAILABLE
        self.storage_manager = storage_manager
        
        if self.enable_storage and not self.storage_manager:
            try:
                from src.storage.utils import load_config
                
                # 确保 StorageManager 可用
                if StorageManager is None:
                    self.enable_storage = False
                    print("[WARN] 存储模块未加载，模板将仅保存到本地")
                    return
                
                # 尝试从项目根目录加载配置
                project_root = template_dir.parent.parent if 'templateFile' in str(template_dir) else template_dir.parent
                config_path = project_root / "config" / "config.yaml"
                
                if config_path.exists():
                    self.storage_manager = StorageManager(config_path=str(config_path))
                else:
                    self.enable_storage = False
                    print("[WARN] MinIO 配置文件不存在，模板将仅保存到本地")
            except Exception as e:
                self.enable_storage = False
                print(f"[WARN] 存储管理器初始化失败: {e}")
                print("   模板将仅保存到本地")
    
    def upload_template(
        self,
        template_file: Union[Path, str],
        template_name: str,
        change_log: str = "上传新模板",
        auto_increment: bool = True,
        format_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> TemplateVersion:
        """
        上传模板文件
        自动生成版本号，按 "模板名_版本号_时间戳" 命名
        
        Args:
            template_file: 模板文件路径
            template_name: 模板名称
            change_log: 变更日志
            auto_increment: 是否自动递增版本号
            format_type: 模板格式类型 ('word', 'pdf', 'html')，如果为 None 则自动判断
            category: 模板分类（如 "财务报表"、"人事合同" 等），如果为 None 则从元数据中获取
        
        Returns:
            模板版本信息对象
        """
        template_file = normalize_path(template_file)
        
        if not template_file.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_file}")
        
        # 获取文件扩展名
        extension = template_file.suffix.lower()
        
        # 确定文件格式（word/pdf/html）
        if format_type is None:
            if extension == '.docx':
                format_type = 'word'
            elif extension == '.html' or extension == '.htm':
                # HTML 模板需要根据模板名称或用途判断保存位置
                # 如果模板文件名包含 'pdf' 或 'PDF'，保存到 pdf 目录
                # 否则保存到 html 目录
                template_file_lower = str(template_file).lower()
                if 'pdf' in template_file_lower:
                    format_type = 'pdf'
                else:
                    format_type = 'html'
            elif extension == '.pdf':
                # PDF 模板暂时不支持，但预留
                format_type = 'pdf'
            else:
                # 如果不支持的扩展名，抛出错误
                raise ValueError(f"不支持的模板格式: {extension}（支持: .docx, .html, .htm）")
        
        # 验证格式类型
        if format_type not in ['word', 'pdf', 'html']:
            raise ValueError(f"不支持的格式类型: {format_type}")
        
        # 验证扩展名和格式类型是否匹配
        if format_type == 'word' and extension != '.docx':
            raise ValueError(f"Word 模板必须是 .docx 格式，当前为: {extension}")
        if format_type in ['pdf', 'html'] and extension != '.html':
            raise ValueError(f"{format_type.upper()} 模板必须是 .html 格式，当前为: {extension}")
        
        # 获取或创建元数据
        metadata = self._get_or_create_metadata(template_name)
        
        # 如果提供了 category 参数，更新元数据
        if category is not None:
            metadata.category = category
        
        # 确定新版本号
        if auto_increment:
            new_version = metadata.current_version + 1
        else:
            new_version = metadata.current_version
        
        # 生成时间戳和文件名
        timestamp = generate_timestamp()
        new_filename = f"{template_name}_v{new_version}_{timestamp}{extension}"
        
        # ==================== 存储步骤 ====================
        
        # 1. 保存到本地文件系统（作为缓存/备份）
        format_dir = ensure_directory(self.template_dir / format_type)
        new_file_path = format_dir / new_filename
        shutil.copy2(template_file, new_file_path)
        local_path = str(new_file_path)
        file_size = new_file_path.stat().st_size
        
        # 2. 上传到 MinIO（如果启用）
        minio_path = None
        version_id = None
        if self.enable_storage and self.storage_manager:
            try:
                # 读取文件内容
                with open(template_file, 'rb') as f:
                    file_content = f.read()
                
                # 构建 MinIO 路径：templates/{format_type}/{template_name}/v{version}_{timestamp}.{ext}
                minio_object_path = f"templates/{format_type}/{template_name}/v{new_version}_{timestamp}{extension}"
                
                # 上传到 MinIO
                # 注意：MinIO metadata 只支持 US-ASCII 字符，需要过滤非 ASCII 字符
                # 中文信息存储在 tags 中（tags 也有限制，但可以编码）或只存储在 SQL 中
                safe_metadata = {}
                if metadata:
                    for k, v in metadata.items():
                        # 只保留 ASCII 字符的 metadata 值
                        if isinstance(v, str):
                            # 尝试编码为 ASCII，如果失败则跳过
                            try:
                                v.encode('ascii')
                                safe_metadata[k] = v
                            except UnicodeEncodeError:
                                # 非 ASCII 字符，跳过 metadata，存储在 SQL 中
                                pass
                        else:
                            safe_metadata[k] = str(v)
                
                # Tags 也需要处理非 ASCII 字符
                safe_tags = {}
                tags = getattr(metadata, 'tags', {})
                if tags:
                    for k, v in tags.items():
                        # Tags 值也需要是 ASCII
                        if isinstance(v, str):
                            try:
                                v.encode('ascii')
                                safe_tags[k] = v
                            except UnicodeEncodeError:
                                # 非 ASCII 字符，使用 URL 编码或跳过
                                import urllib.parse
                                safe_tags[k] = urllib.parse.quote(v, safe='')
                        else:
                            safe_tags[k] = str(v)
                
                upload_result = self.storage_manager.upload_bytes(
                    data=file_content,
                    filename=new_filename,
                    category="templates",
                    content_type=self._get_content_type(format_type),
                    metadata=safe_metadata,  # 只包含 ASCII 字符
                    tags=safe_tags  # 处理非 ASCII 字符
                )
                
                minio_path = upload_result.get('path')
                version_id = upload_result.get('version_id')
                
            except Exception as e:
                print(f"[WARN] 上传模板到 MinIO 失败: {e}")
                print("   模板已保存到本地文件系统")
        
        # 3. 保存元数据到 SQL（如果启用）
        template_db_id = None
        if self.enable_storage:
            try:
                from src.storage.template_metadata_manager import TemplateMetadataManager
                
                with TemplateMetadataManager() as tm_mgr:
                    template_db = tm_mgr.add_template(
                        template_name=template_name,
                        minio_path=minio_path or local_path,
                        bucket=self.storage_manager.bucket if self.storage_manager else 'local',
                        filename=new_filename,
                        format_type=format_type,
                        version=new_version,
                        file_size=file_size,
                        content_type=self._get_content_type(format_type),
                        version_id=version_id,
                        category=category or getattr(metadata, 'category', None),
                        tags=getattr(metadata, 'tags', {}),
                        change_log=change_log,
                        created_by='system',
                        is_latest=True
                    )
                    template_db_id = template_db.id
            except Exception as e:
                print(f"[WARN] 保存模板元数据到数据库失败: {e}")
        
        # 4. 保存本地 JSON 元数据（兼容旧系统）
        version_info = TemplateVersion(
            version=new_version,
            timestamp=timestamp,
            file_path=new_file_path.relative_to(self.template_dir),
            change_log=change_log,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            local_path=local_path,
            minio_path=minio_path,
            version_id=version_id,
            db_id=template_db_id
        )
        
        metadata.versions.append(version_info)
        metadata.current_version = new_version
        self._save_metadata(metadata)
        
        return version_info
    
    def _get_content_type(self, format_type: str) -> str:
        """获取内容类型"""
        content_types = {
            'word': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'pdf': 'text/html',  # PDF 模板使用 HTML 格式
            'html': 'text/html'
        }
        return content_types.get(format_type, 'application/octet-stream')
    
    def load_template(
        self,
        template_name: str,
        version: Optional[int] = None,
        format_type: Optional[str] = None
    ) -> Path:
        """
        加载模板文件
        根据 format_type 加载对应格式的模板（word/html/pdf）
        
        Args:
            template_name: 模板名称
            version: 版本号（None 表示使用最新版本）
            format_type: 格式类型（'word'/'html'/'pdf'），如果为 None 则查找所有格式
        
        Returns:
            模板文件路径
        
        Raises:
            FileNotFoundError: 如果模板不存在
        """
        metadata = self._get_metadata(template_name)
        
        if not metadata:
            raise FileNotFoundError(f"模板不存在: {template_name}")
        
        # 如果指定了格式类型，查找对应格式的模板
        if format_type:
            # 在元数据中查找指定格式的模板
            # 兼容 Windows 路径（反斜杠）和 Unix 路径（正斜杠）
            target_versions = []
            for v in metadata.versions:
                file_path_str = str(v.file_path).replace('\\', '/')  # 统一为正斜杠
                if file_path_str.startswith(f"{format_type}/"):
                    target_versions.append(v)
            
            if not target_versions:
                raise FileNotFoundError(
                    f"模板格式不存在: {template_name} ({format_type}格式)"
                )
            
            # 确定要使用的版本
            if version is None:
                # 使用该格式的最新版本（版本号最大的）
                version_info = max(target_versions, key=lambda v: v.version)
            else:
                # 查找指定版本
                version_info = None
                for v in target_versions:
                    if v.version == version:
                        version_info = v
                        break
                
                if not version_info:
                    raise FileNotFoundError(
                        f"模板版本不存在: {template_name} v{version} ({format_type}格式)"
                    )
        else:
            # 如果没有指定格式类型，使用原来的逻辑（查找所有版本）
            # 确定要使用的版本
            if version is None:
                # 使用最新版本
                target_version = metadata.current_version
            else:
                target_version = version
            
            # 查找对应版本
            version_info = None
            for v in metadata.versions:
                if v.version == target_version:
                    version_info = v
                    break
            
            if not version_info:
                raise FileNotFoundError(
                    f"模板版本不存在: {template_name} v{target_version}"
                )
        
        # 构建完整路径
        template_path = self.template_dir / version_info.file_path
        
        if not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        
        return template_path
    
    def get_template_versions(self, template_name: str) -> List[TemplateVersion]:
        """
        获取模板的所有版本
        
        Args:
            template_name: 模板名称
        
        Returns:
            版本列表
        """
        metadata = self._get_metadata(template_name)
        if not metadata:
            return []
        return metadata.versions
    
    def _get_metadata(self, template_name: str) -> Optional[TemplateMetadata]:
        """
        获取模板元数据
        
        Args:
            template_name: 模板名称
        
        Returns:
            模板元数据对象，如果不存在则返回 None
        """
        metadata_file = self.metadata_dir / f"{template_name}_versions.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换为对象
            versions = [
                TemplateVersion(**v) for v in data.get('versions', [])
            ]
            
            return TemplateMetadata(
                template_name=data['template_name'],
                current_version=data.get('current_version', 0),
                versions=versions
            )
        except Exception as e:
            print(f"读取元数据失败: {e}")
            return None
    
    def _get_or_create_metadata(self, template_name: str) -> TemplateMetadata:
        """
        获取或创建模板元数据
        
        Args:
            template_name: 模板名称
        
        Returns:
            模板元数据对象
        """
        metadata = self._get_metadata(template_name)
        
        if not metadata:
            # 创建新的元数据
            metadata = TemplateMetadata(
                template_name=template_name,
                current_version=0,
                versions=[]
            )
        
        return metadata
    
    def _save_metadata(self, metadata: TemplateMetadata):
        """
        保存模板元数据到 JSON 文件
        
        Args:
            metadata: 模板元数据对象
        """
        metadata_file = self.metadata_dir / f"{metadata.template_name}_versions.json"
        
        # 转换为字典
        data = {
            'template_name': metadata.template_name,
            'current_version': metadata.current_version,
            'versions': [
                {
                    'version': v.version,
                    'timestamp': v.timestamp,
                    'file_path': str(v.file_path),
                    'change_log': v.change_log,
                    'created_at': v.created_at
                }
                for v in metadata.versions
            ]
        }
        
        # 保存到 JSON 文件
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

