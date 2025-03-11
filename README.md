# 自动化测试用例生成工具

基于Python开发的AI测试系统，利用AutoGen框架和多个AI代理自动分析需求并生成测试用例。

## 功能特点

- 📝 基于AI的自动需求分析
- 🤖 基于AutoGen框架的多代理系统
- 📋 可配置的测试用例模板和格式
- 📊 支持Excel格式导出
- 🔄 支持多种文档格式（PDF、Word、Markdown、Text）
- ⚙️ 可扩展的架构设计

## 版本说明
- 📝 当前版本尚不支持接口测试用例生成，仅仅是加了入口，请使用功能测试
- 📋 未来 3 个版本会将功能测试用例生成功能进一步开发，包括生成测试用例性能提升
- 🤖 功能测试开发到一定阶段后，会着手开发生成接口测试用例，并支持自动执行接口测试
- 🔄 UI自动化测试在规划中，莫催，一切都会有的，争取在 2025 年上半年推出。

## 安装说明

1. 克隆代码仓库：
```bash
git clone <repository-url>
cd Auto_Generate_Test_Cases
```

2. 创建并激活虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Windows系统使用: .venv\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 配置系统：
- 复制配置文件模板：
```bash
cp .env.example .env
```
- 在.env 中更新OpenAI API密钥和其他设置

## 使用方法

本工具支持通过命令行参数来控制测试用例的生成：

```bash
python src/main.py -d <需求文档路径> [-o <输出文件路径>] [-t <测试类型>]
```

### 命令行参数说明

- `-d, --doc`：必需参数，指定需求文档的路径，支持PDF、Word、Markdown或Text格式
- `-o, --output`：可选参数，指定测试用例输出文件路径，默认为"test_cases.xlsx"
- `-t, --type`：可选参数，指定测试类型，可选值：
  - `functional`：功能测试（默认值）
  - `api`：接口测试

### 使用示例

1. 生成功能测试用例：
```bash
python src/main.py -d docs/需求文档.pdf -o 功能测试用例.xlsx
# 或
python src/main.py -d docs/需求文档.pdf -t functional -o 功能测试用例.xlsx
```

2. 生成接口测试用例：
```bash
python src/main.py -d docs/接口文档.md -t api -o 接口测试用例.xlsx
```

## 项目结构

```
/
├── .cache/                # 缓存目录
├── .env                   # 环境变量配置文件
├── agent_results/         # 代理执行结果存储目录
│   ├── quality_assurance_result.json    # 质量保证代理结果
│   ├── requirement_analyst_result.json  # 需求分析代理结果
│   ├── test_case_writer_result.json     # 测试用例编写代理结果
│   └── test_designer_result.json        # 测试设计代理结果
├── config.json            # 全局配置文件
├── docs/                  # 文档目录
│   ├── prd.md                # 产品需求文档
│   ├── system_design.json    # 系统设计文档
│   └── 需求文档示例.pdf       # 示例需求文档
├── logs/                  # 日志目录
├── requirements.txt       # 项目依赖
├── src/                   # 源代码目录
│   ├── agents/                 # AutoGen框架的AI智能体
│   │   ├── requirement_analyst.py  # 需求分析智能体
│   │   ├── test_designer.py       # 测试设计智能体
│   │   ├── test_case_writer.py    # 测试用例编写智能体
│   │   ├── quality_assurance.py   # 质量保证智能体
│   │   └── assistant.py           # 助手智能体
│   ├── services/               # 核心服务
│   │   ├── document_processor.py   # 文档处理服务
│   │   ├── test_case_generator.py # 测试用例生成服务
│   │   └── export_service.py      # 导出服务
│   ├── models/                 # 数据模型
│   │   ├── test_case.py          # 测试用例模型
│   │   └── template.py           # 模板模型
│   ├── schemas/                # 数据结构模式
│   │   └── communication.py      # 通信数据结构
│   ├── templates/              # 测试用例模板
│   │   ├── api_test_template.json     # API测试模板
│   │   └── functional_test_template.json  # 功能测试模板
│   ├── utils/                  # 工具类
│   │   ├── logger.py             # 日志工具
│   │   ├── cli_parser.py         # 命令行参数解析工具
│   │   └── agent_io.py           # 代理IO工具
│   └── main.py                # 应用程序入口
└── template_config.json    # 模板配置文件
```

## 配置说明

系统通过config.json进行配置，主要配置项包括：

- openai_api_key：OpenAI API密钥
- log_level：日志级别（INFO、DEBUG等）
- templates_dir：测试用例模板目录
- output_dir：生成文件输出目录
- 代理特定配置（模型、temperature等）

## 输出结果

- 生成的测试用例将以Excel格式保存在指定的输出路径
- 程序运行日志保存在logs目录下
- 测试用例包含以下信息：
  - 测试用例ID
  - 测试场景
  - 前置条件
  - 测试步骤
  - 预期结果
  - 优先级
  - 备注
