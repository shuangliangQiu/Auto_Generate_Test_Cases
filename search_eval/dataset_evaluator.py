import json
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from json_utils import JsonUtils
from annotation_tool import AnnotationTool
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import requests

class SearchEvaluator:
    def __init__(self, jsonl_path: str):
        self.jsonl_path = Path(jsonl_path)
        self.output_dir = Path('evaluation_results')
        self.output_dir.mkdir(exist_ok=True)
        
    def evaluate(self, 
                k_values: List[int] = [1, 3, 5, 10],
                relevance_threshold: int = 1,
                output_path: Optional[str] = None,
                offline_mode: bool = False) -> Dict:
        """
        评估搜索系统性能
        
        Args:
            k_values: 评估的K值列表
            relevance_threshold: 判定为相关的最小相关性分数
            output_path: 评估结果保存路径
            offline_mode: 是否使用离线模式（使用已有搜索结果）
            
        Returns:
            Dict: 评估结果
        """
        data = JsonUtils.load_jsonl(self.jsonl_path)
        needs_annotation = any('relevant_docs' not in query for query in data)
        if needs_annotation:
            print("启动标注工具进行标注...")
            annotation_tool = AnnotationTool(str(self.jsonl_path))
            annotation_tool.run()
            data = JsonUtils.load_jsonl(self.jsonl_path)
        else:
            print("所有数据已完成标注，跳过标注步骤")
        
        # 准备评估数据
        queries = []
        for query in data:
            query_result = query.get('query_result', [])
            if isinstance(query_result, str):
                try:
                    query_result = json.loads(query_result)
                except json.JSONDecodeError:
                    print(f"警告：查询 {query['query_id']} 的结果格式无效，跳过")
                    continue
            
            relevant_docs = query.get('relevant_docs', [])
            if isinstance(relevant_docs, str):
                try:
                    relevant_docs = json.loads(relevant_docs)
                except json.JSONDecodeError:
                    print(f"警告：查询 {query['query_id']} 的相关文档格式无效，跳过")
                    continue
            
            query_data = {
                'query': query['query_text'],
                'query_id': query['query_id'],
                'search_results': query_result,
                'relevant_docs': relevant_docs
            }
            queries.append(query_data)
        
        # 计算评估指标
        metrics = self._calculate_metrics(queries, k_values, relevance_threshold)
        
        results = {
            'evaluation_params': {
                'relevance_threshold': relevance_threshold,
                'k_values': k_values,
                'mode': 'offline' if offline_mode else 'online'
            },
            'metrics': metrics
        }
        
        if output_path:
            self._save_results(results, output_path)
        
        return results
    
    def _calculate_metrics(self, queries: List[Dict], k_values: List[int], relevance_threshold: int) -> Dict:
        """计算评估指标"""
        metrics = {
            'map': 0.0,
            'mrr': 0.0
        }
        
        # 初始化K值相关指标
        for k in k_values:
            metrics[f'precision@{k}'] = 0.0
            metrics[f'recall@{k}'] = 0.0
            metrics[f'f1@{k}'] = 0.0
            metrics[f'hit_rate@{k}'] = 0.0  # 添加hit rate@k
        
        total_queries = len(queries)
        if total_queries == 0:
            return metrics
        
        all_precision_points = []
        all_recall_points = []
        
        for query_data in queries:
            search_results = query_data['search_results']
            relevant_docs = query_data['relevant_docs']
            
            # 获取相关文档ID列表
            relevant_doc_ids = [doc['doc_id'] for doc in relevant_docs if doc['relevance_score'] >= relevance_threshold]
            
            # 计算MRR
            mrr = self._calculate_mrr(search_results, relevant_doc_ids)
            metrics['mrr'] += mrr
            
            # 计算AP并累加到MAP
            ap = self._calculate_average_precision(search_results, relevant_doc_ids)
            metrics['map'] += ap
            
            # 计算不同k值的指标
            for k in k_values:
                precision, recall, f1 = self._calculate_precision_recall_f1(
                    search_results, relevant_doc_ids, k=k)
                metrics[f'precision@{k}'] += precision
                metrics[f'recall@{k}'] += recall
                metrics[f'f1@{k}'] += f1
                
                # 计算hit rate@k
                hit_rate = self._calculate_hit_rate(search_results, relevant_doc_ids, k=k)
                metrics[f'hit_rate@{k}'] += hit_rate
            
            # 计算P-R曲线点
            precision_points, recall_points = self._calculate_pr_curve_points(
                search_results, relevant_doc_ids)
            all_precision_points.append(precision_points)
            all_recall_points.append(recall_points)
        
        # 计算平均值
        for metric in metrics:
            metrics[metric] /= total_queries
        
        # 绘制平均P-R曲线
        if all_precision_points and all_recall_points:
            try:
                avg_precision_points = np.mean(np.array(all_precision_points), axis=0)
                avg_recall_points = np.mean(np.array(all_recall_points), axis=0)
                pr_curve_path = self.output_dir / 'pr_curve.png'
                self._plot_pr_curve(avg_precision_points.tolist(), avg_recall_points.tolist(),
                                  "Average Precision-Recall Curve", str(pr_curve_path))
                print(f"\nP-R曲线已保存至: {pr_curve_path}")
            except Exception as e:
                print(f"\n警告：无法生成P-R曲线 - {str(e)}")
        
        return metrics
    
    def _calculate_mrr(self, search_results: List[Dict], 
                      relevant_doc_ids: List[str], 
                      doc_id_field: str = 'doc_id') -> float:
        """计算MRR值"""
        if not search_results or not relevant_doc_ids:
            return 0.0
        
        for rank, result in enumerate(search_results, 1):
            doc_id = result.get(doc_id_field)
            if doc_id in relevant_doc_ids:
                return 1.0 / rank
        
        return 0.0
    
    def _calculate_precision_recall_f1(self, search_results: List[Dict],
                                     relevant_doc_ids: List[str],
                                     doc_id_field: str = 'doc_id',
                                     k: Optional[int] = None) -> Tuple[float, float, float]:
        """计算Precision@K, Recall@K和F1 Score"""
        if not search_results or not relevant_doc_ids:
            return 0.0, 0.0, 0.0
        
        if k is not None:
            search_results = search_results[:k]
        
        retrieved_relevant = sum(1 for result in search_results 
                               if result.get(doc_id_field) in relevant_doc_ids)
        
        precision = retrieved_relevant / len(search_results) if search_results else 0.0
        recall = retrieved_relevant / len(relevant_doc_ids) if relevant_doc_ids else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return precision, recall, f1
    
    def _calculate_hit_rate(self, search_results: List[Dict],
                          relevant_doc_ids: List[str],
                          doc_id_field: str = 'doc_id',
                          k: Optional[int] = None) -> float:
        """计算命中率"""
        if not search_results or not relevant_doc_ids:
            return 0.0
        
        if k is not None:
            search_results = search_results[:k]
        
        for result in search_results:
            if result.get(doc_id_field) in relevant_doc_ids:
                return 1.0
        return 0.0
    
    def _calculate_pr_curve_points(self, search_results: List[Dict],
                                 relevant_doc_ids: List[str],
                                 doc_id_field: str = 'doc_id') -> Tuple[List[float], List[float]]:
        """计算P-R曲线的点"""
        precision_points = []
        recall_points = []
        
        for k in range(1, len(search_results) + 1):
            precision, recall, _ = self._calculate_precision_recall_f1(
                search_results, relevant_doc_ids, doc_id_field, k)
            precision_points.append(precision)
            recall_points.append(recall)
        
        return precision_points, recall_points
    
    def _plot_pr_curve(self, precision_points: List[float],
                      recall_points: List[float],
                      title: str = "Precision-Recall Curve",
                      save_path: Optional[str] = None) -> None:
        """绘制P-R曲线"""
        try:
            plt.figure(figsize=(10, 6))
            plt.plot(recall_points, precision_points, 'b-', label='P-R Curve')
            plt.xlabel('Recall')
            plt.ylabel('Precision')
            plt.title(title)
            plt.grid(True)
            plt.legend()
            
            if save_path:
                plt.savefig(save_path)
                plt.close()
            else:
                plt.show()
        except Exception as e:
            print(f"警告：无法绘制P-R曲线 - {str(e)}")
            plt.close()
    
    def _calculate_average_precision(self, search_results: List[Dict],
                                   relevant_doc_ids: List[str],
                                   doc_id_field: str = 'doc_id') -> float:
        """计算单个查询的Average Precision (AP)"""
        if not search_results or not relevant_doc_ids:
            return 0.0
        
        relevant_count = 0
        sum_precision = 0.0
        
        for rank, result in enumerate(search_results, 1):
            doc_id = result.get(doc_id_field)
            if doc_id in relevant_doc_ids:
                relevant_count += 1
                # 计算当前位置的precision
                precision = relevant_count / rank
                sum_precision += precision
        
        # AP = 所有相关文档位置的precision之和 / 相关文档总数
        ap = sum_precision / len(relevant_doc_ids) if relevant_doc_ids else 0.0
        return ap
    
    def _save_results(self, results: Dict, output_path: str):
        """保存评估结果"""
        JsonUtils.save_json(results, output_path)

