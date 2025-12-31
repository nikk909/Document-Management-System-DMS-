"""
数据模型定义
用于类型提示和数据结构标准化
"""
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExportResult:
    """
    导出结果数据模型
    符合 need.txt 要求：输出为 dict/标准化文件路径
    """
    result_file: Path              # 导出文件路径
    log_file: Path                  # 导出报告路径
    problems_file: Path             # 错误日志路径
    status: str                     # 状态：'success'/'failed'
    metadata: Dict[str, Any]        # 元数据：文件大小、页数、生成耗时等
    # 存储相关字段（新增）
    storage_path: Optional[str] = None  # MinIO 存储路径
    doc_id: Optional[int] = None  # 数据库文档 ID
    version_id: Optional[str] = None  # MinIO 版本 ID


@dataclass
class TemplateVersion:
    """
    模板版本信息
    """
    version: int                    # 版本号
    timestamp: str                  # 时间戳
    file_path: Path                 # 模板文件路径（本地）
    change_log: str                 # 变更日志
    created_at: str                 # 创建时间
    # 存储位置信息（可选）
    local_path: Optional[str] = None      # 本地文件系统路径
    minio_path: Optional[str] = None      # MinIO 存储路径
    version_id: Optional[str] = None      # MinIO 版本 ID
    db_id: Optional[int] = None           # 数据库记录 ID


@dataclass
class TemplateMetadata:
    """
    模板元数据
    存储在 metadata/{模板名}_versions.json
    """
    template_name: str               # 模板名称
    current_version: int             # 当前版本号
    versions: List[TemplateVersion]  # 版本列表


class DataStructure:
    """
    标准化数据结构
    用于统一处理 JSON/CSV 输入数据
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        初始化数据结构
        
        Args:
            data: 输入数据字典，包含：
                - title: 标题
                - content: 文本内容
                - tables: 表格数据 {table_name: [{col1: val1, ...}, ...]}
                - charts: 图表数据 {chart_name: {type: 'line'/'bar', data: [...]}}
                - images: 图片数据 {image_name: path_or_base64}
        """
        self.data = data
        self.title = data.get('title', '')
        self.content = data.get('content', '')
        self.tables = data.get('tables', {})
        self.charts = data.get('charts', {})
        # 确保 images 是字典类型（如果不是，转换为字典）
        images_data = data.get('images', {})
        if isinstance(images_data, list):
            # 将列表转换为字典
            images_dict = {}
            for idx, img_info in enumerate(images_data):
                if isinstance(img_info, dict):
                    img_name = img_info.get('alt', f'image_{idx}')
                    img_src = img_info.get('src', '')
                    if img_src:
                        images_dict[img_name] = img_src
                else:
                    images_dict[f'image_{idx}'] = img_info
            self.images = images_dict
        else:
            self.images = images_data if isinstance(images_data, dict) else {}
    
    def get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取指定表格数据
        
        Args:
            table_name: 表格名称
            
        Returns:
            表格数据列表
        """
        return self.tables.get(table_name, [])
    
    def get_chart_data(self, chart_name: str) -> Dict[str, Any]:
        """
        获取指定图表数据
        
        Args:
            chart_name: 图表名称
            
        Returns:
            图表数据字典
        """
        return self.charts.get(chart_name, {})
    
    def get_image_data(self, image_name: str) -> Union[str, Path]:
        """
        获取指定图片数据（路径或 Base64）
        
        Args:
            image_name: 图片名称
            
        Returns:
            图片路径或 Base64 字符串
        """
        return self.images.get(image_name, '')



