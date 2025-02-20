# src/main.py
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

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
                                 template_id: str,
                                 output_path: Optional[str] = None) -> Dict:
        """Process requirements and generate test cases."""
        try:
            # Process document
            doc_content = await self.doc_processor.process_document(doc_path)
            
            # Analyze requirements
            requirements = await self.requirement_analyst.analyze(doc_content)
            
            # Design test strategy
            test_strategy = await self.test_designer.design(requirements)
            
            # Generate test cases
            test_cases = await self.test_case_writer.generate(test_strategy)
            
            # Review test cases
            reviewed_cases = await self.quality_assurance.review(test_cases)
            
            # Export test cases
            if output_path:
                await self.export_service.export_to_excel(
                    reviewed_cases, 
                    template_id,
                    output_path
                )
            
            return {
                "requirements": requirements,
                "test_strategy": test_strategy,
                "test_cases": reviewed_cases
            }
            
        except Exception as e:
            logger.error(f"Error processing requirements: {str(e)}")
            raise

async def main():
    # Example usage
    system = AITestingSystem()
    doc_path = "requirements.pdf"
    template_id = "default_template"
    output_path = "test_cases.xlsx"
    
    result = await system.process_requirements(doc_path, template_id, output_path)
    print("Test case generation completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())