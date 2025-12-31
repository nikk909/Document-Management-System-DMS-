"""
文档加密工具
支持 PDF 和 Word 文档的密码保护
"""
from pathlib import Path
from typing import Optional, Union
import tempfile
import shutil


class DocumentEncryption:
    """
    文档加密工具
    支持为 PDF 和 Word 文档添加密码保护
    """
    
    @staticmethod
    def encrypt_pdf(
        input_path: Union[Path, str],
        output_path: Union[Path, str],
        password: str
    ) -> Path:
        """
        加密 PDF 文档
        符合 fuction.txt 要求：支持密码保护 PDF
        
        Args:
            input_path: 输入 PDF 文件路径
            output_path: 输出 PDF 文件路径（加密后）
            password: 密码
        
        Returns:
            加密后的文件路径
        
        Raises:
            ImportError: 如果缺少必要的库
            ValueError: 如果密码为空
        """
        if not password:
            raise ValueError("密码不能为空")
        
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        try:
            # 尝试使用 PyPDF2 加密
            from PyPDF2 import PdfReader, PdfWriter
            
            # 读取原始 PDF
            reader = PdfReader(str(input_path))
            writer = PdfWriter()
            
            # 复制所有页面
            for page in reader.pages:
                writer.add_page(page)
            
            # 添加密码保护
            writer.encrypt(user_password=password, owner_password=password)
            
            # 保存加密后的 PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                writer.write(f)
            
            return output_path
            
        except ImportError:
            # 如果 PyPDF2 不可用，尝试使用 pikepdf
            try:
                import pikepdf
                
                # 打开原始 PDF
                pdf = pikepdf.Pdf.open(str(input_path))
                
                # 保存时加密
                pdf.save(
                    str(output_path),
                    encryption=pikepdf.Encryption(
                        user=password,
                        owner=password,
                        allow=pikepdf.Permissions.all
                    )
                )
                pdf.close()
                
                return output_path
                
            except ImportError:
                raise ImportError(
                    "无法加密 PDF：需要安装 PyPDF2 或 pikepdf\n"
                    "安装命令: pip install PyPDF2 或 pip install pikepdf"
                )
    
    @staticmethod
    def encrypt_word(
        input_path: Union[Path, str],
        output_path: Union[Path, str],
        password: str
    ) -> Path:
        """
        加密 Word 文档
        符合 fuction.txt 要求：支持密码保护 Word
        
        Args:
            input_path: 输入 Word 文件路径
            output_path: 输出 Word 文件路径（加密后）
            password: 密码
        
        Returns:
            加密后的文件路径
        
        Raises:
            ValueError: 如果密码为空
            RuntimeError: 如果加密失败
        """
        if not password:
            raise ValueError("密码不能为空")
        
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        try:
            from docx import Document
            from docx.oxml import parse_xml
            from docx.oxml.ns import qn
            from docx.shared import Mm
            import zipfile
            import io
            import xml.etree.ElementTree as ET
            
            # 使用 python-docx 无法直接加密
            # 需要手动处理 docx 文件（它是 zip 文件）
            # 或者使用 COM 对象（仅 Windows）或第三方库
            
            # 方法1：使用 python-docx + zipfile 添加保护（简单密码保护）
            # 注意：这不是真正的加密，只是添加了打开密码提示
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                tmp_path = Path(tmp_file.name)
            
            try:
                # 复制原始文件到临时文件
                shutil.copy2(input_path, tmp_path)
                
                # 方法：通过修改 document.xml 添加密码提示
                # 注意：这不是真正的加密，真正的加密需要使用其他方法
                # 例如使用 COM 对象（Windows）或 msoffcrypto-tool
                
                # 尝试使用 msoffcrypto-tool（如果可用）
                try:
                    import msoffcrypto
                    
                    # 打开原始文件
                    with open(input_path, 'rb') as f:
                        office_file = msoffcrypto.OfficeFile(f)
                        office_file.load_key(password=password)
                        
                        # 保存加密后的文件
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, 'wb') as out:
                            office_file.save(out)
                    
                    return output_path
                    
                except ImportError:
                    # 如果 msoffcrypto-tool 不可用，使用简单的保护方法
                    # 复制文件并添加密码提示（需要用户手动实现）
                    raise ImportError(
                        "Word 文档加密需要安装 msoffcrypto-tool\n"
                        "安装命令: pip install msoffcrypto-tool\n"
                        "注意：需要配合 Word 软件使用 COM 接口进行真正的加密"
                    )
                
            finally:
                # 清理临时文件
                if tmp_path.exists():
                    tmp_path.unlink()
                    
        except Exception as e:
            raise RuntimeError(f"Word 文档加密失败: {e}")
    
    @staticmethod
    def encrypt_document(
        input_path: Union[Path, str],
        output_path: Union[Path, str],
        password: str,
        file_format: str
    ) -> Path:
        """
        根据格式加密文档
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            password: 密码
            file_format: 文件格式（'pdf'/'word'）
        
        Returns:
            加密后的文件路径
        """
        if file_format.lower() == 'pdf':
            return DocumentEncryption.encrypt_pdf(input_path, output_path, password)
        elif file_format.lower() == 'word':
            return DocumentEncryption.encrypt_word(input_path, output_path, password)
        else:
            raise ValueError(f"不支持的格式: {file_format}")

