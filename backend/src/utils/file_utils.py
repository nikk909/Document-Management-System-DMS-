"""
文件操作工具
处理时间戳命名、路径管理、文件操作等
"""
from pathlib import Path
from datetime import datetime
from typing import Union, Optional
import shutil


def generate_timestamp() -> str:
    """
    生成时间戳字符串
    格式：YYYYMMDD_HHMMSS
    
    Returns:
        时间戳字符串，例如：20240115_143022
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def generate_filename(
    prefix: str,
    original_name: Optional[str] = None,
    extension: str = "",
    timestamp: Optional[str] = None
) -> str:
    """
    生成带时间戳的文件名
    符合需求：存储遵循时间戳+文件名的命名方式
    
    Args:
        prefix: 文件名前缀（如 'result', 'log', 'problems'）
        original_name: 原始文件名（可选）
        extension: 文件扩展名（如 '.docx', '.pdf', '.txt'）
        timestamp: 时间戳（可选，默认使用当前时间）
    
    Returns:
        生成的文件名，例如：result_20240115_143022.docx
    """
    if timestamp is None:
        timestamp = generate_timestamp()
    
    if original_name:
        # 移除原始文件名的扩展名
        name_without_ext = Path(original_name).stem
        return f"{timestamp}_{name_without_ext}{extension}"
    else:
        return f"{prefix}_{timestamp}{extension}"


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
    
    Returns:
        Path 对象
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小（字节）
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件大小（字节）
    """
    return Path(file_path).stat().st_size


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小（字节）
    
    Returns:
        格式化后的字符串，如 "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def safe_save_file(
    content: bytes,
    file_path: Union[str, Path],
    mode: str = 'wb'
) -> Path:
    """
    安全保存文件（先写临时文件，再重命名，避免写入失败导致文件损坏）
    
    Args:
        content: 文件内容（字节）
        file_path: 目标文件路径
        mode: 写入模式（'wb' 或 'w'）
    
    Returns:
        保存的文件路径
    """
    file_path = Path(file_path)
    ensure_directory(file_path.parent)
    
    # 先写入临时文件
    temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
    
    try:
        if mode == 'wb':
            temp_path.write_bytes(content)
        else:
            temp_path.write_text(content if isinstance(content, str) else content.decode('utf-8'))
        
        # 写入成功后重命名
        temp_path.replace(file_path)
        return file_path
    except Exception as e:
        # 如果失败，删除临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise e


def get_page_count(file_path: Union[str, Path], file_format: str) -> int:
    """
    获取文档页数（仅支持 Word 和 PDF）
    
    Args:
        file_path: 文件路径
        file_format: 文件格式（'word'/'pdf'/'html'）
    
    Returns:
        页数（HTML 返回 0）
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return 0
    
    try:
        if file_format == 'word':
            # 使用 python-docx 获取页数（需要估算）
            from docx import Document
            doc = Document(file_path)
            # python-docx 不直接支持页数，这里返回段落数作为估算
            return len(doc.paragraphs) // 20  # 粗略估算：每页约20段
        elif file_format == 'pdf':
            # 使用 PyPDF2 或 pdfplumber 获取页数
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf = PyPDF2.PdfReader(f)
                    return len(pdf.pages)
            except ImportError:
                # 如果没有 PyPDF2，返回 0
                return 0
        else:
            return 0
    except Exception:
        return 0


def normalize_path(path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """
    标准化路径（处理相对路径和绝对路径）
    
    Args:
        path: 路径字符串或 Path 对象
        base_dir: 基础目录（用于相对路径）
    
    Returns:
        标准化的 Path 对象
    """
    path_obj = Path(path)
    
    # 如果是相对路径且提供了基础目录
    if not path_obj.is_absolute() and base_dir:
        path_obj = base_dir / path_obj
    
    return path_obj.resolve()







