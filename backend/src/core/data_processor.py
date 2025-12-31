"""
数据处理器
统一处理 JSON/CSV 格式的输入数据，转换为标准化数据结构
"""
import json
from pathlib import Path
from typing import Union, Dict, Any, Optional
import pandas as pd
from src.models.data_models import DataStructure
from src.utils.file_utils import normalize_path


class DataProcessor:
    """
    数据处理器
    负责解析 JSON/CSV 文件，转换为标准化的数据字典
    """
    
    def __init__(self):
        """初始化数据处理器"""
        pass
    
    def process(
        self,
        data_input: Union[Dict[str, Any], Path, str],
        input_dir: Optional[Path] = None
    ) -> DataStructure:
        """
        处理输入数据（dict 或文件路径）
        符合 need.txt 要求：输入为 dict/Path
        符合 fuction.txt 要求：输入文件遵循"时间戳+文件名"命名方式，存储到 templateFile/input
        
        Args:
            data_input: 输入数据，可以是：
                - dict: 直接使用
                - Path/str: 文件路径（自动识别 JSON/CSV）
            input_dir: 输入目录（可选，用于保存输入文件的副本）
        
        Returns:
            标准化的数据结构对象
        
        Raises:
            ValueError: 如果数据格式不支持或文件不存在
            json.JSONDecodeError: 如果 JSON 解析失败
        """
        # 如果是字典，直接使用
        if isinstance(data_input, dict):
            # 创建 DataStructure，保留原始数据中的 enable_table 和 enable_chart 选项
            data_structure = DataStructure(data_input)
            # 确保 data 字段包含这些选项
            if not hasattr(data_structure, 'data') or not isinstance(data_structure.data, dict):
                data_structure.data = {}
            if 'enable_table' in data_input:
                data_structure.data['enable_table'] = data_input['enable_table']
            if 'enable_chart' in data_input:
                data_structure.data['enable_chart'] = data_input['enable_chart']
            return data_structure
        
        # 如果是路径，读取文件
        file_path = normalize_path(data_input)
        
        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")
        
        # 如果指定了输入目录，复制文件并重命名（符合 fuction.txt 要求：时间戳+文件名）
        if input_dir:
            import shutil
            import time
            
            input_dir = Path(input_dir)
            input_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成时间戳文件名：时间戳_原文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            timestamped_filename = f"{timestamp}_{file_path.name}"
            timestamped_path = input_dir / timestamped_filename
            
            # 复制文件到输入目录
            shutil.copy2(file_path, timestamped_path)
            
            # 使用时间戳文件路径继续处理
            file_path = timestamped_path
        
        # 根据文件扩展名选择解析方法
        extension = file_path.suffix.lower()
        
        if extension == '.json':
            return self._process_json(file_path)
        elif extension in ['.csv', '.tsv']:
            return self._process_csv(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {extension}")
    
    def _process_json(self, file_path: Path) -> DataStructure:
        """
        处理 JSON 文件
        智能处理复杂 JSON 结构，将嵌套数据转换为表格格式
        
        Args:
            file_path: JSON 文件路径
        
        Returns:
            标准化的数据结构对象
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证数据格式
            if not isinstance(data, dict):
                raise ValueError("JSON 文件必须包含一个字典对象")
            
            # 智能处理 JSON 数据，提取标题和表格
            processed_data = self._extract_structured_data(data, file_path.stem)
            
            return DataStructure(processed_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")
    
    def _extract_structured_data(self, json_data: Dict[str, Any], default_title: str = "数据文档") -> Dict[str, Any]:
        """
        从 JSON 数据中提取结构化信息
        自动识别标题、表格等结构化数据
        
        Args:
            json_data: JSON 数据字典
            default_title: 默认标题
        
        Returns:
            标准化的数据字典
        """
        result = {
            'title': default_title,
            'content': '',
            'tables': {},
            'charts': {},
            'images': {},
            'data': json_data  # 保留原始数据
        }
        
        # 尝试提取标题（支持document.title格式）
        if 'document' in json_data and isinstance(json_data['document'], dict):
            if 'title' in json_data['document']:
                result['title'] = json_data['document']['title']
                # 确保title不为空字符串
                if not result['title']:
                    result['title'] = default_title
        
        # 尝试提取标题（常见字段名）
        if result['title'] == default_title:
            title_fields = ['title', 'name', 'store', 'company', 'organization']
            for field in title_fields:
                if field in json_data:
                    if isinstance(json_data[field], str):
                        result['title'] = json_data[field]
                    elif isinstance(json_data[field], dict) and 'name' in json_data[field]:
                        result['title'] = json_data[field]['name']
                    break
        
        # 处理表格数据（支持table_data格式）
        if 'table_data' in json_data and isinstance(json_data['table_data'], list):
            result['tables']['table_data'] = json_data['table_data']
        
        # 处理图表数据（支持chart_data格式）
        if 'chart_data' in json_data and isinstance(json_data['chart_data'], dict):
            chart_name = json_data['chart_data'].get('title', 'chart_data')
            result['charts'][chart_name] = json_data['chart_data']
        
        # 处理图片数据（支持images数组格式）
        if 'images' in json_data and isinstance(json_data['images'], list):
            for idx, img_info in enumerate(json_data['images']):
                if isinstance(img_info, dict):
                    img_name = img_info.get('alt', f'image_{idx}')
                    # 优先使用id字段，如果没有id则使用src字段
                    img_id = img_info.get('id')
                    img_src = img_info.get('src', '')
                    if img_id is not None:
                        # 使用ID格式：image_id:31
                        result['images'][img_name] = f'image_id:{img_id}'
                    elif img_src:
                        result['images'][img_name] = img_src
        
        # 查找列表数据（可能是表格）- 保持向后兼容
        table_index = 0
        for key, value in json_data.items():
            if key in ['table_data', 'chart_data', 'images', 'document', 'table_merge']:
                continue  # 已经处理过的字段跳过
            if isinstance(value, list) and value:
                # 如果是字典列表，转换为表格
                if isinstance(value[0], dict):
                    table_name = key if key not in ['data', 'items', 'list'] else f"table_{table_index}"
                    if table_name not in result['tables']:
                        result['tables'][table_name] = value
                        table_index += 1
                # 如果是简单列表，也转换为表格
                elif len(value) > 0 and not isinstance(value[0], (dict, list)):
                    result['tables'][key] = [{'值': v} for v in value]
        
        # 递归查找嵌套的列表数据
        self._find_nested_tables(json_data, result['tables'], '')
        
        return result
    
    def _find_nested_tables(self, data: Any, tables: Dict[str, list], prefix: str):
        """
        递归查找嵌套的表格数据
        
        Args:
            data: 数据对象
            tables: 表格字典
            prefix: 前缀（用于命名）
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    table_name = f"{prefix}_{key}" if prefix else key
                    if table_name not in tables:
                        tables[table_name] = value
                elif isinstance(value, (dict, list)):
                    new_prefix = f"{prefix}_{key}" if prefix else key
                    self._find_nested_tables(value, tables, new_prefix)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._find_nested_tables(item, tables, prefix)
    
    def _process_csv(
        self,
        file_path: Path,
        auto_generate_charts: bool = True
    ) -> DataStructure:
        """
        处理 CSV 文件
        将 CSV 转换为标准化的数据结构
        符合 fuction.txt 要求：基于 CSV 数据生成折线图/柱状图
        
        Args:
            file_path: CSV 文件路径
            auto_generate_charts: 是否自动生成图表（默认 True）
        
        Returns:
            标准化的数据结构对象
        """
        try:
            # 使用 pandas 读取 CSV（自动检测分隔符：支持逗号和分号）
            # 尝试不同的分隔符
            try:
                df = pd.read_csv(file_path, encoding='utf-8', sep=',')
                # 检查是否只解析出一列，如果是，可能是分号分隔
                if len(df.columns) == 1:
                    df = pd.read_csv(file_path, encoding='utf-8', sep=';')
            except:
                # 如果失败，尝试分号分隔
                df = pd.read_csv(file_path, encoding='utf-8', sep=';')
            
            # 转换为字典格式
            # 将 DataFrame 转换为记录列表（每行一个字典）
            # 先将 NaN 值替换为 None，这样后续处理会统一显示为 "null"
            df = df.where(pd.notna(df), None)
            records = df.to_dict('records')
            
            # 构建标准化数据结构
            data = {
                'title': file_path.stem,  # 使用文件名作为标题
                'content': '',  # CSV 没有文本内容
                'tables': {
                    'data': records  # 将 CSV 数据作为表格数据
                },
                'charts': {},
                'images': {}
            }
            
            # 自动生成图表（如果启用）
            if auto_generate_charts:
                charts = self._generate_charts_from_csv(df, file_path.stem)
                data['charts'] = charts
            
            return DataStructure(data)
        except Exception as e:
            raise ValueError(f"CSV 解析失败: {e}")
    
    def _generate_charts_from_csv(
        self,
        df: pd.DataFrame,
        chart_prefix: str = 'chart'
    ) -> Dict[str, Any]:
        """
        从 CSV 数据自动生成图表
        符合 fuction.txt 要求：基于 CSV 数据生成折线图/柱状图
        实现动态图表生成（加分项4）
        
        Args:
            df: pandas DataFrame
            chart_prefix: 图表名称前缀
        
        Returns:
            图表字典，格式：{'chart_name': {'type': 'line'/'bar', 'data': {...}}}
        """
        charts = {}
        
        if df.empty:
            return charts
        
        # 识别数值列和非数值列（支持多种数值类型）
        numeric_columns = df.select_dtypes(include=['int', 'float', 'int64', 'float64', 'int32', 'float32']).columns.tolist()
        non_numeric_columns = df.select_dtypes(exclude=['int', 'float', 'int64', 'float64', 'int32', 'float32']).columns.tolist()
        
        if not numeric_columns:
            return charts
        
        # 使用第一个非数值列作为 X 轴，或者使用索引
        if non_numeric_columns:
            x_column = non_numeric_columns[0]
            x_values = df[x_column].astype(str).tolist()
            x_label = x_column
        else:
            x_values = [str(i) for i in range(len(df))]
            x_label = '序号'
        
        # 为每个数值列生成图表（动态生成）
        for idx, y_column in enumerate(numeric_columns):
            chart_name = f"{chart_prefix}_{y_column}"
            y_values = df[y_column].tolist()
            
            # 检查数据有效性
            if not y_values or len(y_values) == 0:
                continue
            
            # 生成折线图（所有数值列都生成折线图）
            charts[f"{chart_name}_line"] = {
                'type': 'line',
                'data': {
                    'x': x_values,
                    'y': y_values,
                    'title': f'{y_column} 趋势图',
                    'x_label': x_label,
                    'y_label': y_column
                }
            }
            
            # 如果数据点不多（<=20），也生成柱状图（加分项：动态图表生成）
            if len(x_values) <= 20:
                charts[f"{chart_name}_bar"] = {
                    'type': 'bar',
                    'data': {
                        'x': x_values,
                        'y': y_values,
                        'title': f'{y_column} 柱状图',
                        'x_label': x_label,
                        'y_label': y_column
                    }
                }
        
        return charts
    
    def validate_data(self, data: DataStructure, required_fields: list = None) -> list:
        """
        验证数据完整性
        检查必需字段是否存在
        
        Args:
            data: 数据结构对象
            required_fields: 必需字段列表（可选）
        
        Returns:
            问题列表，每个问题是一个字典：
            {
                'type': 'error'/'warning',
                'field': '字段名',
                'message': '错误信息'
            }
        """
        problems = []
        
        # 默认必需字段
        if required_fields is None:
            required_fields = ['title']
        
        # 检查必需字段
        for field in required_fields:
            field_value = getattr(data, field, None)
            # 如果字段值为空字符串或None，才报错
            # 但对于title字段，如果为空，改为警告而不是错误
            if not field_value:
                if field == 'title':
                    problems.append({
                        'type': 'warning',
                        'field': field,
                        'message': f'标题为空，建议在数据中提供title字段'
                    })
                else:
                    problems.append({
                        'type': 'error',
                        'field': field,
                        'message': f'必需字段缺失: {field}'
                    })
        
        # 检查表格数据格式
        if data.tables:
            for table_name, table_data in data.tables.items():
                if not isinstance(table_data, list):
                    problems.append({
                        'type': 'error',
                        'field': f'tables.{table_name}',
                        'message': f'表格数据格式错误，应为列表: {table_name}'
                    })
                elif table_data and not isinstance(table_data[0], dict):
                    problems.append({
                        'type': 'warning',
                        'field': f'tables.{table_name}',
                        'message': f'表格数据应为字典列表: {table_name}'
                    })
        
        return problems

