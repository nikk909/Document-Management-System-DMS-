"""
导出器基类
定义统一的导出接口，各格式导出器继承此基类
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from src.models.data_models import DataStructure


class BaseExporter(ABC):
    """
    导出器基类
    使用策略模式，定义统一的导出接口
    """
    
    def __init__(self):
        """初始化导出器"""
        pass
    
    @abstractmethod
    def export(
        self,
        template_path: Optional[Path],
        data: DataStructure,
        output_path: Path
    ) -> Path:
        """
        导出文档（抽象方法）
        
        Args:
            template_path: 模板文件路径
            data: 标准化的数据结构
            output_path: 输出文件路径
        
        Returns:
            生成的文档路径
        
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 export 方法")
    
    @abstractmethod
    def fill_template(
        self,
        template_path: Path,
        data: DataStructure
    ) -> Any:
        """
        填充模板数据（抽象方法）
        
        Args:
            template_path: 模板文件路径
            data: 标准化的数据结构
        
        Returns:
            填充后的文档对象（格式取决于具体实现）
        """
        raise NotImplementedError("子类必须实现 fill_template 方法")
    
    def parse_placeholder(self, text: str) -> list:
        """
        解析占位符
        识别 {{placeholder}} 格式的占位符
        
        Args:
            text: 包含占位符的文本
        
        Returns:
            占位符列表，每个元素是 (type, name, params) 元组
            例如：('text', 'title', '') 或 ('table', 'data', '')
        """
        import re
        
        # 匹配 {{xxx}} 或 {{xxx:yyy}} 格式
        pattern = r'\{\{(\w+)(?::([\w:]+))?\}\}'
        matches = re.findall(pattern, text)
        
        parsed = []
        for match in matches:
            placeholder_type = match[0]  # 占位符类型（text/table/chart/image）
            params = match[1] if match[1] else ''  # 参数部分
            
            # 根据类型解析
            if placeholder_type == 'table':
                # {{table:data}} -> ('table', 'data', '')
                parsed.append(('table', params, ''))
            elif placeholder_type == 'chart':
                # {{chart:data:line}} -> ('chart', 'data', 'line')
                parts = params.split(':')
                name = parts[0] if parts else ''
                chart_type = parts[1] if len(parts) > 1 else 'line'
                parsed.append(('chart', name, chart_type))
            elif placeholder_type == 'image':
                # {{image:logo}} -> ('image', 'logo', '')
                parsed.append(('image', params, ''))
            else:
                # 普通文本占位符 {{title}} -> ('text', 'title', '')
                parsed.append(('text', placeholder_type, ''))
        
        return parsed
    
    def replace_text_placeholder(self, text: str, data: DataStructure) -> str:
        """
        替换文本占位符
        例如：{{title}} -> 实际标题
        支持：{{variable}}、{{variable|filter}}等格式
        
        Args:
            text: 包含占位符的文本
            data: 数据结构
        
        Returns:
            替换后的文本
        """
        result = text
        
        # 替换标题
        if hasattr(data, 'title') and data.title:
            result = result.replace('{{title}}', str(data.title))
        
        # 替换内容
        if hasattr(data, 'content') and data.content:
            result = result.replace('{{content}}', str(data.content))
        
        # 替换其他文本占位符（从数据中获取）
        import re
        # 匹配 {{variable}} 或 {{variable|filter}} 格式
        pattern = r'\{\{([^}]+)\}\}'
        matches = re.findall(pattern, result)
        
        for match in matches:
            # 处理带过滤器的占位符，如 {{tasks_list|length}}
            var_name = match.split('|')[0].strip()
            
            # 尝试从tables中获取数据（用于处理CSV数据）
            if hasattr(data, 'tables') and data.tables:
                # 如果变量名是'table:xxx'格式，已经在表格处理中处理了，跳过
                if var_name.startswith('table:'):
                    continue
            
            # 尝试从data.data中获取值
            if hasattr(data, 'data') and isinstance(data.data, dict) and var_name in data.data:
                value = data.data[var_name]
                # 处理过滤器
                if '|' in match:
                    filter_part = match.split('|')[1].strip()
                    if filter_part == 'length' and isinstance(value, (list, dict)):
                        value = len(value)
                result = result.replace(f'{{{{{match}}}}}', str(value))
            # 尝试从tables中获取（用于CSV数据）
            elif hasattr(data, 'tables') and data.tables and var_name in data.tables:
                value = data.tables[var_name]
                if '|' in match:
                    filter_part = match.split('|')[1].strip()
                    if filter_part == 'length' and isinstance(value, list):
                        value = len(value)
                result = result.replace(f'{{{{{match}}}}}', str(value))
            # 尝试直接访问属性
            elif hasattr(data, var_name):
                value = getattr(data, var_name)
                if '|' in match:
                    filter_part = match.split('|')[1].strip()
                    if filter_part == 'length' and isinstance(value, (list, dict)):
                        value = len(value)
                result = result.replace(f'{{{{{match}}}}}', str(value))
        
        return result

