# src/agents/test_designer.py
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

class TestDesignerAgent:
    def __init__(self):
        self.config_list = [
            {
                "model": model,
                "api_key": api_key,
                "base_url":base_url 
            }
        ]
        
        self.agent = autogen.AssistantAgent(
            name="test_designer",
            system_message="""你是一位专业的测试设计师。你的职责是基于分析后的需求
            创建全面的测试策略和测试场景。""",
            llm_config={"config_list": self.config_list}
        )

    async def design(self, requirements: Dict) -> Dict:
        """基于分析后的需求设计测试策略。"""
        try:
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="需求提供者"
            )

            # 创建测试策略
            await user_proxy.initiate_chat(
                self.agent,
                message=f"""基于以下需求创建详细的测试策略：
                
                需求: {requirements}
                
                请提供：
                1. 测试方法
                2. 测试覆盖矩阵
                3. 测试优先级
                4. 资源估算"""
            )

            test_strategy = {
                "test_approach": self._extract_test_approach(self.agent.last_message()),
                "coverage_matrix": self._create_coverage_matrix(self.agent.last_message()),
                "priorities": self._extract_priorities(self.agent.last_message()),
                "resource_estimation": self._extract_resource_estimation(self.agent.last_message())
            }

            return test_strategy

        except Exception as e:
            logger.error(f"测试设计错误: {str(e)}")
            raise

    def _extract_test_approach(self, message: str) -> Dict:
        """从代理消息中提取测试方法详情。"""
        try:
            sections = message.split('\n')
            test_approach = {
                'methodology': [],
                'tools': [],
                'frameworks': []
            }
            in_approach_section = False
            
            for line in sections:
                if '1. 测试方法' in line:
                    in_approach_section = True
                    continue
                elif '2. 测试覆盖矩阵' in line:
                    break
                elif in_approach_section and line.strip() and not line.startswith('1.'):
                    # 分类方法详情
                    if '方法:' in line.lower():
                        test_approach['methodology'].append(line.split(':', 1)[1].strip())
                    elif '工具:' in line.lower():
                        test_approach['tools'].append(line.split(':', 1)[1].strip())
                    elif '框架:' in line.lower():
                        test_approach['frameworks'].append(line.split(':', 1)[1].strip())
                    else:
                        # 默认归类为方法
                        test_approach['methodology'].append(line.strip())
            
            return test_approach
        except Exception as e:
            logger.error(f"提取测试方法错误: {str(e)}")
            return {'methodology': [], 'tools': [], 'frameworks': []}

    def _create_coverage_matrix(self, message: str) -> List[Dict]:
        """从代理消息中创建测试覆盖矩阵。"""
        try:
            sections = message.split('\n')
            coverage_matrix = []
            in_matrix_section = False
            current_feature = None
            
            for line in sections:
                if '2. 测试覆盖矩阵' in line:
                    in_matrix_section = True
                    continue
                elif '3. 测试优先级' in line:
                    break
                elif in_matrix_section and line.strip() and not line.startswith('2.'):
                    # 识别功能及其测试覆盖
                    if line.strip().endswith(':'):
                        current_feature = line.strip()[:-1]
                    elif current_feature and line.strip().startswith('-'):
                        coverage_matrix.append({
                            'feature': current_feature,
                            'test_type': line.strip()[1:].strip()
                        })
            
            return coverage_matrix
        except Exception as e:
            logger.error(f"创建覆盖矩阵错误: {str(e)}")
            return []

    def _extract_priorities(self, message: str) -> List[Dict]:
        """从代理消息中提取测试优先级。"""
        try:
            sections = message.split('\n')
            priorities = []
            in_priorities_section = False
            
            for line in sections:
                if '3. 测试优先级' in line:
                    in_priorities_section = True
                    continue
                elif '4. 资源估算' in line:
                    break
                elif in_priorities_section and line.strip() and not line.startswith('3.'):
                    # 解析优先级和描述
                    if line.strip().startswith('P') and ':' in line:
                        priority, description = line.strip().split(':', 1)
                        priorities.append({
                            'level': priority.strip(),
                            'description': description.strip()
                        })
            
            return priorities
        except Exception as e:
            logger.error(f"提取优先级错误: {str(e)}")
            return []

    def _extract_resource_estimation(self, message: str) -> Dict:
        """从代理消息中提取资源估算。"""
        try:
            sections = message.split('\n')
            resource_estimation = {
                'time': None,
                'personnel': None,
                'tools': [],
                'additional_resources': []
            }
            in_estimation_section = False
            
            for line in sections:
                if '4. 资源估算' in line:
                    in_estimation_section = True
                    continue
                elif line.startswith('5.') or not line.strip():
                    break
                elif in_estimation_section and line.strip() and not line.startswith('4.'):
                    # 解析资源详情
                    if '时间:' in line.lower():
                        resource_estimation['time'] = line.split(':', 1)[1].strip()
                    elif '人员:' in line.lower():
                        resource_estimation['personnel'] = line.split(':', 1)[1].strip()
                    elif '工具:' in line.lower():
                        resource_estimation['tools'].append(line.split(':', 1)[1].strip())
                    else:
                        resource_estimation['additional_resources'].append(line.strip())
            
            return resource_estimation
        except Exception as e:
            logger.error(f"提取资源估算错误: {str(e)}")
            return {'time': None, 'personnel': None, 'tools': [], 'additional_resources': []}