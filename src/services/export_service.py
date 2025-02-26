# src/services/export_service.py
from typing import List, Dict
import pandas as pd
from pathlib import Path
import logging
import os
from models.test_case import TestCase
from models.template import Template

logger = logging.getLogger(__name__)

class ExportService:
    """Service for exporting test cases to Excel format."""
    
    def __init__(self):
        self.supported_formats = ['.xlsx']
        self.max_file_size_mb = 50  # 最大文件大小限制(MB)
    
    async def export_to_excel(self, 
                            test_cases: List[TestCase],
                            template: Template,
                            output_path: str) -> str:
        """Export test cases to Excel file using specified template."""
        try:
            # 验证输出路径
            path = Path(output_path)
            self._validate_output_path(path)
            
            # 转换测试用例到DataFrame
            df = self._convert_to_dataframe(test_cases, template)
            
            # 应用模板样式
            styled_df = self._apply_template_styling(df, template)
            
            # 导出到Excel
            self._save_to_excel(styled_df, path, template)
            
            # 验证文件大小
            self._validate_file_size(path)
            
            return str(path)
            
        except Exception as e:
            logger.error(f"Error exporting test cases: {str(e)}")
            raise
    
    def _validate_output_path(self, path: Path):
        """验证输出路径的有效性"""
        # 检查文件格式
        if path.suffix not in self.supported_formats:
            raise ValueError(f"Unsupported export format: {path.suffix}")
        
        # 检查目录是否存在
        if not path.parent.exists():
            raise ValueError(f"Output directory does not exist: {path.parent}")
        
        # 检查目录写入权限
        if not os.access(path.parent, os.W_OK):
            raise ValueError(f"No write permission for directory: {path.parent}")
        
        # 如果文件已存在，检查是否可写
        if path.exists() and not os.access(path, os.W_OK):
            raise ValueError(f"No write permission for file: {path}")
    
    def _validate_file_size(self, path: Path):
        """验证导出文件大小"""
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            path.unlink()  # 删除超大文件
            raise ValueError(f"Generated file size ({file_size_mb:.2f}MB) exceeds limit ({self.max_file_size_mb}MB)")
    
    def _convert_to_dataframe(self, 
                            test_cases: List[TestCase], 
                            template: Template) -> pd.DataFrame:
        """Convert test cases to pandas DataFrame based on template."""
        data = []
        for test_case in test_cases:
            row = {
                'ID': test_case.id,
                'Title': test_case.title,
                'Description': test_case.description,
                'Preconditions': '\n'.join(test_case.preconditions),
                'Steps': '\n'.join(test_case.steps),
                'Expected Results': '\n'.join(test_case.expected_results),
                'Priority': test_case.priority,
                'Category': test_case.category,
                'Status': test_case.status,
                'Created At': test_case.created_at,
                'Updated At': test_case.updated_at,
                'Created By': test_case.created_by,
                'Last Updated By': test_case.last_updated_by
            }
            # 添加自定义字段
            for field in template.custom_fields:
                row[field] = getattr(test_case, field, '')
            data.append(row)
        
        return pd.DataFrame(data)
    
    def _apply_template_styling(self, 
                              df: pd.DataFrame, 
                              template: Template) -> pd.DataFrame:
        """Apply template styling to DataFrame."""
        # 应用列宽 - 只转换为字符串类型，实际列宽在保存到Excel时应用
        for col, width in template.column_widths.items():
            if col in df.columns:
                df[col] = df[col].astype(str)
                
        # 应用条件格式
        for rule in template.conditional_formatting:
            if rule['column'] in df.columns and 'condition' in rule:
                try:
                    mask = df[rule['column']].str.contains(rule['condition'], na=False)
                    
                    # 应用格式 - 根据format字段的值应用不同的格式
                    if 'format' in rule:
                        format_type = rule['format']
                        if format_type == 'highlight':
                            # 高亮显示
                            df.loc[mask, rule['column']] = f"*** {df.loc[mask, rule['column']]} ***"
                        elif format_type == 'prefix':
                            # 添加前缀
                            df.loc[mask, rule['column']] = f"! {df.loc[mask, rule['column']]}"
                        elif format_type == 'uppercase':
                            # 转换为大写
                            df.loc[mask, rule['column']] = df.loc[mask, rule['column']].str.upper()
                    else:
                        # 默认格式 - 如果没有指定format
                        df.loc[mask, rule['column']] = f"*** {df.loc[mask, rule['column']]} ***"
                except Exception as e:
                    logger.warning(f"Error applying conditional format: {str(e)}")
        
        return df
    
    def _save_to_excel(self, df: pd.DataFrame, path: Path, template: Template = None):
        """Save DataFrame to Excel with formatting."""
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Test Cases')
            
            # 应用列宽
            worksheet = writer.sheets['Test Cases']
            for idx, col in enumerate(df.columns):
                # 如果模板中定义了该列的宽度，则使用模板中的宽度
                if template and col in template.column_widths:
                    worksheet.column_dimensions[chr(65 + idx)].width = template.column_widths[col]
                else:
                    # 否则自动调整列宽
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    # 设置最小和最大列宽
                    adjusted_width = min(max(max_length + 2, 10), 50)
                    worksheet.column_dimensions[chr(65 + idx)].width = adjusted_width