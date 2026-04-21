"""
RAG 检索模块 - 检索增强生成

特性：
- 统一的检索接口
- 支持多知识源
- 可配置的检索策略
- 重排序能力
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum


class RetrievalStrategy(Enum):
    """检索策略"""
    SIMPLE = "simple"           # 简单检索
    SEMANTIC = "semantic"       # 语义检索
    HYBRID = "hybrid"           # 混合检索
    MULTI_QUERY = "multi_query" # 多查询


@dataclass
class RetrievalQuery:
    """检索查询"""
    text: str
    top_k: int = 5
    min_similarity: float = 0.0
    filters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedDocument:
    """检索到的文档"""
    id: str
    content: str
    score: float
    rank: int
    source: str  # 知识来源标识
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGContext:
    """RAG 上下文"""
    query: str
    documents: List[RetrievedDocument]
    system_prompt: Optional[str] = None
    
    def build_prompt(
        self,
        user_prompt: str,
        include_source: bool = True,
    ) -> str:
        """
        构建 RAG 增强的 prompt
        
        Args:
            user_prompt: 用户原始问题
            include_source: 是否包含来源信息
            
        Returns:
            增强后的 prompt
        """
        if not self.documents:
            return user_prompt
        
        parts = []
        
        # 添加系统说明
        if self.system_prompt:
            parts.append(f"[系统提示]\n{self.system_prompt}\n")
        
        # 添加知识上下文
        parts.append("[相关知识]")
        for i, doc in enumerate(self.documents, 1):
            parts.append(f"\n--- 知识 #{i} (相关度: {doc.score:.2f}) ---")
            parts.append(doc.content)
            if include_source and doc.metadata:
                source = doc.metadata.get("source", "未知来源")
                parts.append(f"[来源: {source}]")
        
        # 添加用户问题
        parts.append(f"\n[用户问题]\n{user_prompt}")
        
        # 添加回答指导
        parts.append("\n请基于以上相关知识回答用户问题。")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "documents": [
                {
                    "id": d.id,
                    "content": d.content,
                    "score": d.score,
                    "rank": d.rank,
                    "source": d.source,
                    "metadata": d.metadata,
                }
                for d in self.documents
            ],
            "system_prompt": self.system_prompt,
        }


class RAGRetriever:
    """
    RAG 检索器
    
    使用示例：
        retriever = RAGRetriever()
        
        # 注册知识源
        retriever.register_source("docs", docs_memory)
        retriever.register_source("skills", skills_memory)
        
        # 检索
        context = retriever.retrieve(
            query="如何实现 Python 装饰器？",
            top_k=5,
        )
        
        # 构建 prompt
        prompt = context.build_prompt("装饰器有什么用途？")
    """
    
    def __init__(
        self,
        strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC,
        default_top_k: int = 5,
        rerank: bool = True,
    ):
        """
        初始化 RAG 检索器
        
        Args:
            strategy: 检索策略
            default_top_k: 默认返回数量
            rerank: 是否启用重排序
        """
        self._strategy = strategy
        self._default_top_k = default_top_k
        self._rerank = rerank
        self._sources: Dict[str, Any] = {}  # source_name -> memory
        
        # 嵌入函数（可自定义）
        self._embed_func: Optional[Callable[[str], List[float]]] = None
    
    def register_source(
        self,
        name: str,
        memory,
        priority: int = 1,
    ) -> None:
        """
        注册知识源
        
        Args:
            name: 知识源名称
            memory: 长期记忆实例
            priority: 优先级（越高越优先）
        """
        self._sources[name] = {
            "memory": memory,
            "priority": priority,
        }
    
    def unregister_source(self, name: str) -> bool:
        """取消注册知识源"""
        if name in self._sources:
            del self._sources[name]
            return True
        return False
    
    def set_embed_func(self, func: Callable[[str], List[float]]) -> None:
        """设置嵌入函数"""
        self._embed_func = func
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_similarity: float = 0.0,
        sources: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RAGContext:
        """
        执行检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            min_similarity: 最低相似度
            sources: 指定检索的知识源（None 则检索全部）
            filters: 元数据过滤器
            
        Returns:
            RAG 上下文
        """
        top_k = top_k or self._default_top_k
        
        # 按优先级排序知识源
        source_names = sources or list(self._sources.keys())
        sorted_sources = sorted(
            source_names,
            key=lambda s: self._sources.get(s, {}).get("priority", 0),
            reverse=True,
        )
        
        # 从各知识源检索
        all_results: List[RetrievedDocument] = []
        
        for source_name in sorted_sources:
            if source_name not in self._sources:
                continue
            
            source = self._sources[source_name]
            memory = source["memory"]
            
            # 调用记忆的检索方法
            try:
                if hasattr(memory, "retrieve"):
                    chunks = memory.retrieve(
                        query=query,
                        top_k=top_k,
                        min_similarity=min_similarity,
                    )
                    
                    for chunk in chunks:
                        # 兼容不同记忆模块的返回格式
                        if hasattr(chunk, "entry"):
                            entry = chunk.entry
                            content = entry.content
                            score = chunk.similarity
                        else:
                            content = chunk.content if hasattr(chunk, "content") else str(chunk)
                            score = chunk.score if hasattr(chunk, "score") else 0.0
                        
                        all_results.append(RetrievedDocument(
                            id=entry.id if hasattr(entry, "id") else f"{source_name}_{len(all_results)}",
                            content=content,
                            score=score,
                            rank=0,  # 稍后计算
                            source=source_name,
                            metadata=getattr(entry, "metadata", {}) if hasattr(entry, "metadata") else {},
                        ))
            except Exception as e:
                print(f"[RAGRetriever] 检索 {source_name} 失败: {e}")
        
        # 重排序
        if self._rerank and len(all_results) > 1:
            all_results = self._rerank_results(query, all_results)
        
        # 设置排名
        for i, doc in enumerate(all_results):
            doc.rank = i + 1
        
        # 截取 top_k
        all_results = all_results[:top_k]
        
        return RAGContext(
            query=query,
            documents=all_results,
        )
    
    def retrieve_as_text(
        self,
        query: str,
        top_k: Optional[int] = None,
        sources: Optional[List[str]] = None,
    ) -> str:
        """
        检索并直接返回文本（便捷方法）
        
        Returns:
            格式化的知识文本
        """
        context = self.retrieve(query, top_k, sources=sources)
        
        if not context.documents:
            return ""
        
        parts = ["[相关知识]"]
        for doc in context.documents:
            parts.append(f"\n{doc.content}")
        
        return "\n".join(parts)
    
    def _rerank_results(
        self,
        query: str,
        results: List[RetrievedDocument],
    ) -> List[RetrievedDocument]:
        """
        重排序检索结果
        
        简单实现：结合相关度、来源优先级、知识新鲜度
        """
        query_lower = query.lower()
        
        for doc in results:
            # 基础分数
            base_score = doc.score
            
            # 关键词匹配加成
            keyword_boost = 0.0
            query_words = set(query_lower.split())
            content_words = set(doc.content.lower().split())
            overlap = query_words & content_words
            if overlap:
                keyword_boost = len(overlap) / len(query_words) * 0.2
            
            # 来源优先级加成
            priority_boost = self._sources.get(doc.source, {}).get("priority", 0) * 0.05
            
            # 综合分数
            doc.score = base_score + keyword_boost + priority_boost
        
        # 重新排序
        return sorted(results, key=lambda d: d.score, reverse=True)
    
    def get_sources(self) -> List[str]:
        """获取已注册的知识源"""
        return list(self._sources.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "strategy": self._strategy.value,
            "sources": {},
            "total_entries": 0,
        }
        
        for name, source in self._sources.items():
            memory = source["memory"]
            count = memory.count() if hasattr(memory, "count") else 0
            stats["sources"][name] = {
                "priority": source["priority"],
                "entries": count,
            }
            stats["total_entries"] += count
        
        return stats
