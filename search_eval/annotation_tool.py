import json
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List
from pathlib import Path
from json_utils import JsonUtils
from datetime import datetime

"""
小型评估数据集：50-100个查询
标准评估数据集：200-500个查询
大型评估数据集：1000+个查询

每个查询建议标注：
- 相关文档：3-10个
- 部分相关文档：5-15个
- 不相关文档：10-20个

标注注意事项：
- 确保查询多样性
- 考虑不同难度级别
- 包含边界情况
"""

class AnnotationTool:
    def __init__(self, jsonl_path: str):
        self.root = tk.Tk()
        self.root.title("搜索结果标注工具")
        self.root.geometry("800x600")
        
        self.jsonl_path = Path(jsonl_path)
        # 只加载未标注的数据
        self.data = [query for query in JsonUtils.load_jsonl(jsonl_path) 
                    if query.get('annotation_status') != 'completed']
        
        if not self.data:
            messagebox.showinfo("提示", "没有需要标注的数据！")
            self.root.quit()
            return
        
        # 检查必要的字段
        required_fields = ['query_id', 'query_text', 'query_result']
        for query in self.data:
            for field in required_fields:
                if field not in query:
                    raise ValueError(f"JSONL文件缺少必要字段: {field}")
        
        # 添加relevant_docs字段（如果不存在）
        for query in self.data:
            if 'relevant_docs' not in query:
                query['relevant_docs'] = []
        
        self.current_query_index = 0
        self._init_ui()
        self._load_next_query()
    
    def _init_ui(self):
        # 查询信息区域
        query_frame = ttk.LabelFrame(self.root, text="查询信息", padding="5")
        query_frame.pack(fill="x", padx=5, pady=5)
        
        # 查询ID
        ttk.Label(query_frame, text="查询ID:").pack(anchor="w")
        self.query_id_label = ttk.Label(query_frame, text="")
        self.query_id_label.pack(anchor="w")
        
        # 查询文本
        ttk.Label(query_frame, text="查询文本:").pack(anchor="w")
        self.query_text_label = ttk.Label(query_frame, text="")
        self.query_text_label.pack(anchor="w")
        
        # 搜索结果区域
        results_frame = ttk.LabelFrame(self.root, text="搜索结果", padding="5")
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 创建树形视图
        columns = ("doc_id", "title", "content", "relevance")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings")
        
        # 设置列标题
        self.results_tree.heading("doc_id", text="文档ID")
        self.results_tree.heading("title", text="标题")
        self.results_tree.heading("content", text="内容")
        self.results_tree.heading("relevance", text="相关性")
        
        # 设置列宽
        self.results_tree.column("doc_id", width=100)
        self.results_tree.column("title", width=200)
        self.results_tree.column("content", width=300)
        self.results_tree.column("relevance", width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置树形视图和滚动条
        self.results_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 添加相关性选择区域
        relevance_frame = ttk.LabelFrame(self.root, text="相关性标注", padding="5")
        relevance_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(relevance_frame, text="相关性说明：").pack(anchor="w")
        ttk.Label(relevance_frame, text="2 - 完全相关").pack(anchor="w")
        ttk.Label(relevance_frame, text="1 - 部分相关").pack(anchor="w")
        ttk.Label(relevance_frame, text="0 - 不相关").pack(anchor="w")
        
        # 控制区域
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(control_frame, text="保存标注", command=self._save_annotation).pack(side="left", padx=5)
        ttk.Button(control_frame, text="下一个查询", command=self._load_next_query).pack(side="left", padx=5)
        
        # 添加进度显示
        self.progress_label = ttk.Label(control_frame, text="")
        self.progress_label.pack(side="right", padx=5)
        
        # 绑定双击事件
        self.results_tree.bind('<Double-1>', self._on_double_click)
        
    def _on_double_click(self, event):
        """处理双击事件，用于修改相关性分数"""
        item = self.results_tree.selection()[0]
        current_values = self.results_tree.item(item)["values"]
        current_score = int(current_values[3])
        
        # 循环切换相关性分数：0 -> 1 -> 2 -> 0
        new_score = (current_score + 1) % 3
        self.results_tree.item(item, values=(*current_values[:3], str(new_score)))
        
    def _load_next_query(self):
        """加载下一个待标注的查询"""
        if self.current_query_index < len(self.data):
            query = self.data[self.current_query_index]
            self.query_id_label.config(text=query['query_id'])
            self.query_text_label.config(text=query['query_text'])
            
            # 更新进度显示
            self.progress_label.config(text=f"进度: {self.current_query_index + 1}/{len(self.data)}")
            
            # 清空并加载搜索结果
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            try:
                search_results = query['query_result']
                for result in search_results:
                    # 检查是否已有标注
                    relevance_score = '0'
                    for doc in query.get('relevant_docs', []):
                        if doc['doc_id'] == result['doc_id']:
                            relevance_score = str(doc['relevance_score'])
                            break
                    
                    self.results_tree.insert("", "end", values=(
                        result.get('doc_id', ''),
                        result.get('title', ''),
                        result.get('content', ''),
                        relevance_score
                    ))
            except Exception as e:
                messagebox.showerror("错误", f"查询结果格式错误: {query['query_id']}")
                return
        else:
            messagebox.showinfo("完成", "所有查询都已标注完成！")
            self.root.quit()
    
    def _save_annotation(self):
        """保存当前查询的标注结果"""
        if self.current_query_index >= len(self.data):
            return
            
        query = self.data[self.current_query_index]
        relevant_docs = []
        for item in self.results_tree.get_children():
            values = self.results_tree.item(item)["values"]
            if values[3] != '0':  # 只保存有相关性分数的文档
                relevant_docs.append({
                    "doc_id": values[0],
                    "title": values[1],
                    "relevance_score": int(values[3])
                })
        
        # 读取完整的数据集
        all_data = JsonUtils.load_jsonl(self.jsonl_path)
        
        # 更新当前查询的标注结果
        for item in all_data:
            if item['query_id'] == query['query_id']:
                item['relevant_docs'] = relevant_docs
                item['annotation_status'] = 'completed'
                item['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break
        
        # 保存更新后的完整数据集
        JsonUtils.save_jsonl(all_data, self.jsonl_path)
        
        messagebox.showinfo("成功", "标注已保存")
        
        # 移动到下一个查询
        self.current_query_index += 1
        self._load_next_query()
    
    def run(self):
        self.root.mainloop()

def main():
    # 使用示例
    jsonl_path = 'search_eval/search_evaluation.jsonl'
    tool = AnnotationTool(jsonl_path)
    tool.run()

if __name__ == "__main__":
    main() 