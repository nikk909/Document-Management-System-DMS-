# -*- coding: utf-8 -*-
"""
敏感数据脱敏模块

脱敏格式: XXX****XXXX (显示中间几位，前后用X隐藏)

支持的脱敏类型:
- 身份证号: 18位 -> XXX01199001011XXX (显示中间11位)
- 手机号: 11位 -> XXX1234XXXX (显示中间4位)
- 银行卡号: 16-19位 -> XXXX12345678XXXX (显示中间8位)
- 邮箱: -> XX****@domain.XXX
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MaskResult:
    """脱敏结果"""
    original: str
    masked: str
    mask_type: str
    position: Tuple[int, int]  # 在原文中的位置 (start, end)


class DataMasker:
    """敏感数据脱敏器"""
    
    # 正则表达式模式
    PATTERNS = {
        # 身份证号: 18位数字，最后一位可能是X
        'id_card': r'\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b',
        
        # 手机号: 1开头的11位数字
        'phone': r'\b1[3-9]\d{9}\b',
        
        # 银行卡号: 16-19位数字
        'bank_card': r'\b[3-6]\d{15,18}\b',
        
        # 邮箱
        'email': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    }
    
    def __init__(self):
        # 编译正则表达式
        self._compiled_patterns = {
            name: re.compile(pattern) 
            for name, pattern in self.PATTERNS.items()
        }
    
    def mask_id_card(self, value: str) -> str:
        """
        脱敏身份证号
        格式: XXX01199001011XXX (显示中间11位)
        
        Args:
            value: 原始身份证号
            
        Returns:
            脱敏后的字符串
        """
        if len(value) != 18:
            return value
        
        # 前3位用X，中间11位显示，后4位用X
        # 110101199001011234 -> XXX01199001011XXXX
        return 'XXX' + value[3:14] + 'XXXX'
    
    def mask_phone(self, value: str) -> str:
        """
        脱敏手机号
        格式: XXX1234XXXX (显示中间4位)
        
        Args:
            value: 原始手机号
            
        Returns:
            脱敏后的字符串
        """
        if len(value) != 11:
            return value
        
        # 前3位用X，中间4位显示，后4位用X
        # 13812345678 -> XXX1234XXXX
        return 'XXX' + value[3:7] + 'XXXX'
    
    def mask_bank_card(self, value: str) -> str:
        """
        脱敏银行卡号
        格式: XXXX12345678XXXX (显示中间8位)
        
        Args:
            value: 原始银行卡号
            
        Returns:
            脱敏后的字符串
        """
        length = len(value)
        if length < 16 or length > 19:
            return value
        
        # 前4位用X，中间8位显示，后面用X
        # 6222021234567890123 -> XXXX02123456XXXXXXX
        middle_start = 4
        middle_end = 12
        prefix_x = 'XXXX'
        suffix_x = 'X' * (length - middle_end)
        
        return prefix_x + value[middle_start:middle_end] + suffix_x
    
    def mask_email(self, value: str) -> str:
        """
        脱敏邮箱
        格式: XX****@domain.XXX (显示@和域名中间部分)
        
        Args:
            value: 原始邮箱
            
        Returns:
            脱敏后的字符串
        """
        if '@' not in value:
            return value
        
        local, domain = value.split('@', 1)
        
        # 本地部分: 前2位用X，后面用****
        if len(local) <= 2:
            masked_local = 'X' * len(local)
        else:
            masked_local = 'XX' + '****'
        
        # 域名部分: 显示中间，后缀用X
        if '.' in domain:
            domain_parts = domain.rsplit('.', 1)
            domain_name = domain_parts[0]
            suffix = domain_parts[1]
            masked_domain = domain_name + '.' + 'X' * len(suffix)
        else:
            masked_domain = domain
        
        return masked_local + '@' + masked_domain
    
    def mask_value(self, value: str, mask_type: str) -> str:
        """
        根据类型脱敏单个值
        
        Args:
            value: 原始值
            mask_type: 脱敏类型 (id_card, phone, bank_card, email, name)
            
        Returns:
            脱敏后的字符串
        """
        if mask_type == 'id_card':
            return self.mask_id_card(value)
        elif mask_type == 'phone':
            return self.mask_phone(value)
        elif mask_type == 'bank_card':
            return self.mask_bank_card(value)
        elif mask_type == 'email':
            return self.mask_email(value)
        elif mask_type == 'name':
            return self.mask_name(value)
        else:
            return value
    
    def find_sensitive_data(self, text: str, 
                           mask_types: List[str] = None) -> List[MaskResult]:
        """
        在文本中查找敏感数据
        
        Args:
            text: 要检查的文本
            mask_types: 要检查的类型列表，默认检查所有类型
            
        Returns:
            找到的敏感数据列表
        """
        if mask_types is None:
            mask_types = list(self.PATTERNS.keys())
        
        results = []
        
        for mask_type in mask_types:
            if mask_type not in self._compiled_patterns:
                continue
            
            pattern = self._compiled_patterns[mask_type]
            
            for match in pattern.finditer(text):
                original = match.group()
                masked = self.mask_value(original, mask_type)
                
                results.append(MaskResult(
                    original=original,
                    masked=masked,
                    mask_type=mask_type,
                    position=(match.start(), match.end())
                ))
        
        # 按位置排序
        results.sort(key=lambda x: x.position[0])
        
        return results
    
    def mask_text(self, text: str, 
                  mask_types: List[str] = None) -> Tuple[str, List[MaskResult]]:
        """
        脱敏文本中的所有敏感数据
        
        Args:
            text: 原始文本
            mask_types: 要脱敏的类型列表，默认脱敏所有类型
            
        Returns:
            (脱敏后的文本, 脱敏结果列表)
        """
        results = self.find_sensitive_data(text, mask_types)
        
        if not results:
            return text, []
        
        # 从后往前替换，避免位置偏移
        masked_text = text
        for result in reversed(results):
            start, end = result.position
            masked_text = masked_text[:start] + result.masked + masked_text[end:]
        
        return masked_text, results
    
    def mask_name(self, value: str) -> str:
        """
        脱敏姓名
        格式: 只显示姓氏，名字用*代替
        例如: 张三 -> 张*, 李四 -> 李*, 王五 -> 王*
        
        Args:
            value: 原始姓名
            
        Returns:
            脱敏后的字符串
        """
        if not value or len(value) == 0:
            return value
        
        # 如果只有一个字符，直接返回
        if len(value) == 1:
            return value
        
        # 显示第一个字符，后面的用*代替
        # 张三 -> 张*, 李四 -> 李*, 欧阳修 -> 欧**
        return value[0] + '*' * (len(value) - 1)
    
    def mask_dict(self, data: Dict, 
                  sensitive_fields: Dict[str, str] = None) -> Dict:
        """
        脱敏字典中的敏感字段
        
        Args:
            data: 原始字典
            sensitive_fields: 字段名到脱敏类型的映射
                             例如: {'id_number': 'id_card', 'mobile': 'phone'}
            
        Returns:
            脱敏后的字典
        """
        if sensitive_fields is None:
            # 默认的字段映射
            sensitive_fields = {
                'id_card': 'id_card',
                'id_number': 'id_card',
                'identity': 'id_card',
                '身份证号': 'id_card',
                '身份证': 'id_card',
                'phone': 'phone',
                'mobile': 'phone',
                'telephone': 'phone',
                '手机号': 'phone',
                '手机': 'phone',
                '联系电话': 'phone',
                'bank_card': 'bank_card',
                'card_number': 'bank_card',
                '银行卡号': 'bank_card',
                '银行卡': 'bank_card',
                'email': 'email',
                'mail': 'email',
                '邮箱': 'email',
                '电子邮件': 'email',
                'name': 'name',
                '姓名': 'name',
                '名字': 'name',
            }
        
        result = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # 递归处理嵌套字典
                result[key] = self.mask_dict(value, sensitive_fields)
            elif isinstance(value, str):
                # 检查字段名是否在敏感字段列表中（支持中英文字段名）
                lower_key = key.lower()
                # 同时检查原始键名和转换后的键名（支持中文）
                if lower_key in sensitive_fields or key in sensitive_fields:
                    mask_type = sensitive_fields.get(lower_key) or sensitive_fields.get(key)
                    result[key] = self.mask_value(value, mask_type)
                else:
                    # 如果不是已知的敏感字段，也尝试自动检测敏感数据（身份证、手机号、邮箱等）
                    # 这样可以脱敏嵌套在普通字段中的敏感数据
                    masked_value = value
                    # 尝试检测并脱敏敏感数据，使用 search() 而不是 match()
                    if self._compiled_patterns['id_card'].search(value):
                        masked_value = self.mask_id_card(value)
                    elif self._compiled_patterns['phone'].search(value):
                        masked_value = self.mask_phone(value)
                    elif self._compiled_patterns['email'].search(value):
                        masked_value = self.mask_email(value)
                    elif self._compiled_patterns['bank_card'].search(value):
                        masked_value = self.mask_bank_card(value)
                    result[key] = masked_value
            elif isinstance(value, list):
                # 处理列表（递归处理列表中的字典和字符串）
                masked_list = []
                for item in value:
                    if isinstance(item, dict):
                        masked_list.append(self.mask_dict(item, sensitive_fields))
                    elif isinstance(item, str):
                        # 尝试自动检测并脱敏字符串中的敏感数据
                        masked_item = item
                        if self._compiled_patterns['id_card'].search(item):
                            masked_item = self.mask_id_card(item)
                        elif self._compiled_patterns['phone'].search(item):
                            masked_item = self.mask_phone(item)
                        elif self._compiled_patterns['email'].search(item):
                            masked_item = self.mask_email(item)
                        elif self._compiled_patterns['bank_card'].search(item):
                            masked_item = self.mask_bank_card(item)
                        masked_list.append(masked_item)
                    else:
                        masked_list.append(item)
                result[key] = masked_list
            else:
                result[key] = value
        
        return result
    
    def mask_document_content(self, content: str, 
                              mask_types: List[str] = None) -> str:
        """
        脱敏文档内容（自动检测并脱敏所有敏感信息）
        
        Args:
            content: 文档内容
            mask_types: 要脱敏的类型列表
            
        Returns:
            脱敏后的内容
        """
        masked_content, _ = self.mask_text(content, mask_types)
        return masked_content


# 便捷函数
_default_masker = DataMasker()

def mask_text(text: str, mask_types: List[str] = None) -> str:
    """脱敏文本"""
    masked, _ = _default_masker.mask_text(text, mask_types)
    return masked

def mask_id_card(value: str) -> str:
    """脱敏身份证号"""
    return _default_masker.mask_id_card(value)

def mask_phone(value: str) -> str:
    """脱敏手机号"""
    return _default_masker.mask_phone(value)

def mask_bank_card(value: str) -> str:
    """脱敏银行卡号"""
    return _default_masker.mask_bank_card(value)

def mask_email(value: str) -> str:
    """脱敏邮箱"""
    return _default_masker.mask_email(value)

def mask_name(value: str) -> str:
    """脱敏姓名"""
    return _default_masker.mask_name(value)

