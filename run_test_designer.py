# 从项目根目录运行测试设计器
from src.agents.test_designer import TestDesignerAgent

if __name__ == "__main__":
    # 创建测试设计代理
    designer = TestDesignerAgent()

    # 准备需求数据
    requirements = {
        "original_doc": "原始需求文档内容",
        "analysis_result": {
            "functional_requirements": ["账号密码登录", "检查模块名称为法律检索"],
            "non_functional_requirements": ["性能要求", "安全要求"],
            "test_scenarios": ["正确的账号密码登录", "错误的账号密码登录","检查模块名字为法律检索"],
            "risk_areas": ["风险1", "风险2"]
        }
    }

    # 生成测试策略
    test_strategy = designer.design(requirements)
    print(test_strategy)