from browser_use import Agent
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
import asyncio
import sys
import os
import logging
import json
from dotenv import load_dotenv

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    os.system('chcp 65001')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 配置日志，解决Windows控制台编码问题
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if not isinstance(msg, str):
                msg = str(msg)
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # 如果遇到编码错误，尝试使用GBK编码
            try:
                msg = self.format(record)
                stream = self.stream
                if not isinstance(msg, str):
                    msg = str(msg)
                stream.write(msg.encode('gbk', errors='replace').decode('gbk') + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)


# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# 加载环境变量
load_dotenv()
# env_vars = load_env_variables()
base_url = os.getenv('DS_BASE_URL')
api_key = os.getenv('DS_API_KEY')
model_v3 = os.getenv('DS_MODEL_V3')

# 设置环境变量
os.environ['OPENAI_API_KEY'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url
# os.environ['OPENAI_API_KEY'] = env_vars['DS_API_KEY']
# os.environ['OPENAI_BASE_URL'] = env_vars['DS_BASE_URL']

llm = ChatOpenAI(
    base_url=base_url,
    model=model_v3,
    api_key=SecretStr(api_key),
    temperature=0.6,
    streaming=True,
    max_tokens=4096,
    request_timeout=60
)

async def browser_use_agent(task):
    agent = Agent(
        task=task,
        # planner_llm='', # 规划模型，默认不启用，也可以使用较小的模型仅仅进行规划工作
        # use_vision=True, # 是否启用模型视觉理解
        # max_steps = 100, # 最大步数，默认100
        generate_gif = False, # 是否录制浏览器过程生成 GIF。为 True 时自动生成随机文件名；为字符串时将 GIF 存储到该路径。
        llm=llm
    )
    result = await agent.run()
    return result

def read_test_cases(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('test_cases', [])
    except Exception as e:
        logging.error(f"读取测试用例文件失败: {str(e)}")
        return []

def build_task_prompt(test_case):
    # 只提取需要的字段
    title = test_case.get('title', '')
    steps = test_case.get('steps', [])
    expected_results = test_case.get('expected_results', [])
    
    # 构建任务提示
    prompt = f"测试用例标题: {title}\n\n"
    prompt += "测试步骤:\n"
    for i, step in enumerate(steps, 1):
        prompt += f"{i}. {step}\n"
    
    prompt += "\n预期结果:\n"
    for i, result in enumerate(expected_results, 1):
        prompt += f"{i}. {result}\n"
    
    return prompt


if __name__ == "__main__":
    # 测试用例文件路径
    test_case_file_path = r'C:\\Users\\liut2\\Desktop\\Auto_Generate_Test_Cases\\ui_tst_case.json'
    
    # 读取测试用例
    test_cases = read_test_cases(test_case_file_path)
    
    # 遍历并执行每个测试用例
    for test_case in test_cases:
        extracted_case = {
            'title': test_case.get('title', ''),
            'steps': test_case.get('steps', []),
            'expected_results': test_case.get('expected_results', [])
        }
        
        task_prompt = build_task_prompt(extracted_case)
        # print(f"\n执行测试用例: {test_case.get('id', '')}")
        # print(f"任务提示:\n{task_prompt}")
        
        # 执行测试用例并获取结果
        actual_results = asyncio.run(browser_use_agent(task_prompt))
        
        # 断言
        final_result = actual_results.final_result()
        print(final_result)
        result = actual_results.is_successful()
        
        if result == True:
            print("✅ 测试通过")
        elif result == False:
            print(f"❌ 测试失败: {message}")
        else:  # result == 'warning'
            print(f"⚠️ 警告: {message}")
        
        print("-" * 50)  # 分隔线
