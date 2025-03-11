# src/utils/cli_parser.py
import argparse
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class CLIParser:
    """命令行参数解析器，用于处理用户输入的命令行参数。"""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="自动化测试用例生成工具",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        self._setup_arguments()
    
    def _setup_arguments(self):
        """设置命令行参数"""
        # 添加文档路径参数
        self.parser.add_argument(
            "-d", "--doc", 
            dest="doc_path",
            help="需求文档路径",
            type=str,
            required=True
        )
        
        # 添加输出路径参数
        self.parser.add_argument(
            "-o", "--output",
            dest="output_path",
            help="测试用例输出路径",
            type=str,
            default="test_cases.xlsx"
        )
        
        # 添加测试类型参数
        self.parser.add_argument(
            "-t", "--type",
            dest="test_type",
            help="测试类型：functional(功能测试) 或 api(接口测试)",
            type=str,
            choices=["functional", "api"],
            default="functional"
        )
    
    def parse_args(self):
        """解析命令行参数"""
        args = self.parser.parse_args()
        
        # 验证文档路径
        if not os.path.exists(args.doc_path):
            logger.error(f"文档路径不存在: {args.doc_path}")
            raise ValueError(f"文档路径不存在: {args.doc_path}")
        
        # 根据测试类型选择模板
        template_dir = Path(__file__).parent.parent / "templates"
        
        if args.test_type == "functional":
            args.template_path = str(template_dir / "functional_test_template.json")
            logger.info(f"使用功能测试模板: {args.template_path}")
        else:  # api
            args.template_path = str(template_dir / "api_test_template.json")
            logger.info(f"使用接口测试模板: {args.template_path}")
        
        return args

def get_cli_args():
    """获取命令行参数的便捷函数"""
    parser = CLIParser()
    return parser.parse_args()