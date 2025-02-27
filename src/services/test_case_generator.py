import json
from typing import List, Dict
from datetime import datetime
from models.test_case import TestCase
from schemas.communication import TestScenario

class TestCaseGenerator:
    def __init__(self, template_path: str = "src/templates/functional_test_template.json"):
        self.template_path = template_path
        self.base_template = self._load_template()

    def _load_template(self) -> Dict:
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "test_scenarios": [],
                "common_parameters": {
                    "file_types": ["pdf", "jpg", "png"],
                    "batch_size": 10,
                    "expected_output_formats": ["docx"]
                }
            }

    def generate_for_certification(self, scenarios: List[TestScenario]) -> List[TestCase]:
        """生成资质证照整理专项测试用例"""
        test_cases = []
        
        # 文件上传相关测试用例
        test_cases.extend(self._generate_upload_cases(scenarios))
        
        # AI内容提取验证用例
        test_cases.extend(self._generate_ai_validation_cases(scenarios))
        
        # 溯源功能验证用例
        test_cases.extend(self._generate_traceability_cases(scenarios))
        
        return test_cases

    def _generate_upload_cases(self, scenarios: List[TestScenario]) -> List[TestCase]:
        """生成文件上传相关测试用例"""
        cases = []
        base_params = self.base_template.get("common_parameters", {})
        
        for scenario in scenarios:
            if "文件上传" in scenario.description:
                case = TestCase(
                    title=f"文件格式验证 - {scenario.description}",
                    scenario=scenario,
                    steps=[
                        "上传包含PDF、JPG、PNG格式的混合文件",
                        "尝试上传非允许格式文件（如.exe）"
                    ],
                    expected_results=[
                        "支持文件类型应成功上传",
                        "非允许格式应显示错误提示"
                    ],
                    test_data={
                        "valid_files": base_params["file_types"],
                        "invalid_types": ["exe", "bat"]
                    }
                )
                cases.append(case)
        return cases

    def _generate_ai_validation_cases(self, scenarios: List[TestScenario]) -> List[TestCase]:
        """生成AI内容提取验证用例"""
        cases = []
        for scenario in scenarios:
            if "AI识别" in scenario.description:
                case = TestCase(
                    title=f"AI内容提取验证 - {scenario.description}",
                    scenario=scenario,
                    steps=[
                        "上传包含营业执照、身份证的样本文件",
                        "执行自动整理功能"
                    ],
                    expected_results=[
                        "关键字段提取准确率 ≥98%",
                        "非结构化数据保持原文完整性"
                    ],
                    validation_rules={
                        "accuracy_threshold": 0.98,
                        "allowed_deviation": 0.02
                    }
                )
                cases.append(case)
        return cases

    def _generate_traceability_cases(self, scenarios: List[TestScenario]) -> List[TestCase]:
        """生成溯源功能验证用例"""
        cases = []
        for scenario in scenarios:
            if "溯源功能" in scenario.description:
                case = TestCase(
                    title=f"溯源信息验证 - {scenario.description}",
                    scenario=scenario,
                    steps=[
                        "在整理结果中选择任意字段",
                        "点击查看溯源信息"
                    ],
                    expected_results=[
                        "显示来源文件的截图片段",
                        "截图时间戳与处理时间一致"
                    ],
                    traceability_params={
                        "screenshot_required": True,
                        "timestamp_format": "%Y-%m-%d %H:%M:%S"
                    }
                )
                cases.append(case)
                
                # 性能测试用例
                perf_case = TestCase(
                    title=f"溯源响应性能 - {scenario.description}",
                    scenario=scenario,
                    steps=[
                        "同时发起100个溯源查看请求"
                    ],
                    expected_results=[
                        "平均响应时间 <2秒",
                        "错误率 <1%"
                    ],
                    performance_params={
                        "concurrent_users": 100,
                        "max_response_time": 2,
                        "error_rate_threshold": 0.01
                    }
                )
                cases.append(perf_case)
        return cases