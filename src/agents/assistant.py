# src/agents/assistant.py
import os
import autogen
from typing import List
import logging
from .requirement_analyst import RequirementAnalystAgent
from .test_designer import TestDesignerAgent
from .test_case_writer import TestCaseWriterAgent
from .quality_assurance import QualityAssuranceAgent
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_API_BASE")
model = os.getenv("OPENAI_MODEL")
class AssistantAgent:
    def __init__(self, agents: List):
        self.config_list = [
            {
                "model": model,
                "api_key": api_key,
                "base_url":base_url 
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
                system_message="任务提供者"
            )

            # 开始协调
            await user_proxy.initiate_chat(
                self.agent,
                message=f"""
                协调以下测试任务：
                任务: {task}
                
                确保以下流程的正确执行：
                1. 需求分析
                2. 测试设计
                3. 测试用例编写
                4. 质量保证
                """
            )

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
            source_agent = next((agent for agent in self.agents if agent.agent.name == from_agent), None)
            target_agent = next((agent for agent in self.agents if agent.agent.name == to_agent), None)
            
            if not source_agent or not target_agent:
                raise ValueError(f"找不到指定的代理: {from_agent} -> {to_agent}")
            
            # 记录通信
            logger.info(f"通信: {from_agent} -> {to_agent}")
            logger.debug(f"消息内容: {message}")
            
            # 验证消息格式
            if not isinstance(message, dict):
                raise ValueError("消息必须是字典类型")
                
            # 根据代理类型处理消息
            if to_agent == 'requirement_analyst':
                # 传递给需求分析师的消息
                if 'doc_content' in message:
                    if not isinstance(message['doc_content'], str):
                        raise ValueError("doc_content必须是字符串类型")
                    return target_agent.analyze(message['doc_content'])
            elif to_agent == 'test_designer':
                # 传递给测试设计师的消息
                if 'requirements' in message:
                    return target_agent.design(message['requirements'])
            elif to_agent == 'test_case_writer':
                # 传递给测试用例编写者的消息
                if 'test_strategy' in message:
                    return target_agent.generate(message['test_strategy'])
            elif to_agent == 'quality_assurance':
                # 传递给质量保证的消息
                if 'test_cases' in message:
                    return target_agent.review(message['test_cases'])
            
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
                if isinstance(agent, RequirementAnalystAgent) and agent.last_analysis:
                    progress['phase_status']['需求分析']['status'] = 'completed'
                    progress['phase_status']['需求分析']['completion'] = 100
                    progress['completed_phases'] += 1
                elif isinstance(agent, TestDesignerAgent) and agent.last_design:
                    progress['phase_status']['测试设计']['status'] = 'completed'
                    progress['phase_status']['测试设计']['completion'] = 100
                    progress['completed_phases'] += 1
                elif isinstance(agent, TestCaseWriterAgent) and agent.last_cases:
                    progress['phase_status']['测试用例编写']['status'] = 'completed'
                    progress['phase_status']['测试用例编写']['completion'] = 100
                    progress['completed_phases'] += 1
                elif isinstance(agent, QualityAssuranceAgent) and agent.last_review:
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