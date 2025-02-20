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
        test_approach = {
            'methodology': [],
            'tools': [],
            'frameworks': []
        }
        
        try:
            if not message:
                logger.warning("输入消息为空")
                return test_approach
                
            sections = message.split('\n')
            in_approach_section = False
            
            for line in sections:
                try:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if '1. 测试方法' in line:
                        in_approach_section = True
                        continue
                    elif '2. 测试覆盖矩阵' in line:
                        break
                    elif in_approach_section and not line.startswith('1.'):
                        # 分类方法详情
                        try:
                            if '方法:' in line.lower() or '方法：' in line:
                                content = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                                test_approach['methodology'].append(content)
                            elif '工具:' in line.lower() or '工具：' in line:
                                content = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                                test_approach['tools'].append(content)
                            elif '框架:' in line.lower() or '框架：' in line:
                                content = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                                test_approach['frameworks'].append(content)
                            else:
                                # 默认归类为方法
                                test_approach['methodology'].append(line.strip())
                        except IndexError as e:
                            logger.error(f"解析方法详情时出错: {str(e)}，行内容: {line}")
                            continue
                except Exception as e:
                    logger.error(f"处理单行内容时出错: {str(e)}，行内容: {line}")
                    continue
            
            return test_approach
        except Exception as e:
            logger.error(f"提取测试方法错误: {str(e)}")
            return test_approach

    def _create_coverage_matrix(self, message: str) -> List[Dict]:
        """从代理消息中创建测试覆盖矩阵。"""
        coverage_matrix = []
        
        try:
            if not message:
                logger.warning("输入消息为空")
                return coverage_matrix
                
            sections = message.split('\n')
            in_matrix_section = False
            current_feature = None
            
            for line in sections:
                try:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if '2. 测试覆盖矩阵' in line:
                        in_matrix_section = True
                        continue
                    elif '3. 测试优先级' in line:
                        break
                    elif in_matrix_section and not line.startswith('2.'):
                        try:
                            # 识别功能及其测试覆盖
                            if line.strip().endswith(':') or line.strip().endswith('：'):
                                current_feature = line.strip().rstrip(':').rstrip('：').strip()
                            elif current_feature and any(line.strip().startswith(marker) for marker in ['-', '•', '*', '>', '+']):
                                test_type = line.strip()[1:].strip()
                                if test_type:  # 确保测试类型不为空
                                    coverage_matrix.append({
                                        'feature': current_feature,
                                        'test_type': test_type
                                    })
                            elif line.strip() and not any(marker in line for marker in ['测试覆盖', '覆盖矩阵']):
                                test_type = line.strip()
                                if current_feature and test_type:  # 确保特性和测试类型都不为空
                                    coverage_matrix.append({
                                        'feature': current_feature,
                                        'test_type': test_type
                                    })
                        except Exception as e:
                            logger.error(f"处理测试覆盖项时出错: {str(e)}，行内容: {line}")
                            continue
                except Exception as e:
                    logger.error(f"处理单行内容时出错: {str(e)}，行内容: {line}")
                    continue
            
            return coverage_matrix
        except Exception as e:
            logger.error(f"创建测试覆盖矩阵错误: {str(e)}")
            return coverage_matrix

    def _extract_priorities(self, message: str) -> List[Dict]:
        """从代理消息中提取测试优先级。"""
        priorities = []
        try:
            if not message:
                logger.warning("输入消息为空")
                return priorities
                
            sections = message.split('\n')
            in_priorities_section = False
            
            for line in sections:
                try:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if '3. 测试优先级' in line:
                        in_priorities_section = True
                        continue
                    elif '4. 资源估算' in line:
                        break
                    elif in_priorities_section and not line.startswith('3.'):
                        try:
                            # 解析优先级和描述
                            if any(line.strip().lower().startswith(p) for p in ['p0', 'p1', 'p2', 'p3', 'p4']):
                                if ':' in line or '：' in line:
                                    priority, description = (line.split(':', 1) if ':' in line else line.split('：', 1))
                                    priority = priority.strip()
                                    description = description.strip()
                                    # 标准化优先级格式
                                    priority = f"P{priority[-1]}" if priority[-1].isdigit() else priority
                                    priorities.append({
                                        'level': priority.upper(),
                                        'description': description
                                    })
                        except (IndexError, ValueError) as e:
                            logger.error(f"解析优先级行时出错: {str(e)}，行内容: {line}")
                            continue
                except Exception as e:
                    logger.error(f"处理单行内容时出错: {str(e)}，行内容: {line}")
                    continue
            
            return priorities
        except Exception as e:
            logger.error(f"提取优先级错误: {str(e)}")
            return priorities

    def _extract_resource_estimation(self, message: str) -> Dict:
        """从代理消息中提取资源估算。"""
        resource_estimation = {
            'time': None,
            'personnel': None,
            'tools': [],
            'additional_resources': []
        }
        
        try:
            if not message:
                logger.warning("输入消息为空")
                return resource_estimation
                
            sections = message.split('\n')
            in_estimation_section = False
            
            for line in sections:
                try:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if '4. 资源估算' in line:
                        in_estimation_section = True
                        continue
                    elif line.startswith('5.') or not line.strip():
                        break
                    elif in_estimation_section and not line.startswith('4.'):
                        try:
                            # 解析资源详情
                            if any(marker in line.lower() for marker in ['时间:', '时间：']):
                                resource_estimation['time'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                            elif any(marker in line.lower() for marker in ['人员:', '人员：']):
                                resource_estimation['personnel'] = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                            elif any(marker in line.lower() for marker in ['工具:', '工具：']):
                                tools = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                                resource_estimation['tools'].extend([t.strip() for t in tools.split(',') if t.strip()])
                            else:
                                resource_estimation['additional_resources'].append(line.strip())
                        except IndexError as e:
                            logger.error(f"解析资源详情时出错: {str(e)}，行内容: {line}")
                            continue
                except Exception as e:
                    logger.error(f"处理单行内容时出错: {str(e)}，行内容: {line}")
                    continue
            
            return resource_estimation
        except Exception as e:
            logger.error(f"提取资源估算错误: {str(e)}")
            return resource_estimation