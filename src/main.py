# src/main.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from typing import Dict, Optional
from models.template import Template
import json

from agents.assistant import AssistantAgent
from agents.requirement_analyst import RequirementAnalystAgent
from agents.test_designer import TestDesignerAgent
from agents.test_case_writer import TestCaseWriterAgent
from agents.quality_assurance import QualityAssuranceAgent
from services.document_processor import DocumentProcessor
from services.test_case_generator import TestCaseGenerator
from services.export_service import ExportService
from utils.logger import setup_logger
from utils.config import load_config

logger = logging.getLogger(__name__)

class AITestingSystem:
    def __init__(self):
        self.config = load_config()
        setup_logger()
        
        # Initialize services
        self.doc_processor = DocumentProcessor()
        self.test_generator = TestCaseGenerator()
        self.export_service = ExportService()
        
        # Initialize agents
        self.requirement_analyst = RequirementAnalystAgent()
        self.test_designer = TestDesignerAgent()
        self.test_case_writer = TestCaseWriterAgent()
        self.quality_assurance = QualityAssuranceAgent()
        self.assistant = AssistantAgent(
            [self.requirement_analyst, self.test_designer, 
             self.test_case_writer, self.quality_assurance]
        )

    async def process_requirements(self,
                                 doc_path: str,
                                 template_path: str,
                                 output_path: Optional[str] = None) -> Dict:
        """Process requirements and generate test cases."""
        try:
            # Process document
            doc_content = await self.doc_processor.process_document(doc_path)
            
            # 使用assistant协调工作流程，而不是直接调用各个代理
            task = {
                'name': '测试用例生成',
                'description': doc_content
            }
            
            logger.info("开始协调工作流程")
            try:
                result = await self.assistant.coordinate_workflow(task)
                logger.info(f"工作流程协调结果: {result}")
            except Exception as e:
                logger.error(f"工作流程协调错误: {str(e)}")
                return {'status': 'error', 'message': f'工作流程协调错误: {str(e)}'}
            
            # 如果需要修改，返回错误信息
            if result.get('status') == 'needs_revision':
                logger.error(f"需求分析结果需要调整: {result.get('message')}")
                return {'status': 'error', 'message': '需求分析结果需要调整'}
            
            # 从协调结果中获取各个阶段的结果
            requirements = None
            test_strategy = None
            test_cases = None
            reviewed_cases = None
            
            for agent in self.assistant.agents:
                if isinstance(agent, RequirementAnalystAgent) and hasattr(agent, 'last_analysis'):
                    requirements = agent.last_analysis
                elif isinstance(agent, TestDesignerAgent) and hasattr(agent, 'last_design'):
                    test_strategy = agent.last_design
                elif isinstance(agent, TestCaseWriterAgent) and hasattr(agent, 'last_cases'):
                    test_cases = agent.last_cases
                elif isinstance(agent, QualityAssuranceAgent) and hasattr(agent, 'last_review'):
                    reviewed_cases = agent.last_review
            
            # 如果没有获取到审查后的测试用例，使用测试用例
            if not reviewed_cases and test_cases:
                reviewed_cases = test_cases
                
            # 如果没有获取到任何测试用例，返回错误
            if not reviewed_cases:
                logger.error("没有生成任何测试用例")
                return {'status': 'error', 'message': '没有生成任何测试用例'}
            
            # Export test cases
            if output_path and reviewed_cases:
                # 如果template_path是路径，则从文件加载模板
                if isinstance(template_path, str):
                    try:
                        with open(template_path, 'r') as f:
                            template_data = json.load(f)
                        template = Template.from_dict(template_data)
                    except Exception as e:
                        logger.error(f"Error loading template: {str(e)}")
                        # 使用默认模板
                        template = Template(
                            name="Default Template",
                            description="Default test case template"
                        )
                else:
                    # 假设template_path已经是Template对象
                    template = template_path
                
                await self.export_service.export_to_excel(
                    reviewed_cases,
                    template,
                    output_path
                )
                logger.info(f"测试用例已导出到 {output_path}")
            
            return {
                "status": "success",
                "requirements": requirements,
                "test_strategy": test_strategy,
                "test_cases": reviewed_cases,
                "workflow_result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing requirements: {str(e)}")
            raise

async def main():
    # Example usage
    system = AITestingSystem()
    doc_path = "/Users/liutao/Downloads/Auto_Generate_Test_Cases/docs/简本溯源-资质证照一键整理.pdf"
    template_path = "/Users/liutao/Downloads/Auto_Generate_Test_Cases/src/templates/functional_test_template.json"
    output_path = "test_cases.xlsx"
    
    result = await system.process_requirements(doc_path, template_path, output_path)
    
    if result.get('status') == 'success':
        print("测试用例生成成功！")
        print(f"共生成 {len(result.get('test_cases', []))} 个测试用例")
        if 'workflow_result' in result:
            print(f"工作流程状态: {result['workflow_result'].get('status', 'unknown')}")
    else:
        print(f"测试用例生成失败: {result.get('message', '未知错误')}")

if __name__ == "__main__":
    asyncio.run(main())