def main(input_path: str):
    print("欢迎使用搜索评估工具")
    print("-" * 50)
    
    # 获取JSONL文件路径
    while True:
        jsonl_path = input_path.strip()
        if not jsonl_path:
            print("路径不能为空，请重新输入")
            continue
            
        # 检查文件是否存在
        if not Path(jsonl_path).exists():
            print(f"错误：文件 '{jsonl_path}' 不存在")
            continue
            
        # 检查文件扩展名
        if not jsonl_path.endswith('.jsonl'):
            print("错误：文件必须是JSONL格式（.jsonl）")
            continue
            
        try:
            # 尝试读取JSONL文件
            data = JsonUtils.load_jsonl(jsonl_path)
            
            # 检查必要的字段是否存在
            required_fields = ['query_id', 'query_text', 'query_result']
            missing_fields = []
            for query in data:
                for field in required_fields:
                    if field not in query:
                        missing_fields.append(field)
                if missing_fields:
                    break
            if missing_fields:
                print(f"错误：JSONL文件缺少必要字段: {', '.join(missing_fields)}")
                continue
                
            break
        except Exception as e:
            print(f"错误：无法读取JSONL文件 - {str(e)}")
            print("请确保：")
            print("1. 文件是有效的JSONL文件")
            print("2. 文件没有被其他程序占用")
            print("3. 文件包含必要的字段：query_id, query_text, query_result")
            continue
    
    try:
        # 创建评估器
        evaluator = SearchEvaluator(jsonl_path)
        
        # 选择评估模式
        while True:
            print("\n请选择评估模式：")
            print("1. 在线评估模式（需要API获取查询结果）")
            print("2. 离线评估模式（使用已有查询结果）")
            mode = input("请输入选项（1或2）: ").strip()
            
            if mode not in ['1', '2']:
                print("无效的选项，请重新输入")
                continue
                
            offline_mode = mode == '2'
            break
        
        # 设置评估参数
        k_values = [1, 3, 5, 10]  # 默认K值
        relevance_threshold = 1   # 默认相关性阈值
        
        # 在线模式
        if not offline_mode:
            api_url = "http://k8s-platform-cloudswa-fe77b476e2-b6ef1b9e2e540b4a/api/v1/intelligent/search"
            headers = {"Content-Type": "application/json", "X-TOKEN": "1"}
            
            # 获取没有检索结果的查询
            queries_without_results = [query for query in data if 'query_result' not in query or not query['query_result']]
            if queries_without_results:
                print(f"\n发现 {len(queries_without_results)} 个没有检索结果的查询，开始获取检索结果...")
                
                for query in queries_without_results:
                    try:
                        # 发送API请求
                        request_data = {
                            "q": query["query_text"],
                            "count": 10,
                            "offset": 0
                        }
                        response = requests.post(api_url, headers=headers, json=request_data)
                        result = response.json()
                        
                        # 解析响应结果并适配到数据集格式
                        if "webPages" in result and "value" in result["webPages"]:
                            query_result = []
                            for item in result["webPages"]["value"]:
                                query_result.append({
                                    "doc_id": item.get("id", ""),
                                    "title": item.get("name", ""),
                                    "content": item.get("snippet", "")
                                })
                            query["query_result"] = query_result
                            print(f"成功获取查询 '{query['query_id']}' 的检索结果")
                        else:
                            print(f"警告：查询 '{query['query_id']}' 的响应格式不符合预期")
                    except Exception as e:
                        print(f"处理查询 '{query['query_id']}' 时出错: {str(e)}")
                
                # 保存更新后的数据
                JsonUtils.save_jsonl(data, jsonl_path)
                print("\n检索结果已更新到数据集")
            else:
                print("\n所有查询都有检索结果")
        
        # 设置输出路径
        output_path = './evaluation_results/evaluation_results.json'
        
        # 检查输出目录是否存在
        output_dir = Path(output_path).parent
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True)
            except Exception as e:
                print(f"错误：无法创建输出目录 - {str(e)}")
                return
        
        print("\n开始评估...")
        # 执行评估
        results = evaluator.evaluate(
            k_values=k_values,
            relevance_threshold=relevance_threshold,
            output_path=output_path,
            offline_mode=offline_mode
        )
        
        # 打印评估结果
        print("\n评估完成！")
        print("-" * 50)
        print(f"评估模式: {'离线' if offline_mode else '在线'}")
        print("\n主要评估指标:")
        print(f"MAP: {results['metrics']['map']:.4f}")
        print(f"MRR: {results['metrics']['mrr']:.4f}")
        
        # 打印不同K值的指标
        print("\n不同K值的评估指标:")
        for k in k_values:
            print(f"\nK = {k}:")
            print(f"Precision@{k}: {results['metrics'][f'precision@{k}']:.4f}")
            print(f"Recall@{k}: {results['metrics'][f'recall@{k}']:.4f}")
            print(f"F1@{k}: {results['metrics'][f'f1@{k}']:.4f}")
            print(f"Hit Rate@{k}: {results['metrics'][f'hit_rate@{k}']:.4f}")
        
        print("\n详细评估结果已保存至:", output_path)
        
    except Exception as e:
        print(f"\n评估过程中出现错误: {str(e)}")
        return

if __name__ == "__main__":
    input_path = 'search_eval/search_evaluation.jsonl'
    main(input_path)