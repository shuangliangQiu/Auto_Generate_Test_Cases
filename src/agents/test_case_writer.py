# src/agents/test_case_writer.py
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

class TestCaseWriterAgent:
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
        
        # 初始化AgentIO用于保存和加载测试用例
        self.agent_io = AgentIO()
        
        self.agent = autogen.AssistantAgent(
            name="test_case_writer",
            system_message='''你是一位精确的测试用例编写者。你的职责是基于测试
            策略创建详细、清晰且可执行的测试用例。

            请按照以下 JSON 格式提供测试用例：
            {
                "test_cases": [
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
                        "category": "功能测试"
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
        
        # 添加last_cases属性，用于跟踪最近生成的测试用例
        self.last_cases = None
        
        # 尝试加载之前的测试用例结果
        self._load_last_cases()

    def _load_last_cases(self):
        """加载之前保存的测试用例结果"""
        try:
            result = self.agent_io.load_result("test_case_writer")
            if result:
                self.last_cases = result
                logger.info("成功加载之前的测试用例生成结果")
        except Exception as e:
            logger.error(f"加载测试用例结果时出错: {str(e)}")
    
    def generate(self, test_strategy: Dict) -> List[Dict]:
        """基于测试策略生成测试用例。"""
        try:
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="测试策略提供者",
                human_input_mode="NEVER",
                code_execution_config={"use_docker": False}
            )

            # 提取测试覆盖矩阵和优先级信息
            coverage_matrix = test_strategy.get('coverage_matrix', [])
            priorities = test_strategy.get('priorities', [])
            test_approach = test_strategy.get('test_approach', {})
            
            # 构建更详细的提示，包含覆盖矩阵和优先级信息
            coverage_info = "\n测试覆盖矩阵:\n"
            for item in coverage_matrix:
                coverage_info += f"- 功能: {item.get('feature', '')}, 测试类型: {item.get('test_type', '')}\n"
                
            priority_info = "\n测试优先级:\n"
            for item in priorities:
                priority_info += f"- {item.get('level', '')}: {item.get('description', '')}\n"
            
            approach_info = "\n测试方法:\n"
            if isinstance(test_approach, dict):
                for key, value in test_approach.items():
                    if isinstance(value, list):
                        approach_info += f"- {key}: {', '.join(value)}\n"
                    else:
                        approach_info += f"- {key}: {value}\n"

            # 生成测试用例
            user_proxy.initiate_chat(
                self.agent,
                message=f"""基于以下测试策略创建详细的测试用例：
                
                {approach_info}
                {coverage_info}
                {priority_info}
                
                请确保每个测试用例都对应测试覆盖矩阵中的一个或多个功能点，并遵循定义的优先级策略。
                测试用例的优先级必须使用测试优先级中定义的级别（如P0、P1等）。
                测试用例的类别应该与测试覆盖矩阵中的测试类型相对应。
                
                对每个测试用例，请提供：
                1. 用例ID
                2. 标题
                3. 前置条件
                4. 测试步骤
                5. 预期结果
                6. 优先级（使用上述优先级定义）
                7. 类别（对应测试覆盖矩阵中的测试类型）
                
                请直接提供测试用例，无需等待进一步确认。""",
                max_turns=1  # 限制对话轮次为1，避免死循环
            )

            # 尝试解析测试用例
            test_cases = self._parse_test_cases(self.agent.last_message())
            
            # 如果解析结果为空，尝试重新生成一次
            if not test_cases:
                logger.warning("第一次测试用例生成为空，尝试重新生成")
                
                # 构建更明确的提示，强调必须基于测试覆盖矩阵和优先级
                retry_message = f"""请重新创建测试用例，确保严格按照测试设计生成。
                
                测试覆盖矩阵中的每个功能点都必须有对应的测试用例：
                {coverage_info}
                
                测试用例必须使用以下优先级：
                {priority_info}
                
                每个测试用例必须包含：ID、标题、前置条件、测试步骤、预期结果、优先级和类别。
                优先级必须使用P0、P1等格式，类别必须与测试覆盖矩阵中的测试类型对应。
                
                请以JSON格式返回测试用例，确保格式正确。"""
                
                # 重新尝试生成测试用例
                user_proxy.initiate_chat(
                    self.agent,
                    message=retry_message,
                    max_turns=1
                )
                
                # 再次解析测试用例
                test_cases = self._parse_test_cases(self.agent.last_message())
                
                # 如果仍然为空，记录错误并返回空列表
                if not test_cases:
                    logger.error("重新生成测试用例仍然失败，无法生成符合测试设计的测试用例")
                    return []
            
            # 验证测试用例是否与测试覆盖矩阵对应
            if coverage_matrix and test_cases:
                coverage_features = {item.get('feature', '') for item in coverage_matrix if 'feature' in item}
                test_case_categories = {tc.get('category', '') for tc in test_cases if 'category' in tc}
                
                # 记录覆盖情况
                logger.info(f"测试覆盖矩阵功能点: {coverage_features}")
                logger.info(f"测试用例类别: {test_case_categories}")
                
                # 检查是否有未覆盖的功能点
                uncovered = coverage_features - test_case_categories
                if uncovered:
                    logger.warning(f"以下功能点未被测试用例覆盖: {uncovered}")
            
            # 保存测试用例到last_cases属性
            self.last_cases = test_cases
            logger.info(f"测试用例生成完成，共生成 {len(test_cases)} 个测试用例")
            
            # 将测试用例保存到文件
            self.agent_io.save_result("test_case_writer", test_cases)
            
            return test_cases

        except Exception as e:
            logger.error(f"测试用例生成错误: {str(e)}")
            raise

    def _parse_test_cases(self, message) -> List[Dict]:
        """解析Agent响应为结构化的测试用例。"""
        try:
            # 检查message类型
            if isinstance(message, dict):
                # 如果是字典，尝试从content字段获取内容
                if 'content' in message:
                    message = message['content']
                else:
                    logger.error(f"无法从字典中提取消息内容: {message}")
                    return []
            
            # 确保message是字符串
            if not isinstance(message, str):
                logger.error(f"消息不是字符串类型: {type(message)}")
                return []
            
            # 尝试解析JSON格式的响应
            import json
            import re
            
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', message, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    json_data = json.loads(json_str)
                    if 'test_cases' in json_data and isinstance(json_data['test_cases'], list):
                        logger.info(f"成功从JSON中解析出 {len(json_data['test_cases'])} 个测试用例")
                        
                        # 验证和规范化测试用例
                        validated_test_cases = []
                        for test_case in json_data['test_cases']:
                            # 确保所有必需字段都存在
                            if self._validate_test_case(test_case):
                                # 规范化优先级格式（确保是P0、P1等格式）
                                if 'priority' in test_case and not test_case['priority'].startswith('P'):
                                    test_case['priority'] = f"P{test_case['priority']}" if test_case['priority'].isdigit() else test_case['priority']
                                
                                # 确保类别字段存在且有意义
                                if 'category' not in test_case or not test_case['category']:
                                    test_case['category'] = '功能测试'
                                
                                validated_test_cases.append(test_case)
                            else:
                                logger.warning(f"测试用例验证失败，跳过: {test_case.get('id', 'unknown')}")
                        
                        # 如果验证后的测试用例为空，记录警告并返回空列表
                        if not validated_test_cases:
                            logger.warning("验证后的测试用例为空，需要重新生成")
                            return []
                        
                        return validated_test_cases
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {str(e)}")
                    # 返回空列表，表示解析失败
                    return []
            
            # 如果没有找到JSON格式的响应，尝试使用原来的解析方法
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
                            # 规范化优先级格式
                            if 'priority' in current_test_case and not current_test_case['priority'].startswith('P'):
                                current_test_case['priority'] = f"P{current_test_case['priority']}" if current_test_case['priority'].isdigit() else current_test_case['priority']
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
                # 规范化优先级格式
                if 'priority' in current_test_case and not current_test_case['priority'].startswith('P'):
                    current_test_case['priority'] = f"P{current_test_case['priority']}" if current_test_case['priority'].isdigit() else current_test_case['priority']
                test_cases.append(current_test_case)
            
            # 如果没有解析出任何测试用例，返回空列表
            if not test_cases:
                logger.warning("未能解析出任何测试用例，需要重新生成")
                return []
            
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
                logger.warning(f"测试用例缺少必需字段: {[field for field in required_fields if field not in test_case]}")
                return False
            
            # 验证字段内容
            if not test_case["id"] or not test_case["title"]:
                logger.warning(f"测试用例ID或标题为空: {test_case.get('id', 'unknown')}")
                return False
            
            # 确保步骤和预期结果不为空
            if not test_case["steps"] or not test_case["expected_results"]:
                logger.warning(f"测试用例步骤或预期结果为空: {test_case.get('id', 'unknown')}")
                return False
            
            # 验证优先级格式（如 P0, P1, P2）
            # 注意：我们在解析时会规范化优先级格式，所以这里不再严格要求格式
            if not test_case["priority"]:
                logger.warning(f"测试用例优先级为空: {test_case.get('id', 'unknown')}")
                return False
            
            # 验证类别不为空
            if not test_case["category"]:
                logger.warning(f"测试用例类别为空: {test_case.get('id', 'unknown')}")
                return False
            
            # 验证前置条件是否为列表
            if not isinstance(test_case["preconditions"], list):
                logger.warning(f"测试用例前置条件不是列表: {test_case.get('id', 'unknown')}")
                test_case["preconditions"] = [test_case["preconditions"]] if test_case["preconditions"] else []
            
            # 验证步骤是否为列表
            if not isinstance(test_case["steps"], list):
                logger.warning(f"测试用例步骤不是列表: {test_case.get('id', 'unknown')}")
                test_case["steps"] = [test_case["steps"]] if test_case["steps"] else []
                
            # 验证预期结果是否为列表
            if not isinstance(test_case["expected_results"], list):
                logger.warning(f"测试用例预期结果不是列表: {test_case.get('id', 'unknown')}")
                test_case["expected_results"] = [test_case["expected_results"]] if test_case["expected_results"] else []
            
            return True
        except Exception as e:
            logger.error(f"验证测试用例错误: {str(e)}")
            return False