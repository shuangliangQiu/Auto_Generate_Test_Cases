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
            help="需求文档路径或测试用例文件路径",
            type=str
        )
        
        # 添加输入文件参数（用于UI自动化测试）
        self.parser.add_argument(
            "-i", "--input",
            dest="input_path",
            help="测试用例文件路径（用于UI自动化测试）",
            type=str
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
            help="测试类型：functional(功能测试)、api(接口测试) 或 ui_auto(UI自动化测试)",
            type=str,
            choices=["functional", "api", "ui_auto"],
            default="functional"
        )
        
        # 添加并发数参数
        self.parser.add_argument(
            "-c", "--concurrent",
            dest="concurrent_workers",
            help="并发工作线程数，用于提高测试用例生成和审查效率",
            type=int,
            default=1
        )
    
    def parse_args(self):
        """解析命令行参数"""
        args = self.parser.parse_args()
        
        # 验证至少提供了一个输入参数
        if not args.doc_path and not args.input_path:
            logger.error("必须提供至少一个输入参数(-d/--doc 或 -i/--input)")
            raise ValueError("必须提供至少一个输入参数(-d/--doc 或 -i/--input)")
            
        # 如果是UI自动化测试，使用input_path作为测试用例文件路径
        if args.test_type == "ui_auto":
            if not args.input_path:
                args.input_path = args.doc_path
            if not os.path.exists(args.input_path):
                logger.error(f"测试用例文件不存在: {args.input_path}")
                raise ValueError(f"测试用例文件不存在: {args.input_path}")
        else:
            # 验证文档路径
            if args.doc_path and not os.path.exists(args.doc_path):
                logger.error(f"文档路径不存在: {args.doc_path}")
                raise ValueError(f"文档路径不存在: {args.doc_path}")
        
        # 根据测试类型选择模板
        template_dir = Path(__file__).parent.parent / "templates"
        
        if args.test_type == "functional":
            args.template_path = str(template_dir / "functional_test_template.json")
            logger.info(f"使用功能测试模板: {args.template_path}")
        elif args.test_type == "api":
            args.template_path = str(template_dir / "api_test_template.json")
            logger.info(f"使用接口测试模板: {args.template_path}")
        else:  # ui_auto
            args.template_path = str(template_dir / "ui_auto_test_template.json")
            logger.info(f"使用UI自动化测试模板: {args.template_path}")
        
        return args

def get_cli_args():
    """获取命令行参数的便捷函数"""
    parser = CLIParser()
    return parser.parse_args()