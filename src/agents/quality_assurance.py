# src/agents/quality_assurance.py
import autogen
from typing import Dict, List
import logging
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE")
model = os.getenv("OPENAI_MODEL")

class QualityAssuranceAgent:
    def __init__(self):
        self.config_list = [
            {
                "model": model,
                "api_key": api_key,
                "base_url":base_url 
            }
        ]
        
        self.agent = autogen.AssistantAgent(
            name="quality_assurance",
            system_message="""你是一位严谨的质量保证专家。你的职责是审查和改进
            测试用例，确保它们符合质量标准。""",
            llm_config={"config_list": self.config_list}
        )

    async def review(self, test_cases: List[Dict]) -> List[Dict]:
        """审查和改进测试用例。"""
        try:
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="测试用例提供者"
            )

            # 审查测试用例
            await user_proxy.initiate_chat(
                self.agent,
                message=f"""请审查以下测试用例并提供改进建议：
                
                测试用例: {test_cases}
                
                检查以下方面：
                1. 完整性
                2. 清晰度
                3. 可执行性
                4. 边界情况
                5. 错误场景"""
            )

            reviewed_cases = self._process_review(test_cases, self.agent.last_message())
            return reviewed_cases

        except Exception as e:
            logger.error(f"测试用例审查错误: {str(e)}")
            raise

    def _process_review(self, original_cases: List[Dict], review_feedback: str) -> List[Dict]:
        """处理审查反馈并更新测试用例。"""
        reviewed_cases = []
        for case in original_cases:
            improved_case = self._improve_test_case(case, review_feedback)
            reviewed_cases.append(improved_case)
        return reviewed_cases

    def _improve_test_case(self, test_case: Dict, feedback: str) -> Dict:
        """根据反馈改进测试用例。"""
        try:
            # 创建改进后的测试用例副本
            improved_case = test_case.copy()
            
            # 解析反馈内容
            feedback_sections = feedback.split('\n')
            current_section = None
            improvements = {
                'completeness': [],
                'clarity': [],
                'executability': [],
                'boundary_cases': [],
                'error_scenarios': []
            }
            
            # 提取各个方面的改进建议
            for line in feedback_sections:
                line = line.strip()
                if not line:
                    continue
                    
                if '1. 完整性' in line:
                    current_section = 'completeness'
                elif '2. 清晰度' in line:
                    current_section = 'clarity'
                elif '3. 可执行性' in line:
                    current_section = 'executability'
                elif '4. 边界情况' in line:
                    current_section = 'boundary_cases'
                elif '5. 错误场景' in line:
                    current_section = 'error_scenarios'
                elif current_section and line.startswith('-'):
                    improvements[current_section].append(line[1:].strip())
            
            # 根据反馈改进测试用例
            # 完整性改进
            if improvements['completeness']:
                if 'preconditions' not in improved_case:
                    improved_case['preconditions'] = []
                if 'steps' not in improved_case:
                    improved_case['steps'] = []
                if 'expected_results' not in improved_case:
                    improved_case['expected_results'] = []
            
            # 清晰度改进
            if improvements['clarity']:
                # 确保标题清晰明确
                if 'title' in improved_case and improved_case['title']:
                    improved_case['title'] = improved_case['title'].strip()
                # 确保步骤描述清晰
                if 'steps' in improved_case:
                    improved_case['steps'] = [step.strip() for step in improved_case['steps']]
            
            # 可执行性改进
            if improvements['executability']:
                # 确保每个步骤都有对应的预期结果
                if len(improved_case.get('steps', [])) > len(improved_case.get('expected_results', [])):
                    improved_case['expected_results'].extend(['待补充'] * 
                        (len(improved_case['steps']) - len(improved_case['expected_results'])))
            
            # 边界情况改进
            if improvements['boundary_cases']:
                # 添加边界条件测试步骤
                improved_case.setdefault('boundary_conditions', [])
                improved_case['boundary_conditions'].extend(improvements['boundary_cases'])
            
            # 错误场景改进
            if improvements['error_scenarios']:
                # 添加错误处理步骤
                improved_case.setdefault('error_scenarios', [])
                improved_case['error_scenarios'].extend(improvements['error_scenarios'])
            
            # 验证改进后的测试用例
            if not self._validate_improvements(test_case, improved_case):
                logger.warning(f"测试用例改进可能导致数据丢失: {test_case['id']}")
                return test_case
            
            return improved_case
            
        except Exception as e:
            logger.error(f"改进测试用例错误: {str(e)}")
            return test_case

    def _validate_improvements(self, original: Dict, improved: Dict) -> bool:
        """验证改进是否保持测试用例的完整性。"""
        return all(key in improved for key in original.keys())