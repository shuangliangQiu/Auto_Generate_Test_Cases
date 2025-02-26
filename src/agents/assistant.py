# src/agents/assistant.py
import os
import autogen
from typing import List, Dict
import logging
from .requirement_analyst import RequirementAnalystAgent
from .test_designer import TestDesignerAgent
from .test_case_writer import TestCaseWriterAgent
from .quality_assurance import QualityAssuranceAgent
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# 使用 Azure OpenAI 配置
api_key = os.getenv("AZURE_OPENAI_API_KEY")
base_url = os.getenv("AZURE_OPENAI_BASE_URL")
model = os.getenv("AZURE_OPENAI_MODEL")
model_version = os.getenv("AZURE_OPENAI_MODEL_VERSION")
class AssistantAgent:
    def __init__(self, agents: List):
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
            name="coordinator",
            system_message="""你是一位项目协调员，负责管理不同测试代理之间的交互，
            确保工作流程的顺畅进行。""",
            llm_config={"config_list": self.config_list}
        )
        
        self.agents = agents

    async def coordinate_workflow(self, task: dict):
        """协调不同代理之间的工作流程。"""
        try:
            # 验证任务参数
            if not isinstance(task, dict):
                raise ValueError("任务参数必须是字典类型")
            
            if not task.get('name') or not task.get('description'):
                raise ValueError("任务参数必须包含name和description字段")
                
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="任务提供者",
                human_input_mode="NEVER",
                code_execution_config={"use_docker": False}
            )

            # 开始协调
            try:
                # 使用同步方式调用initiate_chat
                user_proxy.initiate_chat(
                    self.agent,
                    message=f"""
                    协调以下测试任务：
                    任务: {task}
                    
                    确保以下流程的正确执行：
                    1. 需求分析
                    2. 测试设计
                    3. 测试用例编写
                    4. 质量保证
                    
                    请立即开始执行需求分析阶段，无需等待进一步确认。""",
                    max_turns=1  # 限制对话轮次为1，避免死循环
                )
            except Exception as e:
                logger.error(f"初始化对话错误: {str(e)}")
                # 即使初始化对话失败，我们也继续执行后续步骤
            
            # 记录协调开始
            logger.info("开始协调测试任务流程")

            # 1. 需求分析
            requirement_analyst = next((agent for agent in self.agents if isinstance(agent, RequirementAnalystAgent)), None)
            if not requirement_analyst:
                raise ValueError("找不到需求分析代理")
            # 执行需求分析并获取结果
            self._handle_agent_communication(
                'coordinator',
                'requirement_analyst',
                {'doc_content': task['description']}
            )
            # 直接从代理实例获取最新分析结果
            analysis_result = requirement_analyst.last_analysis
            
            # 监控进度
            self._monitor_progress()

            # 等待需求分析结果确认
            try:
                # 使用同步方式调用initiate_chat
                user_proxy.initiate_chat(
                    self.agent,
                    message=f"""
                    需求分析结果如下：
                    {analysis_result}
                    
                    请确认需求分析结果是否正确。
                    如果正确，请回复"正确"，我们将继续进行测试设计和用例编写。
                    如果需要调整，请提供具体的修改建议。
                    
                    注意：如果没有收到明确回复，系统将默认结果正确并继续执行。
                    """,
                    max_turns=1  # 限制对话轮次为1，避免死循环
                )
            except Exception as e:
                logger.error(f"确认需求分析结果错误: {str(e)}")
                # 即使确认失败，我们也继续执行后续步骤

            # 检查确认结果
            confirmation = user_proxy.last_message()
            logger.info(f"用户确认消息: {confirmation}")
            
            # 如果用户明确表示需要调整，则返回需要修改的状态
            if confirmation and ('需要调整' in confirmation or '不正确' in confirmation):
                logger.info("需求分析结果需要调整")
                return {'status': 'needs_revision', 'message': confirmation}
                
            # 如果用户明确表示正确或请求开始设计/编写测试用例，或者消息为空，则继续执行
            # 空消息表示自动回复，我们将其视为确认
            if not confirmation or '正确' in confirmation or '请开始设计' in confirmation or '编写测试用例' in confirmation:
                logger.info("用户确认需求分析结果正确或请求开始测试用例生成，或者收到空消息（自动确认）")
            
            # 自动触发后续流程
            logger.info("需求分析结果已确认正确，开始进行测试设计和用例编写")
            
            # 不再需要额外的确认对话，直接继续执行后续步骤

            # 2. 测试设计
            test_designer = next((agent for agent in self.agents if isinstance(agent, TestDesignerAgent)), None)
            if not test_designer:
                raise ValueError("找不到测试设计代理")
            design_result = self._handle_agent_communication(
                'requirement_analyst',
                'test_designer',
                {
                    'requirements': analysis_result  # 直接传递需求分析结果
                }
            )
            
            # 监控进度
            self._monitor_progress()

            # 3. 测试用例编写
            test_case_writer = next((agent for agent in self.agents if isinstance(agent, TestCaseWriterAgent)), None)
            if not test_case_writer:
                raise ValueError("找不到测试用例编写代理")
            test_cases = self._handle_agent_communication(
                'test_designer',
                'test_case_writer',
                {'test_strategy': design_result}
            )
            
            # 监控进度
            self._monitor_progress()

            # 4. 质量保证
            quality_assurance = next((agent for agent in self.agents if isinstance(agent, QualityAssuranceAgent)), None)
            if not quality_assurance:
                raise ValueError("找不到质量保证代理")
            review_result = self._handle_agent_communication(
                'test_case_writer',
                'quality_assurance',
                {'test_cases': test_cases}
            )
            
            # 监控进度
            self._monitor_progress()

            return self._process_coordination_result(self.agent.last_message())

        except Exception as e:
            logger.error(f"工作流程协调错误: {str(e)}")
            raise

    def _process_coordination_result(self, message: str) -> dict:
        """处理协调结果。
        解析协调器的响应消息，提取工作流程状态和任务分配信息。
        """
        try:
            # 初始化结果字典
            result = {
                'status': 'in_progress',
                'current_phase': '',
                'assigned_tasks': [],
                'completed_tasks': [],
                'next_steps': []
            }
            
            # 解析消息内容
            lines = message.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 识别不同部分
                if '当前阶段' in line:
                    current_section = 'phase'
                    result['current_phase'] = line.split(':', 1)[1].strip() if ':' in line else line
                elif '已分配任务' in line:
                    current_section = 'assigned'
                elif '已完成任务' in line:
                    current_section = 'completed'
                elif '下一步' in line:
                    current_section = 'next'
                elif line.startswith('-') and current_section:
                    # 根据当前部分添加内容
                    if current_section == 'assigned':
                        result['assigned_tasks'].append(line[1:].strip())
                    elif current_section == 'completed':
                        result['completed_tasks'].append(line[1:].strip())
                    elif current_section == 'next':
                        result['next_steps'].append(line[1:].strip())
            
            # 更新状态
            if len(result['completed_tasks']) == 4:  # 所有阶段都完成
                result['status'] = 'completed'
            
            return result
            
        except Exception as e:
            logger.error(f"处理协调结果错误: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _handle_agent_communication(self, from_agent: str, to_agent: str, message: dict):
        """处理代理之间的通信。
        管理代理之间的消息传递，确保正确的信息流动。
        """
        try:
            # 获取源代理和目标代理
            logger.info(f"查找代理: {from_agent} -> {to_agent}")
            logger.info(f"可用代理: {[agent.__class__.__name__ for agent in self.agents]}")
            
            # 打印每个代理的名称，帮助调试
            for agent in self.agents:
                if hasattr(agent, 'agent'):
                    logger.info(f"代理: {agent.__class__.__name__}, 名称: {agent.agent.name}")
            
            # 根据代理类型查找，而不是名称
            if to_agent == 'requirement_analyst':
                target_agent = next((agent for agent in self.agents if isinstance(agent, RequirementAnalystAgent)), None)
            elif to_agent == 'test_designer':
                target_agent = next((agent for agent in self.agents if isinstance(agent, TestDesignerAgent)), None)
            elif to_agent == 'test_case_writer':
                target_agent = next((agent for agent in self.agents if isinstance(agent, TestCaseWriterAgent)), None)
            elif to_agent == 'quality_assurance':
                target_agent = next((agent for agent in self.agents if isinstance(agent, QualityAssuranceAgent)), None)
            else:
                target_agent = None
                
            if not target_agent:
                logger.error(f"找不到指定的代理: {to_agent}")
                raise ValueError(f"找不到指定的代理: {to_agent}")
                
            logger.info(f"成功找到代理: {from_agent} -> {to_agent}")
            
            # 记录通信
            logger.info(f"通信: {from_agent} -> {to_agent}")
            logger.info(f"消息内容: {message}")
            
            # 验证消息格式
            if not isinstance(message, dict):
                raise ValueError("消息必须是字典类型")
                
            # 根据代理类型处理消息
            if to_agent == 'requirement_analyst':
                # 传递给需求分析师的消息
                if 'doc_content' in message:
                    if not isinstance(message['doc_content'], str):
                        raise ValueError("doc_content必须是字符串类型")
                    logger.info("开始需求分析")
                    # 使用同步方式调用analyze
                    result = target_agent.analyze(message['doc_content'])
                    logger.info(f"需求分析完成，结果: {result}")
                    return result
            elif to_agent == 'test_designer':
                # 传递给测试设计师的消息
                if 'requirements' in message:
                    if not isinstance(message['requirements'], dict):
                        raise ValueError("requirements必须是字典类型")
                    required_keys = ['functional_requirements', 'non_functional_requirements', 
                                   'test_scenarios', 'risk_areas']
                    for key in required_keys:
                        if key not in message['requirements']:
                            raise ValueError(f"requirements中缺少必需的键: {key}")
                    logger.info("开始测试设计")
                    # 构建完整的需求上下文
                    complete_requirements = {
                        'original_doc': message.get('doc_content', ''),  # 原始需求文档
                        'analysis_result': message['requirements']  # 需求分析结果
                    }
                    logger.info(f"构建完整需求上下文: {complete_requirements}")
                    # 使用同步方式调用design
                    result = target_agent.design(complete_requirements)
                    logger.info(f"测试设计完成，结果: {result}")
                    return result
            elif to_agent == 'test_case_writer':
                # 传递给测试用例编写者的消息
                if 'test_strategy' in message:
                    if not isinstance(message['test_strategy'], dict):
                        raise ValueError("test_strategy必须是字典类型")
                    required_keys = ['test_approach', 'coverage_matrix', 'priorities', 'resource_estimation']
                    for key in required_keys:
                        if key not in message['test_strategy']:
                            raise ValueError(f"test_strategy中缺少必需的键: {key}")
                    logger.info("开始测试用例编写")
                    # 使用同步方式调用generate
                    result = target_agent.generate(message['test_strategy'])
                    logger.info(f"测试用例生成完成，结果: {result}")
                    return result
            elif to_agent == 'quality_assurance':
                # 传递给质量保证的消息
                if 'test_cases' in message:
                    if not isinstance(message['test_cases'], list):
                        raise ValueError("test_cases必须是列表类型")
                    logger.info("开始质量保证审查")
                    # 使用同步方式调用review
                    result = target_agent.review(message['test_cases'])
                    logger.info(f"质量保证审查完成，结果: {result}")
                    return result
            
            return None
            
        except Exception as e:
            logger.error(f"代理通信错误: {str(e)}")
            raise

    def _monitor_progress(self):
        """监控测试工作流程的进度。
        跟踪各个阶段的完成情况，更新整体进度状态。
        """
        try:
            progress = {
                'total_phases': 4,
                'completed_phases': 0,
                'current_phase': '',
                'phase_status': {
                    '需求分析': {'status': 'pending', 'completion': 0},
                    '测试设计': {'status': 'pending', 'completion': 0},
                    '测试用例编写': {'status': 'pending', 'completion': 0},
                    '质量保证': {'status': 'pending', 'completion': 0}
                }
            }
            
            # 更新各阶段状态
            for agent in self.agents:
                if isinstance(agent, RequirementAnalystAgent):
                    # 检查需求分析代理是否有last_analysis属性
                    if hasattr(agent, 'last_analysis') and agent.last_analysis:
                        progress['phase_status']['需求分析']['status'] = 'completed'
                        progress['phase_status']['需求分析']['completion'] = 100
                        progress['completed_phases'] += 1
                elif isinstance(agent, TestDesignerAgent):
                    # 检查测试设计代理是否有last_design属性
                    if hasattr(agent, 'last_design') and agent.last_design:
                        progress['phase_status']['测试设计']['status'] = 'completed'
                        progress['phase_status']['测试设计']['completion'] = 100
                        progress['completed_phases'] += 1
                elif isinstance(agent, TestCaseWriterAgent):
                    # 检查测试用例编写代理是否有last_cases属性
                    if hasattr(agent, 'last_cases') and agent.last_cases:
                        progress['phase_status']['测试用例编写']['status'] = 'completed'
                        progress['phase_status']['测试用例编写']['completion'] = 100
                        progress['completed_phases'] += 1
                elif isinstance(agent, QualityAssuranceAgent):
                    # 检查质量保证代理是否有last_review属性
                    if hasattr(agent, 'last_review') and agent.last_review:
                        progress['phase_status']['质量保证']['status'] = 'completed'
                        progress['phase_status']['质量保证']['completion'] = 100
                        progress['completed_phases'] += 1
            
            # 更新当前阶段
            for phase, status in progress['phase_status'].items():
                if status['status'] == 'pending':
                    progress['current_phase'] = phase
                    break
            
            # 如果所有阶段都完成，设置当前阶段为'完成'
            if progress['completed_phases'] == progress['total_phases']:
                progress['current_phase'] = 'completed'
                
            logger.info(f"当前进度: {progress['completed_phases']}/{progress['total_phases']} - 当前阶段: {progress['current_phase']}")
            return progress
            
        except Exception as e:
            logger.error(f"监控进度错误: {str(e)}")
            return {
                'total_phases': 4,
                'completed_phases': 0,
                'current_phase': '',
                'phase_status': {
                    '需求分析': {'status': 'error', 'completion': 0},
                    '测试设计': {'status': 'error', 'completion': 0},
                    '测试用例编写': {'status': 'error', 'completion': 0},
                    '质量保证': {'status': 'error', 'completion': 0}
                }
            }