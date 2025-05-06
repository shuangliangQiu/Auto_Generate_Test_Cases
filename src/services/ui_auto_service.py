import logging
from datetime import datetime
import pandas as pd
from src.agents.browser_use_agent import browser_use_agent, read_test_cases

logger = logging.getLogger(__name__)

class UIAutoService:
    def __init__(self, concurrent_workers: int = 1):
        self.test_cases = []
        self.test_results = []

    async def run_ui_tests(self, input_path: str, output_path: str):
        """运行UI自动化测试并将结果导出到Excel
        
        Args:
            input_path: 测试用例文件路径，从cli的--input参数获取
            output_path: 测试结果输出路径
        """
        try:
            # 读取测试用例
            logger.info(f"从 {input_path} 读取测试用例")
            self.test_cases = read_test_cases(input_path)
            
            if not self.test_cases:
                logger.error("未找到测试用例")
                return {
                    "status": "error",
                    "message": "未找到测试用例"
                }
            
            # 执行每个测试用例
            for test_case in self.test_cases:
                result = await self._execute_test_case(test_case)
                self.test_results.append(result)
            
            # 导出结果到Excel
            await self._export_to_excel(output_path)
            
            return {
                "status": "success",
                "message": f"UI自动化测试完成，结果已导出到: {output_path}",
                "total_cases": len(self.test_cases),
                "passed_cases": sum(1 for r in self.test_results if r["status"] == "passed")
            }
            
        except Exception as e:
            logger.error(f"UI自动化测试执行失败: {str(e)}")
            return {
                "status": "error",
                "message": f"UI自动化测试执行失败: {str(e)}"
            }

    async def _execute_test_case(self, test_case):
        """执行单个测试用例,测试用例是json形式"""
        try:
            # 构建任务提示
            task_prompt = self._build_task_prompt(test_case)
            
            #执行测试
            actual_results = await browser_use_agent(task_prompt)
            
            # 获取测试结果
            final_result = actual_results.final_result()
            is_successful = actual_results.is_successful()
            
            return {
                "test_case_id": test_case.get("id", ""),
                "title": test_case.get("title", ""),
                "steps": test_case.get("steps", []),
                "expected_results": test_case.get("expected_results", []),
                "actual_result": final_result,
                "status": "passed" if is_successful == True else "failed" if is_successful == False else "warning",
                "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"测试用例执行失败: {str(e)}")
            return {
                "test_case_id": test_case.get("id", ""),
                "title": test_case.get("title", ""),
                "steps": test_case.get("steps", []),
                "expected_results": test_case.get("expected_results", []),
                "actual_result": str(e),
                "status": "error",
                "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    def _build_task_prompt(self, test_case):
        """构建任务提示"""
        title = test_case.get("title", "")
        steps = test_case.get("steps", [])
        expected_results = test_case.get("expected_results", [])
        
        prompt = f"测试用例标题: {title}\n\n"
        prompt += "测试步骤:\n"
        for i, step in enumerate(steps, 1):
            prompt += f"{i}. {step}\n"
        
        prompt += "\n预期结果:\n"
        for i, result in enumerate(expected_results, 1):
            prompt += f"{i}. {result}\n"
        
        return prompt

    async def _export_to_excel(self, output_path: str):
        """导出测试结果到Excel"""
        try:
            # 确保输出路径以.xlsx结尾
            if not output_path.endswith('.xlsx'):
                output_path = output_path + '.xlsx'
            
            # 创建DataFrame
            df = pd.DataFrame(self.test_results)
            
            # 重新排列列顺序
            columns = [
                "test_case_id",
                "title",
                "steps",
                "expected_results",
                "actual_result",
                "status",
                "execution_time"
            ]
            df = df[columns]
            
            # 导出到Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            logger.info(f"测试结果已导出到: {output_path}")
            
        except Exception as e:
            logger.error(f"导出Excel失败: {str(e)}")
            raise