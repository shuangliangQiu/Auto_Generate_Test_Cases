# src/services/test_case_generator.py
from typing import Dict, List, Set
import logging
from models.test_case import TestCase
from models.template import Template

logger = logging.getLogger(__name__)

class TestCaseGenerator:
    """测试用例生成服务，基于分析结果生成测试用例。"""
    
    def __init__(self):
        self.current_template: Template = None
        self.max_cases_per_requirement = 5
        self.generated_titles: Set[str] = set()
        
    async def generate_test_cases(self, 
                                analysis_result: Dict,
                                template: Template) -> List[TestCase]:
        """基于分析结果和模板生成测试用例。"""
        try:
            self.current_template = template
            self.generated_titles.clear()
            test_cases = []
            
            # 生成功能测试用例
            func_cases = self._generate_functional_test_cases(
                analysis_result.get('functional_requirements', [])
            )
            test_cases.extend(func_cases)
            
            # 生成非功能测试用例
            nfunc_cases = self._generate_non_functional_test_cases(
                analysis_result.get('non_functional_requirements', [])
            )
            test_cases.extend(nfunc_cases)
            
            # 生成边界测试用例
            edge_cases = self._generate_edge_cases(analysis_result)
            test_cases.extend(edge_cases)
            
            return test_cases
            
        except Exception as e:
            logger.error(f"生成测试用例时出错: {str(e)}")
            raise
    
    def _generate_functional_test_cases(self, requirements: List[str]) -> List[TestCase]:
        """生成功能需求的测试用例。"""
        test_cases = []
        for req in requirements:
            cases_count = 0
            while cases_count < self.max_cases_per_requirement:
                title = self._generate_unique_title(f"验证 {req}", cases_count)
                if not title:
                    break
                    
                test_case = TestCase(
                    title=title,
                    description=f"验证需求的测试用例: {req}",
                    preconditions=self._generate_preconditions(req),
                    steps=self._generate_steps(req),
                    expected_results=self._generate_expected_results(req),
                    priority="高",
                    category="功能测试"
                )
                test_cases.append(test_case)
                cases_count += 1
        return test_cases
    
    def _generate_non_functional_test_cases(self, requirements: List[str]) -> List[TestCase]:
        """生成非功能需求的测试用例。"""
        test_cases = []
        for req in requirements:
            cases_count = 0
            while cases_count < self.max_cases_per_requirement:
                title = self._generate_unique_title(f"验证 {req}", cases_count)
                if not title:
                    break
                    
                test_case = TestCase(
                    title=title,
                    description=f"非功能需求测试用例: {req}",
                    preconditions=self._generate_preconditions(req),
                    steps=self._generate_steps(req),
                    expected_results=self._generate_expected_results(req),
                    priority="中",
                    category="非功能测试"
                )
                test_cases.append(test_case)
                cases_count += 1
        return test_cases
    
    def _generate_edge_cases(self, analysis_result: Dict) -> List[TestCase]:
        """生成边界情况和错误场景的测试用例。"""
        edge_cases = []
        risk_areas = analysis_result.get('risk_areas', [])
        
        for risk in risk_areas:
            cases_count = 0
            while cases_count < self.max_cases_per_requirement:
                title = self._generate_unique_title(f"边界情况: {risk}", cases_count)
                if not title:
                    break
                    
                test_case = TestCase(
                    title=title,
                    description=f"边界情况测试场景: {risk}",
                    preconditions=self._generate_preconditions(risk),
                    steps=self._generate_steps(risk),
                    expected_results=self._generate_expected_results(risk),
                    priority="高",
                    category="边界测试"
                )
                edge_cases.append(test_case)
                cases_count += 1
        
        return edge_cases
    
    def _generate_unique_title(self, base_title: str, count: int) -> str:
        """生成唯一的测试用例标题。"""
        if count == 0:
            title = base_title
        else:
            title = f"{base_title} - 变体 {count}"
            
        if title in self.generated_titles:
            return None
            
        self.generated_titles.add(title)
        return title
    
    def _generate_preconditions(self, requirement: str) -> List[str]:
        """基于需求生成测试前置条件。"""
        return [
            "系统处于初始状态",
            "测试数据已准备就绪",
            f"{requirement} 的访问权限已设置"
        ]
    
    def _generate_steps(self, requirement: str) -> List[str]:
        """基于需求生成测试步骤。"""
        return [
            "准备测试环境",
            "准备测试数据",
            f"执行测试: {requirement}",
            "验证结果",
            "清理测试环境"
        ]
    
    def _generate_expected_results(self, requirement: str) -> List[str]:
        """基于需求生成预期结果。"""
        return [
            f"系统成功处理 {requirement}",
            "未产生错误或警告",
            "系统状态保持一致"
        ]