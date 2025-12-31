"""
HTML 导出器
使用 jinja2 模板引擎生成 HTML 文档
"""
from pathlib import Path
from typing import Optional
from jinja2 import Template, Environment, FileSystemLoader
from src.processors.table_processor import TableProcessor
from src.processors.chart_processor import ChartProcessor
from src.processors.image_processor import ImageProcessor
from src.models.data_models import DataStructure
from src.exporters.base_exporter import BaseExporter


class HTMLExporter(BaseExporter):
    """
    HTML 文档导出器
    使用 jinja2 模板引擎渲染 HTML
    """
    
    def __init__(self):
        """初始化 HTML 导出器"""
        super().__init__()
        self.table_processor = TableProcessor()
        self.chart_processor = ChartProcessor()
        self.image_processor = ImageProcessor()
        # 创建 jinja2 环境
        self.env = Environment(loader=FileSystemLoader('.'))
        # 注册自定义函数和过滤器
        from src.utils.jinja2_filters import JINJA2_GLOBALS, JINJA2_FILTERS
        self.env.globals.update(JINJA2_GLOBALS)
        self.env.filters.update(JINJA2_FILTERS)
    
    def export(
        self,
        template_path: Optional[Path],
        data: DataStructure,
        output_path: Path,
        watermark: bool = False,
        watermark_text: str = "内部使用，禁止外传",
        watermark_image_path: Optional[str] = None
    ) -> Path:
        """
        导出 HTML 文档
        
        Args:
            template_path: HTML 模板文件路径，如果为 None 则使用默认模板
            data: 标准化的数据结构
            output_path: 输出文件路径
            watermark: 是否添加水印
            watermark_text: 水印文本
            watermark_image_path: 水印图片路径
        
        Returns:
            生成的文档路径
        """
        # 如果没有模板，使用默认模板生成器
        if template_path is None or not template_path.exists():
            from src.core.default_template_generator import DefaultTemplateGenerator
            html_content = DefaultTemplateGenerator.generate_html_template(data)
        else:
            # 填充模板
            html_content = self.fill_template(template_path, data)
        
        # 添加水印（如果启用）
        if watermark:
            watermark_css = ""
            if watermark_image_path and Path(watermark_image_path).exists():
                # 图片水印：将图片转换为base64并添加到CSS中
                try:
                    import base64
                    with open(watermark_image_path, 'rb') as f:
                        image_data = f.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    image_ext = Path(watermark_image_path).suffix.lower()
                    mime_type = 'image/png' if image_ext == '.png' else 'image/jpeg' if image_ext in ['.jpg', '.jpeg'] else 'image/png'
                    watermark_css = f"""
                    <style>
                    body {{
                        position: relative;
                    }}
                    body::before {{
                        content: '';
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background-image: url('data:{mime_type};base64,{base64_image}');
                        background-repeat: repeat;
                        background-size: 400px auto;
                        opacity: 0.3;
                        pointer-events: none;
                        z-index: 9999;
                        transform: rotate(-45deg);
                        background-position: center;
                    }}
                    </style>
                    """
                except Exception as e:
                    print(f"警告：HTML图片水印失败: {e}，使用文本水印")
                    # fallback到文本水印
                    watermark_css = f"""
                    <style>
                    body::before {{
                        content: '{watermark_text}';
                        position: fixed;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%) rotate(-45deg);
                        font-size: 60px;
                        color: rgba(192, 192, 192, 0.3);
                        pointer-events: none;
                        z-index: 9999;
                        white-space: nowrap;
                    }}
                    </style>
                    """
            else:
                # 文本水印
                watermark_css = f"""
                <style>
                body::before {{
                    content: '{watermark_text}';
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-45deg);
                    font-size: 60px;
                    color: rgba(192, 192, 192, 0.3);
                    pointer-events: none;
                    z-index: 9999;
                    white-space: nowrap;
                }}
                </style>
                """
            # 将水印CSS插入到</head>之前
            if '</head>' in html_content:
                html_content = html_content.replace('</head>', watermark_css + '</head>')
            elif '<body>' in html_content:
                html_content = html_content.replace('<body>', '<head>' + watermark_css + '</head><body>')
            else:
                html_content = watermark_css + html_content
        
        # 保存文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding='utf-8')
        
        return output_path
    
    def fill_template(
        self,
        template_path: Path,
        data: DataStructure
    ) -> str:
        """
        填充 HTML 模板数据
        
        Args:
            template_path: 模板文件路径
            data: 数据结构
        
        Returns:
            填充后的 HTML 内容字符串
        """
        # 读取模板内容
        template_content = template_path.read_text(encoding='utf-8')
        
        # 替换文本占位符
        template_content = self.replace_text_placeholder(template_content, data)
        
        # 处理表格占位符
        for table_name, table_data in data.tables.items():
            template_content = self.table_processor.process_for_html(
                template_content, table_name, table_data
            )
        
        # 处理图表占位符
        for chart_name, chart_info in data.charts.items():
            chart_type = chart_info.get('type', 'line')
            # 兼容性处理：如果chart_info本身就是图表数据，则直接使用；否则使用其'data'字段
            chart_data_to_use = chart_info.get('data', chart_info) if isinstance(chart_info, dict) else chart_info
            template_content = self.chart_processor.process_for_html(
                template_content, chart_name, chart_data_to_use, chart_type
            )
        
        # 处理图片占位符
        for image_name, image_source in data.images.items():
            template_content = self.image_processor.process_for_html(
                template_content, image_name, image_source
            )
        
        # 使用 jinja2 进行最终渲染（支持更复杂的模板语法）
        try:
            template = self.env.from_string(template_content)
            # 准备模板变量（包括原始数据）
            # 添加常用Jinja2全局变量（先添加，确保不会被覆盖）
            from datetime import datetime as dt_class
            template_vars = {
                'title': data.title,
                'content': data.content,
                'tables': data.tables,
                'charts': data.charts,
                'images': data.images,
                # 提供now作为datetime对象（用于显示当前时间）
                'now': dt_class.now(),
                # 提供datetime类（用于模板中使用datetime.now()）
                'datetime': dt_class,
                # 提供一个now函数（用于模板中使用now()）
                'now_func': lambda: dt_class.now()
            }
            # 如果数据包含原始 JSON 数据（data.data），展开到模板变量中
            if hasattr(data, 'data') and isinstance(data.data, dict):
                # 直接展开 data.data 中的所有键到模板变量
                # 包括 document、table_data、table_merge、chart_data、images 等
                # 注意：这会覆盖之前设置的标准字段，确保原始数据优先
                for key, value in data.data.items():
                    if key not in template_vars:
                        template_vars[key] = value
                
                # 兼容性处理：如果模板中使用 table_data 变量（如 test3.json）
                if 'table_data' in template_vars and isinstance(template_vars['table_data'], list):
                    if 'tables' not in template_vars or not template_vars['tables']:
                        template_vars['tables'] = {'data': template_vars['table_data']}
                    elif isinstance(template_vars['tables'], dict) and 'data' not in template_vars['tables']:
                        template_vars['tables']['data'] = template_vars['table_data']
                
                # 同时保留标准化的数据结构（方便向后兼容）
                template_vars['_standardized'] = {
                    'title': data.title,
                    'tables': data.tables,
                    'charts': data.charts,
                    'images': data.images
                }
            
            return template.render(**template_vars)
        except Exception as e:
            # 如果 jinja2 渲染失败，返回已处理的模板内容
            import traceback
            print(f"Jinja2 渲染错误: {e}")
            traceback.print_exc()
            # 尝试重新渲染，这次只使用原始数据
            try:
                if hasattr(data, 'data') and isinstance(data.data, dict):
                    template = Template(template_content)
                    return template.render(**data.data)
            except:
                pass
            return template_content
