"""
工具函数模块
提供配置加载、文件操作等辅助功能
"""

import os
import yaml
from pathlib import Path
from datetime import datetime


def load_config(config_path: str = None) -> dict:
    """
    加载 YAML 配置文件（统一配置文件）
    
    参数:
        config_path: 配置文件路径，默认为 config/config.yaml
    
    返回:
        dict: 配置字典（包含mysql、minio等所有配置）
    """
    if config_path is None:
        # 获取 backend 目录（storage -> src -> backend）
        backend_root = Path(__file__).parent.parent.parent
        config_path = backend_root / "config" / "config.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def load_mysql_config(config_path: str = None) -> dict:
    """
    加载 MySQL 配置（从统一配置文件）
    
    参数:
        config_path: 统一配置文件路径，默认为 config/config.yaml
    
    返回:
        dict: 包含mysql键的配置字典（保持向后兼容）
    """
    # 如果没有提供配置路径，使用默认的统一配置文件
    if config_path is None:
        backend_root = Path(__file__).parent.parent.parent
        config_path = str(backend_root / "config" / "config.yaml")
    
    config = load_config(config_path)
    # 返回包含mysql键的配置，保持向后兼容
    return config


def load_minio_config(config_path: str = None) -> dict:
    """
    加载 MinIO 配置（从统一配置文件）
    
    参数:
        config_path: 配置文件路径，默认为 config/config.yaml
    
    返回:
        dict: MinIO 配置字典
    """
    config = load_config(config_path)
    # 返回包含minio键的配置，保持向后兼容
    return config


def ensure_dir(directory: str) -> None:
    """
    确保目录存在，不存在则创建
    
    参数:
        directory: 目录路径
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """
    获取文件大小（字节）
    
    参数:
        file_path: 文件路径
    
    返回:
        int: 文件大小（字节）
    """
    return os.path.getsize(file_path)


def format_size(size_bytes: int) -> str:
    """
    格式化文件大小为可读格式
    
    参数:
        size_bytes: 文件大小（字节）
    
    返回:
        str: 格式化后的大小（如 "1.5 MB"）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def generate_timestamp() -> str:
    """
    生成时间戳字符串
    
    返回:
        str: 格式为 YYYYMMDD_HHMMSS 的时间戳
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_content_type(file_path: str) -> str:
    """
    根据文件扩展名获取 MIME 类型
    
    参数:
        file_path: 文件路径
    
    返回:
        str: MIME 类型
    """
    extension = Path(file_path).suffix.lower()
    
    mime_types = {
        '.txt': 'text/plain',
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.gz': 'application/gzip',
    }
    
    return mime_types.get(extension, 'application/octet-stream')


def print_separator(title: str = "", char: str = "=", length: int = 60) -> None:
    """
    打印分隔线
    
    参数:
        title: 标题文本
        char: 分隔字符
        length: 分隔线长度
    """
    if title:
        padding = (length - len(title) - 2) // 2
        print(f"\n{char * padding} {title} {char * padding}")
    else:
        print(char * length)

