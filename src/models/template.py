# src/models/template.py
from typing import Dict, List
from dataclasses import dataclass, field

@dataclass
class Template:
    """Model representing a test case template configuration."""
    
    name: str
    description: str
    version: str = "1.0"
    custom_fields: List[str] = field(default_factory=list)
    column_widths: Dict[str, int] = field(default_factory=dict)
    conditional_formatting: List[Dict] = field(default_factory=list)
    
    def __post_init__(self):
        # Initialize default column widths if not provided
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
        """Add a custom field to the template."""
        if field_name not in self.custom_fields:
            self.custom_fields.append(field_name)
            self.column_widths[field_name] = 30  # Default width
    
    def remove_custom_field(self, field_name: str):
        """Remove a custom field from the template."""
        if field_name in self.custom_fields:
            self.custom_fields.remove(field_name)
            self.column_widths.pop(field_name, None)
    
    def add_conditional_formatting(self, rule: Dict):
        """Add a conditional formatting rule."""
        if self._validate_formatting_rule(rule):
            self.conditional_formatting.append(rule)
    
    def _validate_formatting_rule(self, rule: Dict) -> bool:
        """Validate conditional formatting rule."""
        required_keys = ['column', 'condition', 'format']
        return all(key in rule for key in required_keys)
    
    def to_dict(self) -> dict:
        """Convert template to dictionary format."""
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
        """Create template from dictionary."""
        return cls(
            name=data['name'],
            description=data['description'],
            version=data.get('version', '1.0'),
            custom_fields=data.get('custom_fields', []),
            column_widths=data.get('column_widths', {}),
            conditional_formatting=data.get('conditional_formatting', [])
        )