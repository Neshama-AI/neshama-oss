"""
向量存储模块 - 纯 Python 向量检索实现

特性：
- 纯 Python 实现，无需外部依赖
- 支持余弦相似度检索
- 可选的 FAISS/Milvus 等升级路径
- 内存 + 持久化存储
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
import json
import numpy as np
from pathlib import Path
import threading


@dataclass
class VectorEntry:
    """向量条目"""
    id: str
    vector: List[float]
    metadata: Dict[str, Any]


class VectorStore:
    """
    简单向量存储 - 纯 Python 实现
    
    提供基础的向量存储和检索功能。
    生产环境建议升级到 FAISS/Milvus/Qdrant 等专业向量数据库。
    
    使用示例：
        store = VectorStore(dimension=384)
        
        # 添加向量
        store.add("doc1", [0.1] * 384, metadata={"text": "文档内容"})
        
        # 检索
        results = store.search([0.1] * 384, top_k=5)
    """
    
    def __init__(
        self,
        dimension: int = 384,
        storage_path: Optional[str] = None,
        metric: str = "cosine",  # "cosine" | "euclidean"
    ):
        """
        初始化向量存储
        
        Args:
            dimension: 向量维度
            storage_path: 持久化路径
            metric: 距离度量方式
        """
        self._dimension = dimension
        self._storage_path = storage_path
        self._metric = metric
        self._lock = threading.RLock()
        
        # 内存存储
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        
        # 加载已有数据
        if storage_path:
            self._load()
    
    def add(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        添加向量
        
        Args:
            id: 唯一标识
            vector: 向量
            metadata: 元数据
            
        Returns:
            是否成功
        """
        with self._lock:
            try:
                if len(vector) != self._dimension:
                    raise ValueError(
                        f"向量维度不匹配: 期望 {self._dimension}, 实际 {len(vector)}"
                    )
                
                self._vectors[id] = vector
                self._metadata[id] = metadata or {}
                self._save()
                return True
            except Exception as e:
                print(f"[VectorStore] 添加失败: {e}")
                return False
    
    def add_batch(
        self,
        entries: List[Tuple[str, List[float], Optional[Dict[str, Any]]]],
    ) -> int:
        """
        批量添加向量
        
        Args:
            entries: [(id, vector, metadata), ...]
            
        Returns:
            成功添加的数量
        """
        count = 0
        for id, vector, metadata in entries:
            if self.add(id, vector, metadata):
                count += 1
        return count
    
    def get(self, id: str) -> Optional[VectorEntry]:
        """获取向量"""
        with self._lock:
            if id not in self._vectors:
                return None
            return VectorEntry(
                id=id,
                vector=self._vectors[id],
                metadata=self._metadata.get(id, {}),
            )
    
    def delete(self, id: str) -> bool:
        """删除向量"""
        with self._lock:
            if id in self._vectors:
                del self._vectors[id]
                if id in self._metadata:
                    del self._metadata[id]
                self._save()
                return True
            return False
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        向量检索
        
        Args:
            query_vector: 查询向量
            top_k: 返回数量
            filter_metadata: 元数据过滤
            
        Returns:
            [(id, score, metadata), ...]
        """
        with self._lock:
            if not self._vectors:
                return []
            
            query = np.array(query_vector)
            
            # 计算相似度/距离
            results = []
            for id, vector in self._vectors.items():
                # 元数据过滤
                if filter_metadata:
                    if not self._match_metadata(self._metadata.get(id, {}), filter_metadata):
                        continue
                
                vec = np.array(vector)
                score = self._compute_score(query, vec)
                results.append((id, score, self._metadata.get(id, {})))
            
            # 排序
            if self._metric == "cosine":
                results.sort(key=lambda x: x[1], reverse=True)  # 降序
            else:
                results.sort(key=lambda x: x[1])  # 升序（距离）
            
            return results[:top_k]
    
    def count(self) -> int:
        """返回向量数量"""
        with self._lock:
            return len(self._vectors)
    
    def clear(self) -> None:
        """清空所有向量"""
        with self._lock:
            self._vectors.clear()
            self._metadata.clear()
            self._save()
    
    def get_all_ids(self) -> List[str]:
        """获取所有 ID"""
        with self._lock:
            return list(self._vectors.keys())
    
    def _compute_score(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算相似度/距离"""
        if self._metric == "cosine":
            # 余弦相似度
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(vec1, vec2) / (norm1 * norm2))
        else:
            # 欧氏距离
            return float(np.linalg.norm(vec1 - vec2))
    
    def _match_metadata(
        self,
        entry_metadata: Dict[str, Any],
        filter_metadata: Dict[str, Any],
    ) -> bool:
        """检查元数据是否匹配"""
        for key, value in filter_metadata.items():
            if entry_metadata.get(key) != value:
                return False
        return True
    
    def _save(self) -> None:
        """持久化"""
        if not self._storage_path:
            return
        
        try:
            data = {
                "dimension": self._dimension,
                "metric": self._metric,
                "vectors": self._vectors,
                "metadata": self._metadata,
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[VectorStore] 保存失败: {e}")
    
    def _load(self) -> None:
        """加载"""
        try:
            path = Path(self._storage_path)
            if not path.exists():
                return
            
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._dimension = data.get("dimension", self._dimension)
            self._metric = data.get("metric", self._metric)
            self._vectors = data.get("vectors", {})
            self._metadata = data.get("metadata", {})
        except Exception as e:
            print(f"[VectorStore] 加载失败: {e}")


class HybridVectorStore(VectorStore):
    """
    混合向量存储 - 支持多向量场
    
    适用于同一文档有多个语义角度的场景。
    """
    
    def __init__(
        self,
        dimension: int = 384,
        storage_path: Optional[str] = None,
    ):
        super().__init__(dimension, storage_path)
        # 字段名 -> VectorStore
        self._field_stores: Dict[str, VectorStore] = {}
    
    def add_with_fields(
        self,
        id: str,
        fields: Dict[str, List[float]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        添加多字段向量
        
        Args:
            id: 唯一标识
            fields: {字段名: 向量}
            metadata: 元数据
        """
        with self._lock:
            for field_name, vector in fields.items():
                if field_name not in self._field_stores:
                    self._field_stores[field_name] = VectorStore(
                        dimension=len(vector),
                        storage_path=None,  # 暂不支持单独持久化
                    )
                self._field_stores[field_name].add(id, vector)
            
            # 主存储也保存一份
            # 取第一个字段的向量作为主向量
            main_vector = next(iter(fields.values()))
            return super().add(id, main_vector, metadata)
    
    def search_by_field(
        self,
        field: str,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """在指定字段检索"""
        with self._lock:
            store = self._field_stores.get(field)
            if not store:
                return []
            return store.search(query_vector, top_k)
    
    def search_hybrid(
        self,
        fields: Dict[str, List[float]],
        top_k: int = 5,
        weights: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        混合检索
        
        Args:
            fields: {字段名: 查询向量}
            top_k: 返回数量
            weights: 字段权重
            
        Returns:
            [(id, 综合分数, metadata), ...]
        """
        with self._lock:
            # 收集各字段检索结果
            all_results: Dict[str, List[float]] = {}
            
            for field, query_vector in fields.items():
                store = self._field_stores.get(field)
                if not store:
                    continue
                
                weight = (weights or {}).get(field, 1.0)
                results = store.search(query_vector, top_k=top_k * 2)
                
                for id, score, _ in results:
                    if id not in all_results:
                        all_results[id] = []
                    all_results[id].append(score * weight)
            
            # 合并分数
            merged = []
            for id, scores in all_results.items():
                avg_score = sum(scores) / len(scores)
                metadata = self._metadata.get(id, {})
                merged.append((id, avg_score, metadata))
            
            merged.sort(key=lambda x: x[1], reverse=True)
            return merged[:top_k]
