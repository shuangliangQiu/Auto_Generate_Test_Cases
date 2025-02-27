# src/agents/quality_assurance.py
import os
import autogen
from typing import Dict, List
import logging
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

# 使用 Azure OpenAI 配置
api_key = os.getenv("AZURE_OPENAI_API_KEY")
base_url = os.getenv("AZURE_OPENAI_BASE_URL")
model = os.getenv("AZURE_OPENAI_MODEL")
model_version = os.getenv("AZURE_OPENAI_MODEL_VERSION")

class QualityAssuranceAgent:
    def __init__(self):
        self.config_list = [
            {
                "model": model,
                "api_key": api_key,
                "base_url": base_url,
                "api_type": "azure",
                "api_version": model_version
            }
        ]
        
        self.agent = autogen.AssistantAgent(
            name="quality_assurance",
            system_message='''你是一位严谨的质量保证专家。你的职责是审查和改进
            测试用例，确保它们符合质量标准。

            请按照以下 JSON 格式提供审查结果：
            {
                "reviewed_cases": [
                    {
                        "id": "TC001",
                        "title": "测试用例标题",
                        "preconditions": [
                            "前置条件1",
                            "前置条件2"
                        ],
                        "steps": [
                            "测试步骤1",
                            "测试步骤2"
                        ],
                        "expected_results": [
                            "预期结果1",
                            "预期结果2"
                        ],
                        "priority": "P0",
                        "category": "功能测试",
                        "boundary_conditions": [
                            "边界条件1",
                            "边界条件2"
                        ],
                        "error_scenarios": [
                            "错误场景1",
                            "错误场景2"
                        ]
                    }
                ],
                "review_comments": [
                    {
                        "case_id": "TC001",
                        "completeness": ["完整性建议1", "完整性建议2"],
                        "clarity": ["清晰度建议1", "清晰度建议2"],
                        "executability": ["可执行性建议1", "可执行性建议2"],
                        "boundary_cases": ["边界情况建议1", "边界情况建议2"],
                        "error_scenarios": ["错误场景建议1", "错误场景建议2"]
                    }
                ]
            }

            注意：
            1. 所有输出必须严格遵循上述 JSON 格式
            2. 每个数组至少包含一个有效项
            3. 所有文本必须使用双引号
            4. JSON 必须是有效的且可解析的
            5. 每个测试用例必须包含所有必需字段''',
            llm_config={"config_list": self.config_list}
        )
        
        # 添加last_review属性，用于跟踪最近的审查结果
        self.last_review = None

    def review(self, test_cases: List[Dict]) -> List[Dict]:
        """审查和改进测试用例。"""
        try:
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="测试用例提供者",
                human_input_mode="NEVER",
                code_execution_config={"use_docker": False}
            )

            # 审查测试用例
            user_proxy.initiate_chat(
                self.agent,
                message=f"""请审查以下测试用例并提供改进建议：
                
                测试用例: {test_cases}
                
                检查以下方面：
                1. 完整性
                2. 清晰度
                3. 可执行性
                4. 边界情况
                5. 错误场景""",
                max_turns=1  # 限制对话轮次为1，避免死循环
            )

            reviewed_cases = self._process_review(test_cases, self.agent.last_message())
            
            # 如果审查结果为空，返回原始测试用例
            if not reviewed_cases:
                logger.warning("测试用例审查结果为空，返回原始测试用例")
                return test_cases
            
            # 保存审查结果到last_review属性
            self.last_review = reviewed_cases
            logger.info(f"测试用例审查完成，共审查 {len(reviewed_cases)} 个测试用例")
            
            return reviewed_cases

        except Exception as e:
            logger.error(f"测试用例审查错误: {str(e)}")
            raise

    def _process_review(self, original_cases: List[Dict], review_feedback) -> List[Dict]:
        """处理审查反馈并更新测试用例。"""
        reviewed_cases = []
        for case in original_cases:
            improved_case = self._improve_test_case(case, review_feedback)
            reviewed_cases.append(improved_case)
        return reviewed_cases

    def _improve_test_case(self, test_case: Dict, feedback) -> Dict:
        """根据反馈改进测试用例。"""
        try:
            if not test_case:
                logger.warning("测试用例为空")
                return test_case
                
            if not feedback:
                logger.warning("反馈为空")
                return test_case

            # 创建改进后的测试用例副本
            improved_case = test_case.copy()
            
            # 检查feedback类型
            if isinstance(feedback, dict):
                # 如果是字典类型，尝试从content字段获取内容
                if 'content' in feedback:
                    feedback = feedback['content']
                else:
                    logger.error(f"无法从字典中提取反馈内容: {feedback}")
                    return test_case
            
            # 确保feedback是字符串类型
            if not isinstance(feedback, str):
                logger.error(f"反馈不是字符串类型: {type(feedback)}")
                return test_case
                
            # 解析反馈内容
            feedback_sections = [line.strip() for line in feedback.split('\n') if line.strip()]
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
                # 识别章节标题
                section_mapping = {
                    '1. 完整性': 'completeness',
                    '2. 清晰度': 'clarity',
                    '3. 可执行性': 'executability',
                    '4. 边界情况': 'boundary_cases',
                    '5. 错误场景': 'error_scenarios'
                }
                
                for title, section in section_mapping.items():
                    if title in line:
                        current_section = section
                        break
                
                # 提取建议内容
                if current_section and (line.startswith('-') or line.startswith('•')):
                    content = line[1:].strip()
                    if content:  # 确保内容不为空
                        improvements[current_section].append(content)
            
            # 根据反馈改进测试用例
            # 完整性改进
            if improvements['completeness']:
                required_fields = ['preconditions', 'steps', 'expected_results']
                for field in required_fields:
                    if field not in improved_case:
                        improved_case[field] = []
                    elif not isinstance(improved_case[field], list):
                        improved_case[field] = [improved_case[field]]
            
            # 清晰度改进
            if improvements['clarity']:
                # 确保标题清晰明确
                if 'title' in improved_case:
                    improved_case['title'] = improved_case['title'].strip() if improved_case['title'] else ''
                # 确保步骤描述清晰
                if 'steps' in improved_case:
                    improved_case['steps'] = [step.strip() for step in improved_case['steps'] if step]
            
            # 可执行性改进
            if improvements['executability']:
                steps = improved_case.get('steps', [])
                results = improved_case.get('expected_results', [])
                if steps:
                    # 确保每个步骤都有对应的预期结果
                    if len(steps) > len(results):
                        results.extend(['待补充'] * (len(steps) - len(results)))
                    improved_case['expected_results'] = results
            
            # 边界情况改进
            if improvements['boundary_cases']:
                boundary_conditions = improved_case.setdefault('boundary_conditions', [])
                # 去重并添加新的边界条件
                new_conditions = [cond for cond in improvements['boundary_cases'] 
                                if cond not in boundary_conditions]
                boundary_conditions.extend(new_conditions)
            
            # 错误场景改进
            if improvements['error_scenarios']:
                error_scenarios = improved_case.setdefault('error_scenarios', [])
                # 去重并添加新的错误场景
                new_scenarios = [scenario for scenario in improvements['error_scenarios'] 
                               if scenario not in error_scenarios]
                error_scenarios.extend(new_scenarios)
            
            # 验证改进后的测试用例
            if not self._validate_improvements(test_case, improved_case):
                logger.warning(f"测试用例改进可能导致数据丢失: {test_case.get('id', 'unknown')}")
                return test_case
            
            return improved_case
            
        except Exception as e:
            logger.error(f"改进测试用例错误: {str(e)}")
            return test_case

    def _validate_improvements(self, original: Dict, improved: Dict) -> bool:
        """验证改进是否保持测试用例的完整性。"""
        return all(key in improved for key in original.keys())