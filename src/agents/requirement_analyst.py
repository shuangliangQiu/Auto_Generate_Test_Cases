# src/agents/requirement_analyst.py
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

class RequirementAnalystAgent:
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
            name="requirement_analyst",
            system_message="""你是一位专业的需求分析师，专注于软件测试领域。
            你的职责是分析软件需求，识别关键测试领域、功能流程和潜在风险。""",
            llm_config={"config_list": self.config_list}
        )
        
        # 添加last_analysis属性，用于跟踪最近的分析结果
        self.last_analysis = None

    def analyze(self, doc_content: str) -> Dict:
        """分析需求文档并提取测试需求。"""
        try:
            # 检查输入文档是否为空
            if not doc_content or not doc_content.strip():
                logger.warning("输入文档为空，返回默认分析结果")
                default_result = {
                    "functional_requirements": ["需要提供具体的功能需求"],
                    "non_functional_requirements": ["需要提供具体的非功能需求"],
                    "test_scenarios": ["需要提供具体的测试场景"],
                    "risk_areas": ["需要评估具体的风险领域"]
                }
                self.last_analysis = default_result
                return default_result

            # 创建用户代理进行交互
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="需求文档提供者",
                human_input_mode="NEVER",
                code_execution_config={"use_docker": False}
            )

            # 初始化需求分析对话
            user_proxy.initiate_chat(
                self.agent,
                message=f"""请分析以下需求文档并提取关键测试点：
                
                {doc_content}
                
                请按以下格式提供分析：
                1. 功能需求
                2. 非功能需求
                3. 测试场景
                4. 风险领域
                
                请直接提供分析结果，无需等待进一步确认。""",
                max_turns=1  # 限制对话轮次为1，避免死循环
            )

            # 处理代理的响应
            response = self.agent.last_message()
            if not response:
                logger.warning("需求分析代理返回空响应")
                return {
                    "functional_requirements": [],
                    "non_functional_requirements": [],
                    "test_scenarios": [],
                    "risk_areas": []
                }
            
            # 确保响应是字符串类型
            response_str = str(response) if response else ""
            if not response_str.strip():
                logger.warning("需求分析代理返回空响应")
                return {
                    "functional_requirements": [],
                    "non_functional_requirements": [],
                    "test_scenarios": [],
                    "risk_areas": []
                }
            analysis_result = {
                "functional_requirements": self._extract_functional_reqs(response_str),
                "non_functional_requirements": self._extract_non_functional_reqs(response_str),
                "test_scenarios": self._extract_test_scenarios(response_str),
                "risk_areas": self._extract_risk_areas(response_str)
            }
            
            # 验证分析结果的完整性
            if not self._validate_analysis_result(analysis_result):
                logger.warning("需求分析结果不完整，使用默认值填充")
                self._fill_missing_requirements(analysis_result)
            
            # 保存分析结果到last_analysis属性
            self.last_analysis = analysis_result
            logger.info(f"需求分析完成，结果包含：{len(analysis_result['functional_requirements'])}个功能需求，"
                     f"{len(analysis_result['non_functional_requirements'])}个非功能需求，"
                     f"{len(analysis_result['test_scenarios'])}个测试场景，"
                     f"{len(analysis_result['risk_areas'])}个风险领域")

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
                # 清理特殊字符和空白
                line = ''.join(char for char in line.strip() if ord(char) >= 32)
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['1. 功能需求', '功能需求:', '功能需求：', '一、功能需求']):
                    in_functional_section = True
                    continue
                elif any(marker in line.lower() for marker in ['2. 非功能需求', '二、非功能需求', '非功能需求:', '非功能需求：']):
                    in_functional_section = False
                    break
                elif in_functional_section:
                    # 过滤掉编号和空行
                    content = line
                    # 处理带有编号的行
                    if any(char.isdigit() for char in line[:2]):
                        for sep in ['.', '、', '）', ')', ']']:
                            if sep in line:
                                try:
                                    content = line.split(sep, 1)[1]
                                    break
                                except IndexError:
                                    continue
                    content = content.strip()
                    # 过滤掉标题行和空内容
                    if content and not any(content.lower().startswith(prefix.lower()) for prefix in 
                        ['1.', '一、', '功能需求', '需求', '要求']):
                        functional_reqs.append(content)
            
            # 如果没有找到任何功能需求，返回默认值
            if not functional_reqs:
                logger.warning("未找到有效的功能需求，使用默认值")
                functional_reqs = ["需要提供具体的功能需求"]
            else:
                logger.info(f"成功提取{len(functional_reqs)}个功能需求")
            
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

    def _validate_analysis_result(self, result: Dict) -> bool:
        """验证分析结果的完整性。"""
        required_keys = ['functional_requirements', 'non_functional_requirements', 
                        'test_scenarios', 'risk_areas']
        
        # 检查所有必需的键是否存在且不为空
        for key in required_keys:
            if key not in result or not isinstance(result[key], list):
                return False
        return True

    def _fill_missing_requirements(self, result: Dict):
        """填充缺失的需求字段。"""
        default_value = ["需要补充具体内容"]
        required_keys = ['functional_requirements', 'non_functional_requirements', 
                        'test_scenarios', 'risk_areas']
        
        for key in required_keys:
            if key not in result or not result[key]:
                result[key] = default_value.copy()