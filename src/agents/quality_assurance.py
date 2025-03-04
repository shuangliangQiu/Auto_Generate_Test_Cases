# src/agents/quality_assurance.py
import os
import autogen
from typing import Dict, List
import logging
from dotenv import load_dotenv
from src.utils.agent_io import AgentIO
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
        
        # 初始化AgentIO用于保存和加载审查结果
        self.agent_io = AgentIO()
        
        # 初始化agent
        self.agent = autogen.AssistantAgent(
            name="quality_assurance",
            system_message="""你是一位专业的质量保证工程师，负责审查和改进测试用例。
            你的职责是确保测试用例的完整性、清晰度、可执行性，并关注边界情况和错误场景。
            
            在审查测试用例时，请重点关注以下方面并以JSON格式返回审查结果：
            {
                "review_comments": {
                    "completeness": ["完整性相关的改进建议1", "完整性相关的改进建议2"],
                    "clarity": ["清晰度相关的改进建议1", "清晰度相关的改进建议2"],
                    "executability": ["可执行性相关的改进建议1", "可执行性相关的改进建议2"],
                    "boundary_cases": ["边界情况相关的改进建议1", "边界情况相关的改进建议2"],
                    "error_scenarios": ["错误场景相关的改进建议1", "错误场景相关的改进建议2"]
                }
            }
            
            注意事项：
            1. 必须严格按照上述JSON格式返回审查结果
            2. 每个类别至少包含一条具体的改进建议
            3. 所有建议必须清晰、具体、可执行
            4. 不要返回任何JSON格式之外的文本内容""",
            llm_config={"config_list": self.config_list}
        )
        
        # 添加last_review属性，用于跟踪最近的审查结果
        self.last_review = None
        
        # 尝试加载之前的审查结果
        self._load_last_review()

    def _load_last_review(self):
        """加载之前保存的审查结果"""
        try:
            result = self.agent_io.load_result("quality_assurance")
            if result:
                self.last_review = result
                logger.info("成功加载之前的质量审查结果")
        except Exception as e:
            logger.error(f"加载质量审查结果时出错: {str(e)}")
    
    def review(self, test_cases: List[Dict]) -> Dict:
        """审查和改进测试用例。"""
        try:
            # 验证输入参数
            if not test_cases or not isinstance(test_cases, list):
                logger.warning("输入的测试用例为空或格式不正确")
                return {"error": "输入的测试用例为空或格式不正确", "reviewed_cases": []}
            
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

            # 获取审查反馈
            review_feedback = self.agent.last_message()
            
            # 确保反馈是字符串格式
            if not review_feedback:
                logger.warning("审查反馈为空")
                review_feedback = ""
            elif isinstance(review_feedback, dict):
                if 'content' in review_feedback:
                    review_feedback = review_feedback['content']
                else:
                    logger.warning("无法从反馈字典中提取内容，使用空字符串")
                    review_feedback = ""
            elif not isinstance(review_feedback, str):
                logger.warning(f"审查反馈格式不正确: {type(review_feedback)}，转换为字符串")
                review_feedback = str(review_feedback)
            
            # 查找测试用例编写者代理
            from src.agents.test_case_writer import TestCaseWriterAgent
            test_case_writer = TestCaseWriterAgent()
            
            # 将反馈发送给测试用例编写者进行改进
            reviewed_cases = test_case_writer.improve_test_cases(test_cases, review_feedback)
            
            # 如果审查结果为空，返回原始测试用例
            if not reviewed_cases:
                logger.warning("测试用例审查结果为空，使用原始测试用例")
                reviewed_cases = test_cases
            
            # 保存审查结果到last_review属性
            self.last_review = reviewed_cases
            logger.info(f"测试用例审查完成，共审查 {len(reviewed_cases)} 个测试用例")
            
            # 提取反馈中的关键改进建议
            review_comments = self._extract_review_comments(review_feedback)
            
            # 创建包含审查反馈和改进后测试用例的结果
            result = {
                "reviewed_cases": reviewed_cases,
                "review_comments": review_comments,
                "review_date": self._get_current_timestamp(),
                "review_status": "completed"
            }
            
            # 验证结果数据的完整性
            if not self._validate_result(result):
                logger.warning("审查结果数据不完整，可能影响后续处理")
                result["review_status"] = "incomplete"
            
            # 将审查结果保存到文件
            try:
                self.agent_io.save_result("quality_assurance", result)
                logger.info("质量审查结果已成功保存")
            except Exception as e:
                logger.error(f"保存质量审查结果时出错: {str(e)}")
                # 即使保存失败，仍然返回结果
            
            return result

        except Exception as e:
            logger.error(f"测试用例审查错误: {str(e)}")
            error_result = {
                "error": str(e),
                "reviewed_cases": test_cases if isinstance(test_cases, list) else [],
                "review_comments": {},
                "review_status": "error"
            }
            return error_result

    def _extract_review_comments(self, feedback: str) -> Dict:
        """从字符串格式的反馈中提取结构化的审查评论。"""
        review_comments = {
            "completeness": [],
            "clarity": [],
            "executability": [],
            "boundary_cases": [],
            "error_scenarios": []
        }
        
        if not feedback:
            return review_comments
            
        # 尝试解析JSON格式的反馈
        import json
        import re
        
        try:
            # 查找JSON内容
            json_match = re.search(r'\{[\s\S]*\}', feedback)
            if json_match:
                json_str = json_match.group(0)
                # 解析JSON
                parsed_feedback = json.loads(json_str)
                
                # 提取review_comments部分
                if 'review_comments' in parsed_feedback:
                    return parsed_feedback['review_comments']
        except Exception as e:
            logger.warning(f"JSON解析失败，将使用文本解析方式: {str(e)}")
        
        # 如果JSON解析失败，回退到文本解析方式
        feedback_sections = [line.strip() for line in feedback.split('\n') if line.strip()]
        current_section = None
        
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
                    review_comments[current_section].append(content)
        
        return review_comments

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _validate_result(self, result: Dict) -> bool:
        """验证审查结果的完整性和有效性"""
        required_keys = ["reviewed_cases", "review_comments", "review_status"]
        if not all(key in result for key in required_keys):
            return False
            
        # 验证reviewed_cases是否为列表
        if not isinstance(result.get("reviewed_cases"), list):
            return False
            
        # 验证review_comments是否包含所有必要的类别
        comment_categories = ["completeness", "clarity", "executability", "boundary_cases", "error_scenarios"]
        if not all(category in result.get("review_comments", {}) for category in comment_categories):
            return False
            
        return True

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