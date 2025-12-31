"""
日志工具
统一日志格式，生成导出报告和错误日志
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from src.utils.file_utils import generate_timestamp, ensure_directory, format_file_size


class ExportLogger:
    """
    导出日志记录器
    负责生成导出报告（log）和错误日志（problems）
    """
    
    def __init__(self, log_dir: Path = None):
        """
        初始化日志记录器
        符合 fuction.txt 要求：log 保存到 output/log/，problems 保存到 output/problems/
        
        Args:
            log_dir: 日志目录路径（已弃用，保持兼容性）
        """
        # 符合 fuction.txt 要求：输出结果保存在 templateFile/output 文件夹里对应的文件夹中
        self.export_logs_dir = ensure_directory(Path("templateFile/output/log"))
        self.error_logs_dir = ensure_directory(Path("templateFile/output/problems"))
        
        # 初始化 Python logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_export_log(
        self,
        result_file: Path,
        file_format: str,
        generation_time: float,
        file_size: int = None,
        page_count: int = None,
        data_count: int = None
    ) -> Path:
        """
        创建导出报告（log_{timestamp}.txt）
        记录文件大小、页数、生成耗时等信息
        
        Args:
            result_file: 导出文件路径
            file_format: 文件格式
            generation_time: 生成耗时（秒）
            file_size: 文件大小（字节），如果为 None 则自动获取
            page_count: 页数，如果为 None 则自动获取
            data_count: 处理的数据量（可选）
        
        Returns:
            日志文件路径
        """
        # 使用结果文件名中的时间戳，而不是生成新时间戳
        # 这样确保每个格式的日志文件是独立的，不会被覆盖
        if result_file and result_file.name.startswith('result_'):
            # 从文件名提取时间戳（格式：result_YYYYMMDD_HHMMSS.ext）
            try:
                name_without_ext = result_file.stem  # result_YYYYMMDD_HHMMSS
                timestamp = '_'.join(name_without_ext.split('_')[1:3])  # YYYYMMDD_HHMMSS
                if len(timestamp.split('_')) != 2:
                    timestamp = generate_timestamp()
            except:
                timestamp = generate_timestamp()
        else:
            timestamp = generate_timestamp()
        
        log_file = self.export_logs_dir / f"log_{timestamp}.txt"
        
        # 如果没有提供文件大小，自动获取
        if file_size is None:
            file_size = result_file.stat().st_size if result_file.exists() else 0
        
        # 如果没有提供页数，尝试获取
        if page_count is None:
            from src.utils.file_utils import get_page_count
            page_count = get_page_count(result_file, file_format)
        
        # 生成日志内容
        log_content = f"""导出报告
====================
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
导出文件: {result_file}
文件格式: {file_format.upper()}
文件大小: {format_file_size(file_size)} ({file_size} 字节)
页数: {page_count}
生成耗时: {generation_time:.2f} 秒
"""
        if data_count is not None:
            log_content += f"处理数据量: {data_count} 条\n"
        
        log_content += "====================\n"
        
        # 写入日志文件
        log_file.write_text(log_content, encoding='utf-8')
        self.logger.info(f"导出报告已保存: {log_file}")
        
        return log_file
    
    def create_error_log(
        self,
        problems: List[Dict[str, Any]],
        result_file: Path = None
    ) -> Path:
        """
        创建错误日志（problems_{timestamp}.txt）
        记录格式错误、数据缺失等提示
        
        Args:
            problems: 问题列表，每个问题是一个字典：
                {
                    'type': 'error'/'warning',
                    'message': '错误信息',
                    'field': '字段名（可选）'
                }
            result_file: 关联的导出文件路径（可选）
        
        Returns:
            错误日志文件路径
        """
        # 使用结果文件名中的时间戳和格式，确保每个格式的错误日志文件是独立的
        # 格式：problems_YYYYMMDD_HHMMSS_format.txt（例如：problems_20251122_233649_pdf.txt）
        if result_file and result_file.name.startswith('result_'):
            # 从文件名提取时间戳（格式：result_YYYYMMDD_HHMMSS.ext）
            try:
                name_without_ext = result_file.stem  # result_YYYYMMDD_HHMMSS
                parts = name_without_ext.split('_')
                if len(parts) >= 3:
                    timestamp = '_'.join(parts[1:3])  # YYYYMMDD_HHMMSS
                    # 从扩展名提取格式类型
                    format_type = result_file.suffix[1:] if result_file.suffix else 'unknown'
                    # 使用格式类型作为后缀，确保不同格式的错误日志不会覆盖
                    problems_file = self.error_logs_dir / f"problems_{timestamp}_{format_type}.txt"
                else:
                    timestamp = generate_timestamp()
                    problems_file = self.error_logs_dir / f"problems_{timestamp}.txt"
            except:
                timestamp = generate_timestamp()
                problems_file = self.error_logs_dir / f"problems_{timestamp}.txt"
        else:
            timestamp = generate_timestamp()
            problems_file = self.error_logs_dir / f"problems_{timestamp}.txt"
        
        # 生成错误日志内容
        log_content = f"""错误日志
====================
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        if result_file:
            log_content += f"关联文件: {result_file}\n"
        
        log_content += f"问题总数: {len(problems)}\n"
        log_content += "====================\n\n"
        
        # 按类型分类问题
        errors = [p for p in problems if p.get('type') == 'error']
        warnings = [p for p in problems if p.get('type') == 'warning']
        
        if errors:
            log_content += f"错误 ({len(errors)} 个):\n"
            for i, problem in enumerate(errors, 1):
                log_content += f"  {i}. [{problem.get('field', 'N/A')}] {problem.get('message')}\n"
            log_content += "\n"
        
        if warnings:
            log_content += f"警告 ({len(warnings)} 个):\n"
            for i, problem in enumerate(warnings, 1):
                log_content += f"  {i}. [{problem.get('field', 'N/A')}] {problem.get('message')}\n"
            log_content += "\n"
        
        if not problems:
            log_content += "未发现问题\n"
        
        log_content += "====================\n"
        
        # 写入日志文件
        problems_file.write_text(log_content, encoding='utf-8')
        self.logger.warning(f"错误日志已保存: {problems_file}")
        
        return problems_file
    
    def log_info(self, message: str):
        """记录信息日志"""
        # 安全处理Unicode字符，避免GBK编码错误
        try:
            self.logger.info(message)
        except UnicodeEncodeError:
            # 如果编码失败，尝试使用ASCII安全版本
            safe_message = message.encode('ascii', 'ignore').decode('ascii')
            self.logger.info(safe_message)
    
    def log_warning(self, message: str):
        """记录警告日志"""
        # 安全处理Unicode字符，避免GBK编码错误
        try:
            self.logger.warning(message)
        except UnicodeEncodeError:
            # 如果编码失败，尝试使用ASCII安全版本
            safe_message = message.encode('ascii', 'ignore').decode('ascii')
            self.logger.warning(safe_message)
    
    def log_error(self, message: str):
        """记录错误日志"""
        # 安全处理Unicode字符，避免GBK编码错误
        try:
            self.logger.error(message)
        except UnicodeEncodeError:
            # 如果编码失败，尝试使用ASCII安全版本
            safe_message = message.encode('ascii', 'ignore').decode('ascii')
            self.logger.error(safe_message)

