"""
Neshama Memory - 主模块

三层记忆统一接口，整合短期、中期、长期记忆，
为 Agent 提供完整的记忆能力。
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import threading

from .layers import ShortTermMemory, MediumTermMemory, LongTermMemory
from .storage import FileStorage, VectorStore
from .retrieval.rag import RAGRetriever, RetrievalStrategy


@dataclass
class MemoryConfig:
    """记忆配置"""
    # 基础配置
    agent_id: str = "default"
    storage_path: str = "./memory_data"
    
    # 短期记忆配置
    short_term_capacity: int = 20
    short_term_persist: bool = True
    
    # 中期记忆配置
    medium_term_enabled: bool = True
    
    # 长期记忆配置
    long_term_enabled: bool = True
    embedding_dim: int = 384
    
    # RAG 配置
    rag_top_k: int = 5
    rag_strategy: RetrievalStrategy = RetrievalStrategy.SEMANTIC


@dataclass
class MemoryStats:
    """记忆统计"""
    short_term_count: int
    interaction_count: int
    long_term_count: int
    preferences_count: int
    habits_count: int


class Memory:
    """
    Neshama Memory - 统一记忆接口
    
    三层记忆架构：
    - 短期：滑动窗口对话记忆
    - 中期：用户画像、偏好、习惯
    - 长期：RAG 知识库
    
    使用示例：
        # 初始化
        memory = Memory(agent_id="my_agent")
        
        # 添加对话
        memory.add_turn("user", "你好")
        memory.add_turn("assistant", "你好！")
        
        # 获取短期记忆上下文
        context = memory.get_short_term_context()
        
        # 获取中期记忆摘要
        profile = memory.get_medium_term_summary()
        
        # RAG 检索
        rag_context = memory.retrieve("相关知识")
        
        # 获取完整上下文（用于 Agent）
        full_context = memory.get_context()
    """
    
    def __init__(
        self,
        agent_id: str = "default",
        config: Optional[MemoryConfig] = None,
    ):
        """
        初始化 Memory
        
        Args:
            agent_id: Agent 唯一标识
            config: 配置对象
        """
        self._config = config or MemoryConfig(agent_id=agent_id)
        self._agent_id = self._config.agent_id
        self._lock = threading.RLock()
        
        # 初始化存储层
        self._file_storage = FileStorage(
            base_path=self._config.storage_path,
        )
        
        # 初始化向量存储
        self._vector_store = VectorStore(
            dimension=self._config.embedding_dim,
            storage_path=f"{self._config.storage_path}/vectors.json",
        )
        
        # 初始化三层记忆
        self._init_short_term()
        self._init_medium_term()
        self._init_long_term()
        
        # 初始化 RAG 检索器
        self._init_rag()
    
    def _init_short_term(self) -> None:
        """初始化短期记忆"""
        persist_path = None
        if self._config.short_term_persist:
            persist_path = f"{self._config.storage_path}/short_term.json"
        
        self._short_term = ShortTermMemory(
            capacity=self._config.short_term_capacity,
            auto_persist=self._config.short_term_persist,
            persist_path=persist_path,
        )
    
    def _init_medium_term(self) -> None:
        """初始化中期记忆"""
        self._medium_term = MediumTermMemory(
            agent_id=self._agent_id,
            storage_path=f"{self._config.storage_path}/medium_term_{self._agent_id}.json",
            auto_save=True,
        ) if self._config.medium_term_enabled else None
    
    def _init_long_term(self) -> None:
        """初始化长期记忆"""
        self._long_term = LongTermMemory(
            agent_id=self._agent_id,
            storage_path=f"{self._config.storage_path}/long_term_{self._agent_id}.json",
            vector_store=self._vector_store,
        ) if self._config.long_term_enabled else None
    
    def _init_rag(self) -> None:
        """初始化 RAG 检索器"""
        self._rag = RAGRetriever(
            strategy=self._config.rag_strategy,
            default_top_k=self._config.rag_top_k,
        )
        
        # 注册长期记忆作为知识源
        if self._long_term:
            self._rag.register_source("knowledge", self._long_term, priority=2)
    
    # ========== 短期记忆操作 ==========
    
    def add_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加对话轮次
        
        Args:
            role: 角色 ("user" | "assistant" | "system")
            content: 对话内容
            metadata: 额外元数据
        """
        with self._lock:
            self._short_term.add(role, content, metadata)
            
            # 更新中期记忆交互计数
            if self._medium_term:
                self._medium_term.increment_interaction()
    
    def get_short_term_context(
        self,
        last_n: Optional[int] = None,
        include_system: bool = False,
    ) -> str:
        """
        获取短期记忆上下文
        
        Args:
            last_n: 最近 N 轮，None 则全部
            include_system: 是否包含系统消息
            
        Returns:
            格式化对话字符串
        """
        return self._short_term.get_context(last_n or 10, include_system)
    
    def search_short_term(self, query: str, top_k: int = 5) -> List[Any]:
        """搜索短期记忆"""
        return self._short_term.search(query, top_k)
    
    def clear_short_term(self) -> None:
        """清空短期记忆"""
        self._short_term.clear()
    
    # ========== 中期记忆操作 ==========
    
    def set_user_profile(
        self,
        name: Optional[str] = None,
        language: str = "zh-CN",
        interests: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        """
        设置用户画像
        
        Args:
            name: 用户名
            language: 语言
            interests: 兴趣列表
            **kwargs: 其他画像字段
        """
        if not self._medium_term:
            return
        
        from .layers.medium_term import UserProfile
        
        profile = UserProfile(
            name=name,
            language=language,
            interests=interests or [],
            **{k: v for k, v in kwargs.items() if k in [
                "timezone", "profession", "custom_fields"
            ]},
        )
        self._medium_term.set_profile(profile)
    
    def update_preference(
        self,
        key: str,
        value: Any,
        confidence: float = 1.0,
    ) -> None:
        """更新用户偏好"""
        if self._medium_term:
            self._medium_term.update_preference(key, value, confidence)
    
    def learn_preference(
        self,
        key: str,
        value: Any,
    ) -> None:
        """隐式学习偏好（从行为中推断）"""
        if self._medium_term:
            self._medium_term.learn_preference_implicit(key, value)
    
    def record_habit(
        self,
        pattern: str,
        context: str = "general",
    ) -> None:
        """记录用户习惯"""
        if self._medium_term:
            self._medium_term.record_habit(pattern, context=context)
    
    def get_medium_term_summary(self) -> str:
        """获取中期记忆摘要"""
        if self._medium_term:
            return self._medium_term.get_context_summary()
        return ""
    
    def get_preferences(self) -> Dict[str, Any]:
        """获取所有偏好"""
        if self._medium_term:
            return self._medium_term.get_all_preferences()
        return {}
    
    # ========== 长期记忆操作 ==========
    
    def add_knowledge(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        添加知识到长期记忆
        
        Args:
            content: 知识内容
            metadata: 元数据
            
        Returns:
            知识 ID
        """
        if self._long_term:
            return self._long_term.add_knowledge(content, metadata)
        return None
    
    def add_knowledge_batch(
        self,
        contents: List[str],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """批量添加知识"""
        if self._long_term:
            return self._long_term.add_knowledge_batch(contents, metadata_list)
        return []
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        sources: Optional[List[str]] = None,
    ):
        """
        RAG 检索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            sources: 指定知识源
            
        Returns:
            RAGContext
        """
        return self._rag.retrieve(
            query=query,
            top_k=top_k,
            sources=sources,
        )
    
    def build_rag_prompt(
        self,
        query: str,
        user_prompt: str,
        top_k: Optional[int] = None,
    ) -> str:
        """
        构建 RAG 增强的 prompt
        
        Args:
            query: 检索查询
            user_prompt: 用户原始问题
            top_k: 检索数量
            
        Returns:
            增强后的 prompt
        """
        context = self.retrieve(query, top_k)
        return context.build_prompt(user_prompt)
    
    # ========== 统一上下文 ==========
    
    def get_context(
        self,
        short_term_turns: int = 10,
        include_rag: bool = True,
        rag_query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取完整的记忆上下文
        
        返回结构：
        {
            "short_term": {...},
            "medium_term": {...},
            "long_term": {...},
        }
        
        Args:
            short_term_turns: 短期记忆轮数
            include_rag: 是否包含 RAG 结果
            rag_query: RAG 查询词（None 则使用最后一条用户消息）
        """
        with self._lock:
            # 短期记忆
            short_term = {
                "count": self._short_term.size(),
                "context": self._short_term.get_context(short_term_turns),
            }
            
            # 中期记忆
            medium_term = {}
            if self._medium_term:
                medium_term = {
                    "profile": (
                        self._medium_term.get_profile().to_dict()
                        if self._medium_term.get_profile()
                        else None
                    ),
                    "preferences": self._medium_term.get_all_preferences(),
                    "habits": [
                        h.to_dict() for h in self._medium_term.get_habits()
                    ],
                    "interaction_count": self._medium_term.get_interaction_count(),
                    "summary": self._medium_term.get_context_summary(),
                }
            
            # RAG 结果
            long_term = {}
            if include_rag and self._long_term:
                # 确定 RAG 查询
                query = rag_query
                if not query:
                    # 使用最后一条用户消息
                    recent = self._short_term.get_recent(1)
                    if recent and recent[-1].role == "user":
                        query = recent[-1].content
                
                if query:
                    rag_context = self.retrieve(query)
                    long_term = {
                        "rag_context": rag_context.to_dict(),
                        "prompt": rag_context.build_prompt(query),
                    }
            
            return {
                "short_term": short_term,
                "medium_term": medium_term,
                "long_term": long_term,
            }
    
    def get_prompt_context(self) -> str:
        """
        获取适合注入 Agent Prompt 的上下文字符串
        
        Returns:
            格式化的上下文字符串
        """
        parts = []
        
        # 中期记忆摘要
        if self._medium_term:
            summary = self._medium_term.get_context_summary()
            if summary:
                parts.append("[用户信息]")
                parts.append(summary)
                parts.append("")
        
        # 短期记忆（最近 5 轮）
        short_context = self._short_term.get_context(5, include_system=False)
        if short_context:
            parts.append("[最近对话]")
            parts.append(short_context)
            parts.append("")
        
        return "\n".join(parts)
    
    # ========== 统计与管理 ==========
    
    def get_stats(self) -> MemoryStats:
        """获取记忆统计"""
        return MemoryStats(
            short_term_count=self._short_term.size(),
            interaction_count=(
                self._medium_term.get_interaction_count()
                if self._medium_term else 0
            ),
            long_term_count=(
                self._long_term.size() if hasattr(self._long_term, 'size') else 0
                if self._long_term else 0
            ),
            preferences_count=len(
                self._medium_term.get_all_preferences()
                if self._medium_term else {}
            ),
            habits_count=len(
                self._medium_term.get_habits()
                if self._medium_term else []
            ),
        )
    
    def reset(self, confirm: bool = False) -> None:
        """
        重置所有记忆（危险操作）
        
        Args:
            confirm: 必须为 True 才执行
        """
        if not confirm:
            raise ValueError("必须设置 confirm=True 才能重置记忆")
        
        with self._lock:
            self._short_term.clear()
            if self._medium_term:
                self._medium_term._preferences.clear()
                self._medium_term._habits.clear()
            if self._long_term:
                self._long_term.clear()
    
    @property
    def short_term(self) -> ShortTermMemory:
        """获取短期记忆实例（高级用法）"""
        return self._short_term
    
    @property
    def medium_term(self) -> Optional[MediumTermMemory]:
        """获取中期记忆实例（高级用法）"""
        return self._medium_term
    
    @property
    def long_term(self) -> Optional[LongTermMemory]:
        """获取长期记忆实例（高级用法）"""
        return self._long_term
    
    @property
    def rag(self) -> RAGRetriever:
        """获取 RAG 检索器（高级用法）"""
        return self._rag
