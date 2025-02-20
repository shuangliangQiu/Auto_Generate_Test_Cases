# src/agents/requirement_analyst.py
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

class RequirementAnalystAgent:
    def __init__(self):
        self.config_list = [
            {
                "model": model,
                "api_key": api_key,
                "base_url":base_url 
            }
        ]
        
        self.agent = autogen.AssistantAgent(
            name="requirement_analyst",
            system_message="""你是一位专业的需求分析师，专注于软件测试领域。
            你的职责是分析软件需求，识别关键测试领域、功能流程和潜在风险。""",
            llm_config={"config_list": self.config_list}
        )

    async def analyze(self, doc_content: str) -> Dict:
        """分析需求文档并提取测试需求。"""
        try:
            # 创建用户代理进行交互
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="需求文档提供者"
            )

            # 初始化需求分析对话
            await user_proxy.initiate_chat(
                self.agent,
                message=f"""请分析以下需求文档并提取关键测试点：
                
                {doc_content}
                
                请按以下格式提供分析：
                1. 功能需求
                2. 非功能需求
                3. 测试场景
                4. 风险领域"""
            )

            # 处理代理的响应
            analysis_result = {
                "functional_requirements": self._extract_functional_reqs(self.agent.last_message()),
                "non_functional_requirements": self._extract_non_functional_reqs(self.agent.last_message()),
                "test_scenarios": self._extract_test_scenarios(self.agent.last_message()),
                "risk_areas": self._extract_risk_areas(self.agent.last_message())
            }

            return analysis_result

        except Exception as e:
            logger.error(f"需求分析错误: {str(e)}")
            raise

    def _extract_functional_reqs(self, message: str) -> List[str]:
        """从代理消息中提取功能需求。"""
        try:
            if not message:
                logger.warning("输入消息为空")
                return []
                
            # 将消息分割成段落并找到功能需求部分
            sections = message.split('\n')
            functional_reqs = []
            in_functional_section = False
            
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['1. 功能需求', '功能需求:', '功能需求：']):
                    in_functional_section = True
                    continue
                elif any(marker in line.lower() for marker in ['2. 非功能需求', '非功能需求:', '非功能需求：']):
                    break
                elif in_functional_section:
                    # 过滤掉编号和空行
                    content = line
                    if line[0].isdigit() and '. ' in line:
                        content = line.split('. ', 1)[1]
                    if content and not content.startswith('1.'):
                        functional_reqs.append(content)
            
            return functional_reqs
        except Exception as e:
            logger.error(f"提取功能需求错误: {str(e)}")
            return []

    def _extract_non_functional_reqs(self, message: str) -> List[str]:
        """从代理消息中提取非功能需求。"""
        try:
            if not message:
                logger.warning("输入消息为空")
                return []
                
            sections = message.split('\n')
            non_functional_reqs = []
            in_non_functional_section = False
            
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['2. 非功能需求', '非功能需求:', '非功能需求：']):
                    in_non_functional_section = True
                    continue
                elif any(marker in line.lower() for marker in ['3. 测试场景', '测试场景:', '测试场景：']):
                    break
                elif in_non_functional_section:
                    # 过滤掉编号和空行
                    content = line
                    if line[0].isdigit() and '. ' in line:
                        content = line.split('. ', 1)[1]
                    if content and not content.startswith('2.'):
                        non_functional_reqs.append(content)
            
            return non_functional_reqs
        except Exception as e:
            logger.error(f"提取非功能需求错误: {str(e)}")
            return []

    def _extract_test_scenarios(self, message: str) -> List[str]:
        """从代理消息中提取测试场景。"""
        try:
            if not message:
                logger.warning("输入消息为空")
                return []
                
            sections = message.split('\n')
            test_scenarios = []
            in_scenarios_section = False
            
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['3. 测试场景', '测试场景:', '测试场景：']):
                    in_scenarios_section = True
                    continue
                elif any(marker in line.lower() for marker in ['4. 风险领域', '风险领域:', '风险领域：']):
                    break
                elif in_scenarios_section:
                    # 过滤掉编号和空行
                    content = line
                    if line[0].isdigit() and '. ' in line:
                        content = line.split('. ', 1)[1]
                    if content and not content.startswith('3.'):
                        test_scenarios.append(content)
            
            return test_scenarios
        except Exception as e:
            logger.error(f"提取测试场景错误: {str(e)}")
            return []

    def _extract_risk_areas(self, message: str) -> List[str]:
        """从代理消息中提取风险领域。"""
        try:
            if not message:
                logger.warning("输入消息为空")
                return []
                
            sections = message.split('\n')
            risk_areas = []
            in_risks_section = False
            
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['4. 风险领域', '风险领域:', '风险领域：']):
                    in_risks_section = True
                    continue
                elif line.startswith('5.') or not line.strip():
                    break
                elif in_risks_section:
                    # 过滤掉编号和空行
                    content = line
                    if line[0].isdigit() and '. ' in line:
                        content = line.split('. ', 1)[1]
                    if content and not content.startswith('4.'):
                        risk_areas.append(content)
            
            return risk_areas
        except Exception as e:
            logger.error(f"提取风险领域错误: {str(e)}")
            return []