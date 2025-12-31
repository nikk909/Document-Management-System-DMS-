"""
Jinja2自定义过滤器和函数
用于模板中的数据处理
"""
import base64
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


def process_table_with_merge(table_data: List[Dict], merge_config: Dict = None) -> str:
    """
    处理表格数据，生成包含合并信息的HTML表格字符串
    
    Args:
        table_data: 表格数据列表
        merge_config: 合并配置
    
    Returns:
        HTML表格字符串
    """
    if not table_data:
        return "<table></table>"
    
    columns = list(table_data[0].keys())
    html_parts = ["<table><thead><tr>"]
    for col in columns:
        html_parts.append(f"<th>{col}</th>")
    html_parts.append("</tr></thead><tbody>")
    
    # 存储合并单元格的信息，避免重复渲染
    merged_cells = set()
    
    for r_idx, row_data in enumerate(table_data):
        html_parts.append("<tr>")
        for c_idx, col in enumerate(columns):
            if (r_idx, c_idx) in merged_cells:
                continue
            
            cell_value = row_data.get(col, '')
            # 格式化数值
            if isinstance(cell_value, float):
                if 0 < cell_value < 1:
                    # 可能是百分比
                    cell_value = f"{cell_value * 100:.1f}%"
                else:
                    cell_value = f"{cell_value:,.0f}"
            elif isinstance(cell_value, int):
                cell_value = f"{cell_value:,.0f}"
            
            cell_attrs = []
            
            # 检查是否需要合并
            if merge_config and 'merge_rows' in merge_config:
                for merge in merge_config['merge_rows']:
                    start_row = merge.get('start_row', 0)
                    end_row = merge.get('end_row', 0)
                    start_col = merge.get('start_col', 0)
                    end_col = merge.get('end_col', 0)
                    
                    # 调整为基于0的索引
                    if start_row <= r_idx <= end_row and start_col <= c_idx <= end_col:
                        if r_idx == start_row and c_idx == start_col:
                            rowspan = end_row - start_row + 1
                            colspan = end_col - start_col + 1
                            if rowspan > 1:
                                cell_attrs.append(f'rowspan="{rowspan}"')
                            if colspan > 1:
                                cell_attrs.append(f'colspan="{colspan}"')
                            
                            # 标记被合并的单元格
                            for r_merge in range(start_row, end_row + 1):
                                for c_merge in range(start_col, end_col + 1):
                                    if (r_merge != r_idx or c_merge != c_idx):
                                        merged_cells.add((r_merge, c_merge))
                        
                        # 如果当前单元格是被合并的一部分，则跳过
                        if (r_idx != start_row or c_idx != start_col) and (r_idx, c_idx) in merged_cells:
                            continue
            
            html_parts.append(f"<td {' '.join(cell_attrs)}>{cell_value}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table>")
    
    return "".join(html_parts)


def process_image_src(image_src: str, base_path: Optional[Path] = None) -> str:
    """
    处理图片源，转换为data URI
    
    Args:
        image_src: 图片源
        base_path: 基础路径
    
    Returns:
        data URI或原始路径
    """
    if isinstance(image_src, str):
        if image_src.startswith('base64:'):
            base64_data = image_src[7:]
            return f'data:image/png;base64,{base64_data}'
        elif image_src.startswith('data:image'):
            return image_src
        else:
            # 尝试读取本地文件
            path = None
            # 首先尝试直接路径
            test_path = Path(image_src.lstrip('/'))
            if test_path.exists():
                path = test_path
            # 如果不存在，尝试相对于base_path
            elif base_path:
                test_path = (base_path / image_src.lstrip('/')).resolve()
                if test_path.exists():
                    path = test_path
            # 如果还是不存在，尝试相对于当前工作目录
            if not path:
                test_path = Path.cwd() / image_src.lstrip('/')
                if test_path.exists():
                    path = test_path
            
            if path and path.exists():
                try:
                    image_data = path.read_bytes()
                    base64_str = base64.b64encode(image_data).decode('utf-8')
                    ext = path.suffix.lower()
                    img_format = 'png'
                    if ext in ['.jpg', '.jpeg']:
                        img_format = 'jpeg'
                    elif ext == '.gif':
                        img_format = 'gif'
                    return f'data:image/{img_format};base64,{base64_str}'
                except Exception as e:
                    print(f"读取图片文件失败 {path}: {e}")
                    pass
    
    return image_src


def generate_chart_image_base64(chart_data: Dict) -> Optional[str]:
    """
    生成图表并返回Base64编码的图片字符串
    
    Args:
        chart_data: 图表数据字典，包含：
            - labels: X轴标签列表
            - series: 数据系列列表，每个系列包含 name 和 points/data
            - title: 图表标题
            - x_label: X轴标签
            - y_label: Y轴标签
    
    Returns:
        Base64编码的图片字符串，失败时返回空字符串
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
        import matplotlib.pyplot as plt
        import io
        
        # 支持多种数据格式
        x_values = chart_data.get('labels', [])
        if not x_values:
            # 尝试从其他字段获取
            x_values = chart_data.get('x', [])
        
        series_list = chart_data.get('series', [])
        
        # 如果没有series，尝试从data字段获取
        if not series_list:
            data = chart_data.get('data', [])
            if data and isinstance(data, list) and len(data) > 0:
                # 如果是字典列表格式 [{x: 'Jan', y: 100}, ...]
                if isinstance(data[0], dict):
                    x_values = [item.get('x', '') for item in data]
                    y_values = [item.get('y', 0) for item in data]
                    series_list = [{'name': chart_data.get('title', '数据'), 'points': y_values}]
                # 如果是简单的y值列表
                elif isinstance(data[0], (int, float)):
                    series_list = [{'name': chart_data.get('title', '数据'), 'points': data}]
        
        if not x_values or not series_list:
            # 如果数据仍然不完整，返回空字符串
            return ""
        
        plt.figure(figsize=(10, 6))
        
        # 处理图表类型
        chart_type = chart_data.get('type', 'line')
        
        for series in series_list:
            y_values = series.get('points', series.get('data', []))
            if not y_values:
                continue
            
            series_name = series.get('name', '')
            
            if chart_type == 'bar':
                plt.bar(x_values, y_values, label=series_name)
            else:  # 默认使用折线图
                plt.plot(x_values, y_values, label=series_name, marker='o', linewidth=2)
        
        plt.title(chart_data.get('title', ''), fontsize=14, fontweight='bold')
        plt.xlabel(chart_data.get('x_label', ''), fontsize=12)
        plt.ylabel(chart_data.get('y_label', ''), fontsize=12)
        
        if len(series_list) > 1 or (len(series_list) == 1 and series_list[0].get('name')):
            plt.legend()
        
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        base64_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        return f'data:image/png;base64,{base64_str}'
    except Exception as e:
        import traceback
        print(f"生成图表图片失败: {e}")
        traceback.print_exc()
        return ""


def tojson_filter(value: Any) -> str:
    """Jinja2过滤器：将值转换为JSON字符串"""
    return json.dumps(value, ensure_ascii=False)


# Jinja2全局函数和过滤器字典
JINJA2_GLOBALS = {
    'process_table_with_merge': process_table_with_merge,
    'process_image_src': process_image_src,
    'generate_chart_image_base64': generate_chart_image_base64,
}

JINJA2_FILTERS = {
    'tojson': tojson_filter,
}

