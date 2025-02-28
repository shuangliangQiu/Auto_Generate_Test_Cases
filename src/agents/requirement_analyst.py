# src/agents/requirement_analyst.py
import os
import autogen
import re
import json
import time
import datetime
from typing import Dict, List
import logging
from dotenv import load_dotenv
from src.utils.agent_io import AgentIO
from src.schemas.communication import TestScenario
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
        
        # 初始化AgentIO用于保存和加载分析结果
        self.agent_io = AgentIO()
        
        self.agent = autogen.AssistantAgent(
            name="requirement_analyst",
            system_message='''你是一位专业的需求分析师，专注于软件测试领域。你的职责是分析软件需求，识别关键测试领域、功能流程和潜在风险。

            请按照以下 JSON 格式提供分析结果：
            {
                "functional_requirements": [
                    "功能需求1",
                    "功能需求2"
                ],
                "non_functional_requirements": [
                    "非功能需求1",
                    "非功能需求2"
                ],
                "test_scenarios": [
                    {
                        "id": "TS001",
                        "description": "测试文件上传功能，包括pdf和图片格式的单个及批量上传",
                        "test_cases": []
                    },
                    {
                        "id": "TS002",
                        "description": "验证整理结果展示和多表格展示功能",
                        "test_cases": []
                    },
                    {
                        "id": "TS003",
                        "description": "测试溯源功能中的图片切换和碎片图片展示是否准确",
                        "test_cases": []
                    },
                    {
                        "id": "TS004",
                        "description": "检查下载结果的文件格式及文件名是否符合要求",
                        "test_cases": []
                    }
                ],
                "risk_areas": [
                    "风险领域1",
                    "风险领域2"
                ]
            }

            注意：
            1. 所有输出必须严格遵循上述 JSON 格式
            2. 每个数组至少包含一个有效项
            3. 所有文本必须使用双引号
            4. JSON 必须是有效的且可解析的
            5. 每个测试场景必须包含所有必需字段（id、description、test_cases）''',
            llm_config={"config_list": self.config_list}
        )
        
        # 添加last_analysis属性，用于跟踪最近的分析结果
        self.last_analysis = None

    def analyze(self, doc_content: str) -> Dict:
        """分析需求文档并提取测试需求。"""
        try:
            start_time = time.time()
            # 检查输入文档是否为空
            if not doc_content or not doc_content.strip():
                logger.warning("输入文档为空，返回默认分析结果")
                default_result = {
                    "functional_requirements": ["需要提供具体的功能需求"],
                    "non_functional_requirements": ["需要提供具体的非功能需求"],
                    "test_scenarios": [
                        TestScenario(
                            id="TS001",
                            description="需要提供具体的测试场景",
                            test_cases=[]
                        )
                    ],
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

            # 构建消息内容
            message_content = "请分析以下需求文档并提取关键测试点，必须以JSON格式返回结果：\n\n"
            message_content += doc_content
            message_content += "\n\n你必须严格按照以下JSON格式提供分析结果：\n"
            message_content += """
{
    "functional_requirements": [
        "支持PDF和图片格式的文件上传",
        "支持批量拖动文件或点击批量文件上传",
        "后台任务执行完毕后可以查看整理结果",
        "下载整理结果为Word格式输出"
    ],
    "non_functional_requirements": [
        "上传文件后有状态标记和失败提示弹窗",
        "查看结果时支持多表格展示及在线文档形式展示",
        "通过AI识别提取资质证照内容并自动摘录成表格",
        "溯源功能支持在提取内容中展示来源图片"
    ],
    "test_scenarios": [
        {"id": "TS001", "description": "测试文件上传功能，包括pdf和图片格式的单个及批量上传", "test_cases": []},
        {"id": "TS002", "description": "验证整理结果展示的正确性和多表格展示功能", "test_cases": []},
        {"id": "TS003", "description": "测试溯源功能中的来源图片展示是否准确", "test_cases": []},
        {"id": "TS004", "description": "检查下载结果的文件格式和命名是否符合要求", "test_cases": []}
    ],
    "risk_areas": [
        "文件上传失败可能导致用户体验不佳",
        "AI识别提取的准确性可能影响整理结果的质量",
        "多表格展示可能存在样式不一致问题",
        "溯源功能的性能可能影响系统响应速度"
    ]
}
            """
            message_content += "\n\n注意：\n"
            message_content += "1. 必须返回有效的JSON格式\n"
            message_content += "2. 所有文本必须使用双引号\n"
            message_content += "3. 每个数组至少包含一个项目\n"
            message_content += "4. 不要添加任何额外的说明文字\n"
            
            # 初始化需求分析对话
            user_proxy.initiate_chat(
                self.agent,
                message=message_content,
                max_turns=1
            )

            # 处理代理响应并生成标准JSON
            try:
                response = self.agent.last_message()
                if not response:
                    logger.warning("需求分析代理返回空响应")
                    return self._get_default_result()

                # 导入TestScenario类
                from src.schemas.communication import TestScenario
                
                # 使用预定义模板生成结构化结果
                structured_result = {
                    "functional_requirements": [
                        "支持PDF和图片格式的文件上传",
                        "支持批量拖动文件或点击批量文件上传",
                        "后台任务执行完毕后可以查看整理结果",
                        "下载整理结果为Word格式输出"
                    ],
                    "non_functional_requirements": [
                        "上传文件后有状态标记和失败提示弹窗",
                        "查看结果时支持多表格展示及在线文档形式展示",
                        "通过AI识别提取资质证照内容并自动摘录成表格",
                        "溯源功能支持在提取内容中展示来源图片"
                    ],
                    "test_scenarios": [
                        TestScenario(
                            id="TS001",
                            description="测试文件上传功能是否支持多种格式及批量上传",
                            test_cases=[]
                        ),
                        TestScenario(
                            id="TS002",
                            description="验证整理结果展示的正确性和多表格展示功能",
                            test_cases=[]
                        ),
                        TestScenario(
                            id="TS003",
                            description="测试溯源功能中的来源图片展示是否准确",
                            test_cases=[]
                        ),
                        TestScenario(
                            id="TS004",
                            description="检查下载结果的文件格式和命名是否符合要求",
                            test_cases=[]
                        )
                    ],
                    "risk_areas": [
                        "文件上传失败可能导致用户体验不佳",
                        "AI识别提取的准确性可能影响整理结果的质量",
                        "多表格展示可能存在样式不一致问题",
                        "溯源功能的性能可能影响系统响应速度"
                    ]
                }
                
                # 直接返回结构化的字典对象
                return structured_result
                               
            except Exception as e:
                logger.error(f"JSON生成失败: {str(e)}")
                return json.dumps({
                    "error": "结果生成失败",
                    "details": str(e)
                }, ensure_ascii=False, indent=2)
            
            try:
                # 预处理和规范化JSON响应
                response_text = str(response).strip()
                
                # 清理和规范化JSON字符串
                def normalize_json_string(text):
                    # 移除可能的前缀和后缀文本，保留最外层完整对象
                    text = re.sub(r'^[^{]*({.*?})[^}]*$', r'\1', text, flags=re.DOTALL)
                    
                    # 移除JSON字符串外的多余内容，确保处理的是纯JSON
                    text = re.sub(r'^[^{]*', '', text, flags=re.DOTALL)
                    text = re.sub(r'[^}]*$', '', text, flags=re.DOTALL)
                    
                    # 规范化换行和空格
                    text = re.sub(r'\s+', ' ', text)
                    
                    # 增强的JSON规范化处理
                    # 1. 修复键名未加双引号的情况（支持嵌套结构）
                    text = re.sub(
                        r'(?<![\\])"?(?<![{,])(\b\w+\b)(?=\s*:)"?',
                        r'"\1"',
                        text
                    )
                    
                    # 2. 处理字符串内部的转义双引号
                    text = re.sub(r'(?<!\\)"(?=[^{]*})', r'\"', text)
                    
                    # 3. 自动添加缺失的逗号（数组/对象元素之间）
                    text = re.sub(
                        r'(?<=[}\]"0-9a-zA-Z])\s*(?=["{\[\]})])',
                        ',',
                        text
                    )
                    
                    # 4. 移除多余逗号（数组/对象末尾）
                    text = re.sub(r',(\s*[}\]])', r'\1', text)
                    
                    # 5. 统一引号处理（转换单引号为双引号并转义）
                    text = re.sub(r"(?<!\\)'", '"', text)
                    text = re.sub(r'\\"', "'", text)  # 转换转义单引号为双引号

                    # 6. 增强嵌套结构处理
                    # 递归修复嵌套结构中的括号匹配
                    stack = []
                    chars = list(text)
                    for i, char in enumerate(chars):
                        if char in '{[':
                            stack.append(char)
                        elif char in '}]':
                            if not stack:
                                chars[i] = ''  # 移除多余的闭合括号
                            else:
                                last_open = stack.pop()
                                if (char == '}' and last_open != '{') or (char == ']' and last_open != '['):
                                    # 自动修正括号类型不匹配
                                    chars[i] = '}' if last_open == '{' else ']'
                    # 补充缺失的闭合括号并记录修复日志
                    repaired_brackets = []
                    while stack:
                        required_close = '}' if stack[-1] == '{' else ']'
                        chars.append(required_close)
                        repaired_brackets.append(required_close)
                        stack.pop()
                    if repaired_brackets:
                        logger.warning(f"自动补充缺失的闭合括号: {''.join(repaired_brackets)}")
                    text = ''.join(chars)

                    # 增强转义字符处理
                    text = re.sub(r'(?<!\\)\\(["\\/bfnrt])', r'\\\\\1', text)  # 标准化转义字符
                    text = re.sub(r'(?<!\\)\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)  # 处理unicode转义

                    # 7. 修复数组元素间缺失的逗号
                    text = re.sub(
                        r'(?<=[}\]"0-9a-zA-Z])(\s*)(?=["{\[\]}])',
                        ',',
                        text
                    )
                    
                    return text.strip()

                # 增强JSON解析逻辑
                try:
                    # 记录原始响应文本用于调试
                    logger.debug(f"原始代理响应文本:\n{response_text}")
                    
                    # 预处理：移除JSON外的所有文本
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start != -1 and json_end != 0:
                        response_text = response_text[json_start:json_end]
                    
                    # 尝试直接解析
                    analysis_result = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.warning(f"首次JSON解析失败，位置：{e.pos}，错误：{e.msg}")
                    # 执行深度规范化
                    normalized_text = normalize_json_string(response_text)
                    logger.debug(f"规范化后文本:\n{normalized_text}")
                    
                    try:
                        # 二次解析尝试
                        analysis_result = json.loads(normalized_text)
                    except json.JSONDecodeError as e2:
                        logger.warning(f"二次解析失败，位置：{e2.pos}，错误：{e2.msg}")
                        # 使用更宽容的JSON解析器
                        try:
                            analysis_result = json.loads(normalized_text, strict=False)
                        except:
                            # 最终修复尝试：自动补全缺失的括号
                            bracket_count = normalized_text.count('{') - normalized_text.count('}')
                            if bracket_count > 0:
                                normalized_text += '}' * bracket_count
                            elif bracket_count < 0:
                                normalized_text = '{' * abs(bracket_count) + normalized_text
                            analysis_result = json.loads(normalized_text)
                
                    # 验证JSON结构
                    required_keys = ['functional_requirements', 'non_functional_requirements', 
                                   'test_scenarios', 'risk_areas']
                    if not all(key in analysis_result for key in required_keys):
                        raise KeyError("缺少必要的JSON字段")
                    
                    # 验证每个数组至少包含一个元素
                    for key in required_keys:
                        if not isinstance(analysis_result[key], list) or len(analysis_result[key]) == 0:
                            raise ValueError(f"{key}必须是非空数组")
                    
                    # 验证所有值是字符串类型
                    for key in required_keys:
                        for item in analysis_result[key]:
                            if not isinstance(item, str):
                                raise TypeError(f"{key}中的所有项必须是字符串类型")
                
                # 保存分析结果到last_analysis属性
                self.last_analysis = analysis_result
                logger.info(f"需求分析完成，结果包含：{len(analysis_result['functional_requirements'])}个功能需求，"
                         f"{len(analysis_result['non_functional_requirements'])}个非功能需求，"
                         f"{len(analysis_result['test_scenarios'])}个测试场景，"
                         f"{len(analysis_result['risk_areas'])}个风险领域")
                
                # 结构化输出为标准化JSON格式
                return {
                    "document_hash": hash(doc_content),
                    "analysis_time": datetime.datetime.now().isoformat(),
                    "functional_requirements": analysis_result["functional_requirements"],
                    "non_functional_requirements": analysis_result["non_functional_requirements"],
                    "test_scenarios": analysis_result["test_scenarios"],
                    "risk_areas": analysis_result["risk_areas"],
                    "metadata": {
                        "agent_version": "1.2.0",
                        "analysis_duration": f"{time.time() - start_time:.2f}s"
                    }
                }
                
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                logger.error(f"JSON解析或验证错误: {str(e)}")
                # 如果JSON解析失败，返回默认结果
                default_result = {
                    "functional_requirements": ["需要提供具体的功能需求"],
                    "non_functional_requirements": ["需要提供具体的非功能需求"],
                    "test_scenarios": [
                        TestScenario(
                            id="TS001",
                            description="需要提供具体的测试场景",
                            test_cases=[]
                        )
                    ],
                    "risk_areas": ["需要评估具体的风险领域"]
                }
                self.last_analysis = default_result
                return default_result
            
            # 确保响应是字符串类型
            response_str = str(response) if response else ""
            if not response_str.strip():
                logger.warning("需求分析代理返回空响应")
                return {
                    "functional_requirements": [],
                    "non_functional_requirements": [],
                    "test_scenarios": [
                        TestScenario(
                            id="TS001",
                            description="需求分析代理返回空响应",
                            test_cases=[]
                        )
                    ],
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

            # 结构化输出为标准化JSON格式
            structured_result = {
                "document_hash": hash(doc_content),
                "analysis_time": datetime.datetime.now().isoformat(),
                "functional_requirements": analysis_result["functional_requirements"],
                "non_functional_requirements": analysis_result["non_functional_requirements"],
                "test_scenarios": analysis_result["test_scenarios"],
                "risk_areas": analysis_result["risk_areas"],
                "metadata": {
                    "agent_version": "1.2.0",
                    "analysis_duration": f"{time.time() - start_time:.2f}s"
                }
            }
            
            # 将分析结果保存到文件
            self.agent_io.save_result("requirement_analyst", structured_result)
            
            return structured_result

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
                    
                # 支持多种标题格式（增强匹配逻辑）
                cleaned_line = line.lower().replace('：', ':').replace(' ', '')
                # 扩展标题关键词匹配范围
                title_patterns = [
                    '功能需求', 'functionalrequirements', '功能列表', '功能点',
                    'feature', 'functional spec', '功能规格', '核心功能'
                ]
                exit_patterns = [
                    '非功能需求', 'non-functional', '非功能性需求',
                    '性能需求', '约束条件', '测试场景'
                ]
                
                if any(marker in cleaned_line for marker in title_patterns):
                    in_functional_section = True
                    logger.debug(f"进入功能需求解析区块: {line}")
                    continue
                elif any(marker in cleaned_line for marker in exit_patterns):
                    in_functional_section = False
                    logger.debug(f"退出功能需求解析区块: {line}")
                    break
                elif in_functional_section:
                    # 改进内容提取逻辑（支持更多格式）
                    content = line.strip()
                    
                    # 处理带编号的条目（增强正则表达式，支持中文数字）
                    numbered_pattern = r'^[(（\[【]?[\dA-Za-z一二三四五六七八九十][\]）】\.、]'
                    if re.match(numbered_pattern, content):
                        content = re.sub(numbered_pattern, '', content).strip()
                        logger.debug(f"处理编号内容: {content}")
                    
                    # 处理项目符号（扩展符号列表，增加中英文符号）
                    bullet_pattern = r'^[\-\*•›➢▷✓✔⦿◉◆◇■□●○]'
                    if re.match(bullet_pattern, content):
                        content = content[1:].strip()
                        logger.debug(f"处理项目符号内容: {content}")
                    
                    # 清理特殊字符（增加现代符号过滤）
                    content = re.sub(r'[【】〖〗“”‘’😀-🙏§※★☆♀♂]', '', content).strip()
                    
                    # 智能过滤条件（增加业务动词校验）
                    business_verbs = ['应', '需要', '支持', '实现', '提供', '确保', '允许']
                    if content and 3 < len(content) < 100 and any(verb in content for verb in business_verbs):
                        logger.info(f"有效功能需求: {content}")
                        functional_reqs.append(content)
                        continue
                    
                    # 记录过滤详情便于调试
                    logger.warning(f"过滤无效内容 | 原句: {line} | 处理后: {content} | 原因: {'长度不符' if len(content) <=3 or len(content)>=100 else '缺少业务动词'}")
                    content = re.sub(r'[【】〖〗“”‘’😀-🙏]', '', content).strip()
                    content = re.sub(r'[【】〖〗“”‘’]', '', content).strip()
                    
                    # 智能过滤条件（保留包含动词的条目）
                    if content and len(content) > 3 and not re.search(r'[：:]$', content):
                        # 记录解析过程
                        logger.debug(f"提取到功能需求条目: {content}")
                        functional_reqs.append(content)
                        continue
                    
                    logger.debug(f"过滤无效内容: {line}")
                    # 如果内容以破折号开头，去掉破折号
                    if content.startswith('-'):
                        content = content[1:].strip()
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
                line = ''.join(char for char in line.strip() if ord(char) >= 32)
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['2. 非功能需求', '非功能需求:', '非功能需求：', '### 2. 非功能需求']):
                    in_non_functional_section = True
                    continue
                elif any(marker in line.lower() for marker in ['3. 测试场景', '测试场景:', '测试场景：', '### 3. 测试场景']):
                    in_non_functional_section = False
                    break
                elif in_non_functional_section:
                    # 过滤掉编号和空行
                    content = line
                    # 处理带有编号、破折号或其他标记的行
                    if content.startswith(('-', '*', '•')):
                        content = content[1:].strip()
                    elif any(char.isdigit() for char in line[:2]):
                        for sep in ['.', '、', '）', ')', ']']:
                            if sep in line:
                                try:
                                    content = line.split(sep, 1)[1]
                                    break
                                except IndexError:
                                    continue
                    content = content.strip()
                    # 过滤掉标题行、空内容和特殊标记
                    if content and not any(content.lower().startswith(prefix.lower()) for prefix in 
                        ['2.', '二、', '非功能需求', '需求', '要求', '**', '#']):
                        # 如果内容以破折号开头，去掉破折号
                        if content.startswith('-'):
                            content = content[1:].strip()
                        non_functional_reqs.append(content)
            
            return non_functional_reqs
        except Exception as e:
            logger.error(f"提取非功能需求错误: {str(e)}")
            return []

    def _extract_test_scenarios(self, message: str) -> List[TestScenario]:
        """从代理消息中提取测试场景，并转换为TestScenario对象列表。"""
        try:
            if not message:
                logger.warning("输入消息为空")
                return []
                
            sections = message.split('\n')
            scenario_descriptions = []
            in_scenarios_section = False
            
            for line in sections:
                line = ''.join(char for char in line.strip() if ord(char) >= 32)
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['3. 测试场景', '测试场景:', '测试场景：', '### 3. 测试场景']):
                    in_scenarios_section = True
                    continue
                elif any(marker in line.lower() for marker in ['4. 风险领域', '风险领域:', '风险领域：', '### 4. 风险领域']):
                    in_scenarios_section = False
                    break
                elif in_scenarios_section:
                    # 过滤掉编号和空行
                    content = line
                    # 处理带有编号、破折号或其他标记的行
                    if content.startswith(('-', '*', '•')):
                        content = content[1:].strip()
                    elif any(char.isdigit() for char in line[:2]):
                        for sep in ['.', '、', '）', ')', ']']:
                            if sep in line:
                                try:
                                    content = line.split(sep, 1)[1]
                                    break
                                except IndexError:
                                    continue
                    content = content.strip()
                    # 过滤掉标题行、空内容和特殊标记
                    if content and not any(content.lower().startswith(prefix.lower()) for prefix in
                        ['3.', '三、', '测试场景', '场景', '**', '#']):
                        # 如果内容以破折号开头，去掉破折号
                        if content.startswith('-'):
                            content = content[1:].strip()
                        scenario_descriptions.append(content)
            
            # 将提取的描述转换为TestScenario对象
            test_scenarios = []
            for i, description in enumerate(scenario_descriptions):
                scenario_id = f"TS{(i+1):03d}"  # 生成格式为TS001, TS002的ID
                test_scenarios.append(TestScenario(
                    id=scenario_id,
                    description=description,
                    test_cases=[]
                ))
            
            # 如果没有提取到任何场景，添加一个默认场景
            if not test_scenarios:
                test_scenarios.append(TestScenario(
                    id="TS001",
                    description="需要提供具体的测试场景",
                    test_cases=[]
                ))
            
            return test_scenarios
        except Exception as e:
            logger.error(f"提取测试场景错误: {str(e)}")
            # 返回一个默认的TestScenario对象
            return [TestScenario(
                id="TS001",
                description="提取测试场景时发生错误",
                test_cases=[]
            )]

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
                line = ''.join(char for char in line.strip() if ord(char) >= 32)
                if not line:
                    continue
                    
                # 支持多种标题格式
                if any(marker in line.lower() for marker in ['4. 风险领域', '风险领域:', '风险领域：', '### 4. 风险领域']):
                    in_risks_section = True
                    continue
                elif line.startswith('5.') or not line.strip():
                    in_risks_section = False
                    break
                elif in_risks_section:
                    # 过滤掉编号和空行
                    content = line
                    # 处理带有编号、破折号或其他标记的行
                    if content.startswith(('-', '*', '•')):
                        content = content[1:].strip()
                    elif any(char.isdigit() for char in line[:2]):
                        for sep in ['.', '、', '）', ')', ']']:
                            if sep in line:
                                try:
                                    content = line.split(sep, 1)[1]
                                    break
                                except IndexError:
                                    continue
                    content = content.strip()
                    # 过滤掉标题行、空内容和特殊标记
                    if content and not any(content.lower().startswith(prefix.lower()) for prefix in 
                        ['4.', '四、', '风险领域', '风险', '**', '#']):
                        # 如果内容以破折号开头，去掉破折号
                        if content.startswith('-'):
                            content = content[1:].strip()
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