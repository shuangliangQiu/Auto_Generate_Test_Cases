# src/agents/test_case_writer.py
import os
import autogen
from typing import Dict, List
import logging
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE")
model = os.getenv("OPENAI_MODEL")

class TestCaseWriterAgent:
    def __init__(self):
        self.config_list = [
            {
                "model": model,
                "api_key": api_key,
                "base_url":base_url 
            }
        ]
        
        self.agent = autogen.AssistantAgent(
            name="test_case_writer",
            system_message="""你是一位精确的测试用例编写者。你的职责是基于测试
            策略创建详细、清晰且可执行的测试用例。""",
            llm_config={"config_list": self.config_list}
        )

    async def generate(self, test_strategy: Dict) -> List[Dict]:
        """基于测试策略生成测试用例。"""
        try:
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="测试策略提供者"
            )

            # 生成测试用例
            await user_proxy.initiate_chat(
                self.agent,
                message=f"""基于以下测试策略创建详细的测试用例：
                
                测试策略: {test_strategy}
                
                对每个测试用例，请提供：
                1. 用例ID
                2. 标题
                3. 前置条件
                4. 测试步骤
                5. 预期结果
                6. 优先级
                7. 类别"""
            )

            test_cases = self._parse_test_cases(self.agent.last_message())
            return test_cases

        except Exception as e:
            logger.error(f"测试用例生成错误: {str(e)}")
            raise

    def _parse_test_cases(self, message: str) -> List[Dict]:
        """解析Agent响应为结构化的测试用例。"""
        try:
            sections = message.split('\n')
            test_cases = []
            current_test_case = None
            current_field = None
            
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                
                # 当找到ID时开始新的测试用例
                if line.lower().startswith('id:'):
                    if current_test_case:
                        if self._validate_test_case(current_test_case):
                            test_cases.append(current_test_case)
                    current_test_case = {
                        'id': '',
                        'title': '',
                        'preconditions': [],
                        'steps': [],
                        'expected_results': [],
                        'priority': '',
                        'category': ''
                    }
                    current_test_case['id'] = line.split(':', 1)[1].strip()
                    current_field = 'id'
                
                # 识别当前正在处理的字段
                elif line.lower().startswith('title:'):
                    current_test_case['title'] = line.split(':', 1)[1].strip()
                    current_field = 'title'
                elif line.lower().startswith('preconditions:'):
                    current_field = 'preconditions'
                elif line.lower().startswith('steps:'):
                    current_field = 'steps'
                elif line.lower().startswith('expected results:'):
                    current_field = 'expected_results'
                elif line.lower().startswith('priority:'):
                    current_test_case['priority'] = line.split(':', 1)[1].strip()
                    current_field = 'priority'
                elif line.lower().startswith('category:'):
                    current_test_case['category'] = line.split(':', 1)[1].strip()
                    current_field = 'category'
                
                # 添加内容到当前字段
                elif current_test_case and current_field:
                    if current_field in ['preconditions', 'steps', 'expected_results']:
                        if line.strip().startswith('-'):
                            current_test_case[current_field].append(line.strip()[1:].strip())
                        elif line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '0.')):
                            current_test_case[current_field].append(line.strip().split('.', 1)[1].strip())
            
            # 如果存在最后一个测试用例则添加
            if current_test_case and self._validate_test_case(current_test_case):
                test_cases.append(current_test_case)
            
            return test_cases
        except Exception as e:
            logger.error(f"解析测试用例错误: {str(e)}")
            return []

    def _validate_test_case(self, test_case: Dict) -> bool:
        """验证测试用例的结构和内容。"""
        try:
            # 检查是否所有必需字段都存在
            required_fields = [
                "id", "title", "preconditions", "steps", 
                "expected_results", "priority", "category"
            ]
            if not all(field in test_case for field in required_fields):
                return False
            
            # 验证字段内容
            if not test_case["id"] or not test_case["title"]:
                return False
            
            # 确保步骤和预期结果不为空
            if not test_case["steps"] or not test_case["expected_results"]:
                return False
            
            # 验证优先级格式（如 P0, P1, P2）
            if not test_case["priority"].startswith('P') or not test_case["priority"][1:].isdigit():
                return False
            
            return True
        except Exception as e:
            logger.error(f"验证测试用例错误: {str(e)}")
            return False