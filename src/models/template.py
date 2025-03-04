# src/models/template.py
from typing import Dict, List
from dataclasses import dataclass, field

@dataclass
class Template:
    """测试用例模板配置的模型。"""
    
    name: str
    description: str
    version: str = "1.0"
    custom_fields: List[str] = field(default_factory=list)
    column_widths: Dict[str, int] = field(default_factory=dict)
    conditional_formatting: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        # 如果未提供列宽，则初始化默认列宽
        if not self.column_widths:
            self.column_widths = {
                'ID': 10,
                'Title': 50,
                'Description': 100,
                'Preconditions': 50,
                'Steps': 100,
                'Expected Results': 100,
                'Priority': 15,
                'Category': 20
            }
    
    def add_custom_field(self, field_name: str):
        """向模板添加自定义字段。
        
        Args:
            field_name: 要添加的字段名
            
        Raises:
            ValueError: 当字段名无效时
        """
        if not isinstance(field_name, str):
            raise ValueError("字段名必须是字符串类型")
            
        if not field_name.strip():
            raise ValueError("字段名不能为空")
            
        if field_name not in self.custom_fields:
            self.custom_fields.append(field_name)
            self.column_widths[field_name] = 30  # 默认宽度
    
    def remove_custom_field(self, field_name: str):
        """从模板中移除自定义字段。
        
        Args:
            field_name: 要移除的字段名
            
        Raises:
            ValueError: 当字段名无效时
        """
        if not isinstance(field_name, str):
            raise ValueError("字段名必须是字符串类型")
            
        if not field_name.strip():
            raise ValueError("字段名不能为空")
            
        if field_name in self.custom_fields:
            self.custom_fields.remove(field_name)
            self.column_widths.pop(field_name, None)
    
    def add_conditional_formatting(self, rule: Dict):
        """添加条件格式化规则。"""
        if self._validate_formatting_rule(rule):
            self.conditional_formatting.append(rule)
    
    def _validate_formatting_rule(self, rule: Dict) -> bool:
        """验证条件格式化规则。
        
        Args:
            rule: 包含格式化规则的字典
            
        Returns:
            bool: 规则验证是否通过
            
        Raises:
            ValueError: 当规则格式不正确时
        """
        if not isinstance(rule, dict):
            raise ValueError("格式化规则必须是字典类型")
            
        required_keys = ['column', 'condition', 'format']
        if not all(key in rule for key in required_keys):
            raise ValueError(f"格式化规则缺少必要的键: {', '.join(required_keys)}")
            
        if not isinstance(rule['column'], str) or not rule['column']:
            raise ValueError("column必须是非空字符串")
            
        if not isinstance(rule['condition'], str) or not rule['condition']:
            raise ValueError("condition必须是非空字符串")
            
        if not isinstance(rule['format'], str) or not rule['format']:
            raise ValueError("format必须是非空字符串")
            
        return True
    
    def to_dict(self) -> dict:
        """将模板转换为字典格式。"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'custom_fields': self.custom_fields,
            'column_widths': self.column_widths,
            'conditional_formatting': self.conditional_formatting
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Template':
        """从字典创建模板。"""
        # 提供默认值，以防字典中缺少必要的键
        return cls(
            data.get('name', 'Default Template'),
            data.get('description', 'Default test case template'),
            version=data.get('version', '1.0'),
            custom_fields=data.get('custom_fields', []),
            column_widths=data.get('column_widths', {}),
            conditional_formatting=data.get('conditional_formatting', [])
        )