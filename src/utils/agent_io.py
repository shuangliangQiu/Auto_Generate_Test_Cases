# src/utils/agent_io.py
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AgentIO:
    """处理Agent结果的序列化和反序列化
    
    这个类提供了保存和加载Agent执行结果的功能，使各个Agent之间的数据流转更加清晰。
    每个Agent的结果将被保存为单独的JSON文件，并可以在需要时被其他Agent读取。
    """
    
    def __init__(self, output_dir: str = "agent_results"):
        """初始化AgentIO
        
        Args:
            output_dir: 保存Agent结果的目录，默认为'agent_results'
        """
        self.output_dir = output_dir
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
    
    def save_result(self, agent_name: str, result: Dict[str, Any]) -> str:
        """将Agent的执行结果保存为JSON文件
        
        Args:
            agent_name: Agent的名称，用于生成文件名
            result: 要保存的结果数据
            
        Returns:
            保存的文件路径
        """
        file_path = os.path.join(self.output_dir, f"{agent_name}_result.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存{agent_name}的执行结果到{file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存{agent_name}结果时出错: {str(e)}")
            raise
    
    def load_result(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """加载指定Agent的执行结果
        
        Args:
            agent_name: Agent的名称，用于查找文件
            
        Returns:
            加载的结果数据，如果文件不存在则返回None
        """
        file_path = os.path.join(self.output_dir, f"{agent_name}_result.json")
        if not os.path.exists(file_path):
            logger.warning(f"找不到{agent_name}的结果文件: {file_path}")
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            logger.info(f"已加载{agent_name}的执行结果")
            return result
        except Exception as e:
            logger.error(f"加载{agent_name}结果时出错: {str(e)}")
            return None