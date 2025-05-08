import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from datetime import datetime

class JsonUtils:
    @staticmethod
    def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
        """
        加载JSONL文件
        
        Args:
            file_path: JSONL文件路径
            
        Returns:
            List[Dict[str, Any]]: 加载的数据列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [json.loads(line) for line in f if line.strip()]
        except Exception as e:
            raise ValueError(f"无法读取JSONL文件: {str(e)}")
    
    @staticmethod
    def save_jsonl(data: List[Dict[str, Any]], file_path: str):
        """
        保存数据到JSONL文件
        
        Args:
            data: 要保存的数据列表
            file_path: 保存路径
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        except Exception as e:
            raise ValueError(f"保存JSONL文件失败: {str(e)}")
    
    @staticmethod
    def load_json(file_path: str) -> Dict[str, Any]:
        """
        加载JSON文件
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Dict[str, Any]: 加载的数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"无法读取JSON文件: {str(e)}")
    
    @staticmethod
    def save_json(data: Dict[str, Any], file_path: str):
        """
        保存数据到JSON文件
        
        Args:
            data: 要保存的数据
            file_path: 保存路径
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise ValueError(f"保存JSON文件失败: {str(e)}")
    
    @staticmethod
    def load_or_create_jsonl(jsonl_path: str) -> List[Dict]:
        """
        加载或创建JSONL文件
        
        Args:
            jsonl_path: JSONL文件路径
            
        Returns:
            List[Dict]: 数据列表
        """
        try:
            path = Path(jsonl_path)
            if path.exists():
                return JsonUtils.load_jsonl(jsonl_path)
            else:
                # 创建新的JSONL文件
                data = []
                JsonUtils.save_jsonl(data, jsonl_path)
                return data
        except Exception as e:
            raise ValueError(f"无法处理JSONL文件: {str(e)}")
    
    @staticmethod
    def add_queries(jsonl_path: str, queries: List[Dict[str, str]]):
        """
        添加新的查询
        
        Args:
            jsonl_path: JSONL文件路径
            queries: 查询列表，每个查询包含query_id和query_text
        """
        data = JsonUtils.load_jsonl(jsonl_path)
        for query in queries:
            new_query = {
                'query_id': query['query_id'],
                'query_text': query['query_text'],
                'query_result': [],
                'annotation_status': 'pending',
                'relevant_docs': [],
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            data.append(new_query)
        
        # 保存更改
        JsonUtils.save_jsonl(data, jsonl_path)
    
    
    @staticmethod
    def update_annotation(jsonl_path: str, query_id: str, relevant_docs: List[Dict]):
        """
        更新标注结果
        
        Args:
            jsonl_path: JSONL文件路径
            query_id: 查询ID
            relevant_docs: 相关文档列表
        """
        try:
            data = JsonUtils.load_jsonl(jsonl_path)
            # 查找对应的查询
            for query in data:
                if query['query_id'] == query_id:
                    query['relevant_docs'] = relevant_docs
                    JsonUtils.save_jsonl(data, jsonl_path)
                    return
            
            raise ValueError(f"未找到查询ID: {query_id}")
        except Exception as e:
            raise ValueError(f"更新标注结果失败: {str(e)}")
    
    @staticmethod
    def get_pending_queries(jsonl_path: str) -> List[Dict]:
        """
        获取待处理的查询
        
        Args:
            jsonl_path: JSONL文件路径
            
        Returns:
            List[Dict]: 待处理的查询列表
        """
        data = JsonUtils.load_jsonl(jsonl_path)
        return [query for query in data if query['annotation_status'] == 'pending']
    
    @staticmethod
    def get_completed_queries(jsonl_path: str) -> List[Dict]:
        """
        获取已完成的查询
        
        Args:
            jsonl_path: JSONL文件路径
            
        Returns:
            List[Dict]: 已完成的查询列表
        """
        data = JsonUtils.load_jsonl(jsonl_path)
        return [query for query in data if query['annotation_status'] == 'completed']
    
    @staticmethod
    def export_dataset(jsonl_path: str, output_path: str):
        """
        导出数据集
        
        Args:
            jsonl_path: 源JSONL文件路径
            output_path: 输出文件路径
        """
        try:
            data = JsonUtils.load_jsonl(jsonl_path)
            JsonUtils.save_jsonl(data, output_path)
        except Exception as e:
            raise ValueError(f"导出数据集失败: {str(e)}")

def main():
    # 使用示例
    jsonl_path = 'search_eval/search_evaluation.jsonl'
    
    # 添加示例查询
    queries = [
        {'query_id': 'q1', 'query_text': 'Python异常处理最佳实践'},
        {'query_id': 'q2', 'query_text': '机器学习模型评估方法'}
    ]
    JsonUtils.add_queries(jsonl_path, queries)
    
    # 搜索查询
    api_url = "YOUR_API_URL_HERE"
    request_body_template = {
        "query": "",
        # 其他API参数
    }
    JsonUtils.search_queries(jsonl_path, api_url, request_body_template)
    
    # 更新标注
    relevant_docs = [
        {
            "doc_id": "doc1",
            "title": "Python异常处理完全指南",
            "relevance_score": 2
        }
    ]
    JsonUtils.update_annotation(jsonl_path, 'q1', relevant_docs)
    
    # 导出数据集
    JsonUtils.export_dataset(jsonl_path, 'search_eval/annotated_dataset.jsonl')

if __name__ == "__main__":
    main() 