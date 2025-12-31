"""
模板渲染辅助函数
用于Jinja2模板中的复杂数据处理（表格合并、图表数据、图片处理等）
"""
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional


def merge_table_cells(table_data: List[Dict], merge_config: Dict) -> List[List[str]]:
    """
    处理表格合并，返回合并后的表格数据
    
    Args:
        table_data: 原始表格数据列表
        merge_config: 合并配置 {'merge_rows': [...]}
    
    Returns:
        合并后的表格数据（行列表，每行是列值列表）
    """
    if not table_data or not merge_config:
        return []
    
    # 获取列名
    columns = list(table_data[0].keys())
    
    # 创建表格矩阵
    rows = []
    for row_data in table_data:
        row = [row_data.get(col, '') for col in columns]
        rows.append(row)
    
    # 标记需要合并的单元格
    merged_cells = set()
    if 'merge_rows' in merge_config:
        for merge in merge_config['merge_rows']:
            start_row = merge.get('start_row', 0)
            end_row = merge.get('end_row', 0)
            start_col = merge.get('start_col', 0)
            end_col = merge.get('end_col', 0)
            
            # 标记合并范围内的单元格（除了起始单元格）
            for row_idx in range(start_row, end_row + 1):
                for col_idx in range(start_col, end_col + 1):
                    if row_idx == start_row and col_idx == start_col:
                        continue  # 保留起始单元格
                    merged_cells.add((row_idx, col_idx))
    
    # 返回表格数据和合并信息
    return {
        'columns': columns,
        'rows': rows,
        'merged_cells': merged_cells
    }


def process_image_src(image_src: str, base_path: Optional[Path] = None) -> str:
    """
    处理图片源，将base64:前缀转换为data URI，本地路径转换为绝对路径
    
    Args:
        image_src: 图片源（base64:... 或 本地路径）
        base_path: 基础路径（用于解析相对路径）
    
    Returns:
        处理后的图片源（data URI 或 绝对路径）
    """
    if isinstance(image_src, str):
        # 处理 base64: 前缀
        if image_src.startswith('base64:'):
            base64_data = image_src[7:]  # 去掉 'base64:' 前缀
            # 尝试检测图片格式（简单检测，默认PNG）
            img_format = 'png'
            try:
                # 解码前几个字节来检测格式
                decoded = base64.b64decode(base64_data[:20])
                if decoded[:4] == b'\xff\xd8\xff\xe0':
                    img_format = 'jpeg'
                elif decoded[:8] == b'\x89PNG\r\n\x1a\n':
                    img_format = 'png'
            except:
                pass
            return f'data:image/{img_format};base64,{base64_data}'
        
        # 处理 data:image 格式（已经是data URI）
        if image_src.startswith('data:image'):
            return image_src
        
        # 处理本地路径
        if base_path:
            path = (base_path / image_src.lstrip('/')).resolve()
            if path.exists():
                # 读取文件并转换为base64
                try:
                    image_data = path.read_bytes()
                    base64_str = base64.b64encode(image_data).decode('utf-8')
                    # 检测格式
                    ext = path.suffix.lower()
                    img_format = 'png'
                    if ext in ['.jpg', '.jpeg']:
                        img_format = 'jpeg'
                    elif ext == '.gif':
                        img_format = 'gif'
                    return f'data:image/{img_format};base64,{base64_str}'
                except Exception as e:
                    print(f"处理图片路径失败 {path}: {e}")
                    return image_src
            else:
                # 文件不存在，尝试相对路径
                path = Path(image_src.lstrip('/'))
                if path.exists():
                    image_data = path.read_bytes()
                    base64_str = base64.b64encode(image_data).decode('utf-8')
                    ext = path.suffix.lower()
                    img_format = 'png'
                    if ext in ['.jpg', '.jpeg']:
                        img_format = 'jpeg'
                    elif ext == '.gif':
                        img_format = 'gif'
                    return f'data:image/{img_format};base64,{base64_str}'
    
    return image_src


def prepare_chart_data(chart_data: Dict) -> Dict:
    """
    准备图表数据，统一格式
    
    Args:
        chart_data: 原始图表数据
    
    Returns:
        标准化的图表数据字典
    """
    result = {
        'type': chart_data.get('type', 'line'),
        'title': chart_data.get('title', '图表'),
        'x_label': chart_data.get('x_label', 'X轴'),
        'y_label': chart_data.get('y_label', 'Y轴'),
        'labels': [],
        'datasets': []
    }
    
    # 提取labels
    if 'labels' in chart_data:
        result['labels'] = chart_data['labels']
    
    # 提取series数据
    if 'series' in chart_data:
        series_list = chart_data['series']
        for idx, serie in enumerate(series_list):
            dataset = {
                'label': serie.get('name', f'系列 {idx + 1}'),
                'data': serie.get('points', serie.get('data', []))
            }
            result['datasets'].append(dataset)
    
    return result


def format_value(value: Any) -> str:
    """
    格式化值，用于显示
    
    Args:
        value: 待格式化的值
    
    Returns:
        格式化后的字符串
    """
    if value is None:
        return ''
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f'{value:.2f}'
    if isinstance(value, (int, str)):
        return str(value)
    return str(value)

