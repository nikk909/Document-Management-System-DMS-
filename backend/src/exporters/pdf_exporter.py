"""
PDF 导出器
使用 weasyprint 将 HTML 转换为 PDF
"""
import os
from pathlib import Path
from typing import Optional

def configure_weasyprint_dll():
    """
    配置 WeasyPrint 的 DLL 路径
    自动搜索常见的 GTK+ 安装位置
    """
    gtk_paths = [
        r"C:\GTK\bin",
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
        r"C:\msys64\mingw64\bin",
        r"C:\msys64\usr\bin",
        r"C:\tools\gtk\bin",
        os.environ.get('GTK_BIN_PATH', ''),
    ]
    
    path_dirs = os.environ.get('PATH', '').split(os.pathsep)
    for path_dir in path_dirs:
        if path_dir and Path(path_dir).exists():
            dll_file = Path(path_dir) / "libgobject-2.0-0.dll"
            if dll_file.exists() and path_dir not in gtk_paths:
                gtk_paths.append(path_dir)
    
    for gtk_path in gtk_paths:
        if not gtk_path:
            continue
        path_obj = Path(gtk_path)
        if path_obj.exists():
            dll_file = path_obj / "libgobject-2.0-0.dll"
            if dll_file.exists():
                try:
                    os.add_dll_directory(str(path_obj))
                    return True, str(path_obj)
                except Exception:
                    pass
    
    return False, None

_gtk_configured, _gtk_path = configure_weasyprint_dll()

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
    WEASYPRINT_HTML = HTML
    if _gtk_configured:
        WEASYPRINT_CONFIGURED = True
        WEASYPRINT_GTK_PATH = _gtk_path
    else:
        WEASYPRINT_CONFIGURED = False
        WEASYPRINT_GTK_PATH = None
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    WEASYPRINT_HTML = None
    WEASYPRINT_ERROR = str(e)
    WEASYPRINT_CONFIGURED = False
    WEASYPRINT_GTK_PATH = None

from .html_exporter import HTMLExporter
from ..models.data_models import DataStructure


class PDFExporter(HTMLExporter):
    """
    PDF 文档导出器
    通过 HTML 作为中间格式，使用 weasyprint 转换为 PDF
    """
    
    def __init__(self):
        """初始化 PDF 导出器"""
        super().__init__()
    
    def export(
        self,
        template_path: Optional[Path],
        data: DataStructure,
        output_path: Path,
        watermark: bool = False,
        watermark_text: str = "CONFIDENTIAL",
        watermark_image_path: Optional[str] = None
    ) -> Path:
        """
        导出 PDF 文档
        
        Args:
            template_path: HTML 模板文件路径
            data: 标准化的数据结构
            output_path: 输出文件路径(.pdf)
            watermark: 是否添加水印
            watermark_text: 水印文本
            watermark_image_path: 水印图片路径
        
        Returns:
            生成的文档路径
        
        Raises:
            RuntimeError: 如果 weasyprint 不可用
        """
        if not WEASYPRINT_AVAILABLE or WEASYPRINT_HTML is None:
            error_detail = ''
            try:
                from weasyprint import HTML
                globals()['WEASYPRINT_AVAILABLE'] = True
                globals()['WEASYPRINT_HTML'] = HTML
            except Exception as e:
                error_detail = f"{type(e).__name__}: {str(e)}"
                error_msg = f"weasyprint not available"
                if error_detail:
                    error_msg += f": {error_detail}"
                raise RuntimeError(error_msg)
        
        if template_path is None or not template_path.exists():
            from src.core.default_template_generator import DefaultTemplateGenerator
            html_content = DefaultTemplateGenerator.generate_html_template(data)
        else:
            html_content = self.fill_template(template_path, data)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if WEASYPRINT_HTML is None:
            raise RuntimeError("weasyprint HTML class not available")
        
        WEASYPRINT_HTML(string=html_content).write_pdf(str(output_path))
        
        if watermark:
            from src.utils.word_protection import WordProtection
            try:
                output_path = WordProtection.add_watermark_to_pdf(
                    output_path,
                    watermark_text,
                    output_path,
                    watermark_image_path
                )
            except Exception as e:
                print(f"Warning: PDF watermark failed: {e}")
                import traceback
                traceback.print_exc()
        
        return output_path
    
    def fill_template(
        self,
        template_path: Path,
        data: DataStructure
    ) -> str:
        """
        填充 PDF 模板数据（实际是 HTML 模板）
        """
        return super().fill_template(template_path, data)
