"""
长期记忆模块 - RAG 检索与知识库

特性：
- 向量嵌入存储
- RAG 检索能力
- 知识库管理
- 支持多种嵌入模型
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import json
import hashlib
import threading


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    relevance_score: float = 1.0  # 知识的重要性/质量评分
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "relevance_score": self.relevance_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeEntry":
        return cls(
            id=data["id"],
            content=data["content"],
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            access_count=data.get("access_count", 0),
            relevance_score=data.get("relevance_score", 1.0),
        )


@dataclass
class RetrievedChunk:
    """检索结果片段"""
    entry: KnowledgeEntry
    similarity: float
    rank: int


class LongTermMemory:
    """
    长期记忆 - RAG 检索与知识库
    
    使用示例：
        # 初始化（使用默认嵌入函数）
        memory = LongTermMemory(agent_id="agent_001")
        
        # 添加知识
        memory.add_knowledge(
            content="Python 是一种高级编程语言...",
            metadata={"source": "文档", "category": "编程"}
        )
        
        # RAG 检索
        results = memory.retrieve("Python 有什么特点？", top_k=5)
        
        # 构建 RAG 上下文
        context = memory.build_rag_context("Python 有什么特点？")
    """
    
    def __init__(
        self,
        agent_id: str,
        storage_path: Optional[str] = None,
        embed_func: Optional[Callable[[str], List[float]]] = None,
        vector_store = None,  # 向量存储实例
        auto_save: bool = True,
        embedding_dim: int = 384,  # 默认嵌入维度
    ):
        """
        初始化长期记忆
        
        Args:
            agent_id: Agent 唯一标识
            storage_path: 存储路径
            embed_func: 嵌入函数，接受文本返回向量列表
            vector_store: 向量存储实例（如不使用内置）
            auto_save: 是否自动保存
            embedding_dim: 嵌入向量维度
        """
        self._agent_id = agent_id
        self._storage_path = storage_path
        self._auto_save = auto_save
        self._lock = threading.RLock()
        
        # 嵌入函数（可自定义）
        self._embed_func = embed_func or self._default_embed
        
        # 向量存储（内置简单实现）
        self._vector_store = vector_store
        self._embedding_dim = embedding_dim
        
        # 知识库
        self._knowledge: Dict[str, KnowledgeEntry] = {}
        self._created_at = datetime.now().isoformat()
        
        # 加载已有数据
        if storage_path:
            self._load()
    
    def add_knowledge(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        generate_embedding: bool = True,
        id: Optional[str] = None,
    ) -> str:
        """
        添加知识条目
        
        Args:
            content: 知识内容
            metadata: 元数据
            generate_embedding: 是否生成嵌入向量
            id: 指定 ID，不指定则自动生成
            
        Returns:
            知识条目 ID
        """
        with self._lock:
            entry_id = id or self._generate_id(content)
            embedding = None
            
            if generate_embedding and self._embed_func:
                embedding = self._embed_func(content)
            
            entry = KnowledgeEntry(
                id=entry_id,
                content=content,
                embedding=embedding,
                metadata=metadata or {},
            )
            
            self._knowledge[entry_id] = entry
            
            # 添加到向量存储
            if embedding and self._vector_store:
                self._vector_store.add(entry_id, embedding)
            
            self._mark_updated()
            self._save()
            
            return entry_id
    
    def add_knowledge_batch(
        self,
        contents: List[str],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        批量添加知识
        
        Args:
            contents: 知识内容列表
            metadata_list: 元数据列表
            
        Returns:
            知识条目 ID 列表
        """
        ids = []
        for i, content in enumerate(contents):
            metadata = (
                metadata_list[i] if metadata_list and i < len(metadata_list)
                else {}
            )
            entry_id = self.add_knowledge(content, metadata)
            ids.append(entry_id)
        return ids
    
    def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """获取指定知识条目"""
        with self._lock:
            entry = self._knowledge.get(entry_id)
            if entry:
                entry.access_count += 1
            return entry
    
    def update_knowledge(
        self,
        entry_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新知识条目"""
        with self._lock:
            entry = self._knowledge.get(entry_id)
            if not entry:
                return False
            
            if content is not None:
                entry.content = content
                if self._embed_func:
                    entry.embedding = self._embed_func(content)
            
            if metadata is not None:
                entry.metadata.update(metadata)
            
            entry.updated_at = datetime.now().isoformat()
            self._mark_updated()
            self._save()
            return True
    
    def delete_knowledge(self, entry_id: str) -> bool:
        """删除知识条目"""
        with self._lock:
            if entry_id not in self._knowledge:
                return False
            
            del self._knowledge[entry_id]
            
            if self._vector_store:
                self._vector_store.delete(entry_id)
            
            self._mark_updated()
            self._save()
            return True
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        检索相关知识
        
        Args:
            query: 查询文本
            top_k: 返回数量
            min_similarity: 最低相似度阈值
            filter_metadata: 元数据过滤条件
            
        Returns:
            检索结果列表
        """
        with self._lock:
            query_embedding = self._embed_func(query)
            
            # 计算与所有条目的相似度
            candidates = []
            for entry in self._knowledge.values():
                # 元数据过滤
                if filter_metadata:
                    if not self._match_metadata(entry.metadata, filter_metadata):
                        continue
                
                if entry.embedding:
                    similarity = self._cosine_similarity(query_embedding, entry.embedding)
                else:
                    # 无嵌入时使用关键词匹配
                    similarity = self._keyword_similarity(query, entry.content)
                
                if similarity >= min_similarity:
                    candidates.append((entry, similarity))
            
            # 排序并取 Top K
            candidates.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for rank, (entry, similarity) in enumerate(candidates[:top_k]):
                results.append(RetrievedChunk(
                    entry=entry,
                    similarity=similarity,
                    rank=rank + 1,
                ))
            
            return results
    
    def build_rag_context(
        self,
        query: str,
        top_k: int = 5,
        include_metadata: bool = False,
    ) -> str:
        """
        构建 RAG 上下文字符串
        
        Args:
            query: 查询文本
            top_k: 检索数量
            include_metadata: 是否包含元数据
            
        Returns:
            格式化的 RAG 上下文
        """
        results = self.retrieve(query, top_k=top_k)
        
        if not results:
            return ""
        
        parts = ["[相关知识]", ""]
        
        for chunk in results:
            parts.append(f"--- 知识 #{chunk.rank} (相似度: {chunk.similarity:.2f}) ---")
            parts.append(chunk.entry.content)
            
            if include_metadata and chunk.entry.metadata:
                meta_str = ", ".join(
                    f"{k}={v}" for k, v in chunk.entry.metadata.items()
                )
                parts.append(f"[元数据: {meta_str}]")
            
            parts.append("")
        
        return "\n".join(parts)
    
    def search_by_metadata(
        self,
        metadata: Dict[str, Any],
    ) -> List[KnowledgeEntry]:
        """根据元数据搜索知识"""
        with self._lock:
            return [
                entry for entry in self._knowledge.values()
                if self._match_metadata(entry.metadata, metadata)
            ]
    
    def get_all_knowledge(
        self,
        limit: Optional[int] = None,
    ) -> List[KnowledgeEntry]:
        """获取所有知识条目"""
        with self._lock:
            entries = list(self._knowledge.values())
            if limit:
                entries = entries[:limit]
            return entries
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_entries": len(self._knowledge),
                "created_at": self._created_at,
                "categories": self._count_categories(),
            }
    
    # ========== 内部方法 ==========
    
    def _default_embed(self, text: str) -> List[float]:
        """
        默认嵌入函数（简单 TF-IDF 风格）
        实际使用时建议替换为 OpenAI/Cohere 等专业嵌入服务
        """
        words = text.lower().split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 简化为固定大小的向量（用于演示）
        vector = []
        for i in range(min(self._embedding_dim, len(words) * 10)):
            idx = i % len(words)
            vector.append(float(word_freq.get(words[idx], 0)) / max(len(words), 1))
        
        # 补齐或截断到固定维度
        while len(vector) < self._embedding_dim:
            vector.append(0.0)
        vector = vector[:self._embedding_dim]
        
        # L2 归一化
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _keyword_similarity(self, query: str, content: str) -> float:
        """关键词相似度（备选方案）"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words & content_words
        return len(intersection) / len(query_words)
    
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
    
    def _generate_id(self, content: str) -> str:
        """生成唯一 ID"""
        hash_input = f"{content[:100]}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    def _count_categories(self) -> Dict[str, int]:
        """统计类别分布"""
        categories = {}
        for entry in self._knowledge.values():
            cat = entry.metadata.get("category", "uncategorized")
            categories[cat] = categories.get(cat, 0) + 1
        return categories
    
    def _mark_updated(self) -> None:
        """标记更新时间"""
        pass
    
    def _save(self) -> None:
        """保存到文件"""
        if not self._auto_save or not self._storage_path:
            return
        
        try:
            data = {
                "agent_id": self._agent_id,
                "knowledge": {k: v.to_dict() for k, v in self._knowledge.items()},
                "created_at": self._created_at,
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[LongTermMemory] 保存失败: {e}")
    
    def _load(self) -> None:
        """从文件加载"""
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._knowledge = {
                    k: KnowledgeEntry.from_dict(v)
                    for k, v in data.get("knowledge", {}).items()
                }
                self._created_at = data.get("created_at", datetime.now().isoformat())
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[LongTermMemory] 加载失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        with self._lock:
            return {
                "agent_id": self._agent_id,
                "knowledge": {k: v.to_dict() for k, v in self._knowledge.items()},
                "created_at": self._created_at,
            }
