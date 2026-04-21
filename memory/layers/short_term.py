"""
短期记忆模块 - 滑动窗口实现

特性：
- 固定容量，自动清理最旧记录
- 支持对话轮次管理
- 可配置的遗忘策略
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import threading


@dataclass
class ConversationTurn:
    """单轮对话记录"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )


class ShortTermMemory:
    """
    短期记忆 - 滑动窗口实现
    
    使用示例：
        memory = ShortTermMemory(capacity=10)
        memory.add("user", "你好")
        memory.add("assistant", "你好！有什么可以帮助你的？")
        
        # 获取最近5轮对话
        recent = memory.get_recent(n=5)
        
        # 搜索历史
        results = memory.search("关于某个主题的对话")
    """
    
    def __init__(
        self,
        capacity: int = 20,
        auto_persist: bool = True,
        persist_path: Optional[str] = None,
    ):
        """
        初始化短期记忆
        
        Args:
            capacity: 滑动窗口容量，超过则自动清理旧记录
            auto_persist: 是否自动持久化
            persist_path: 持久化文件路径
        """
        self._capacity = capacity
        self._turns: List[ConversationTurn] = []
        self._auto_persist = auto_persist
        self._persist_path = persist_path
        self._lock = threading.RLock()
        
        if auto_persist and persist_path:
            self._load()
    
    def add(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加一轮对话记录
        
        Args:
            role: 角色 ("user" | "assistant" | "system")
            content: 对话内容
            metadata: 额外元数据
        """
        with self._lock:
            turn = ConversationTurn(
                role=role,
                content=content,
                metadata=metadata or {},
            )
            self._turns.append(turn)
            self._evict_if_needed()
            
            if self._auto_persist and self._persist_path:
                self._save()
    
    def add_turn(self, turn: ConversationTurn) -> None:
        """直接添加 ConversationTurn 对象"""
        with self._lock:
            self._turns.append(turn)
            self._evict_if_needed()
            
            if self._auto_persist and self._persist_path:
                self._save()
    
    def get_recent(self, n: Optional[int] = None) -> List[ConversationTurn]:
        """
        获取最近 N 轮对话
        
        Args:
            n: 返回数量，None 则返回全部
            
        Returns:
            最近 N 轮对话列表
        """
        with self._lock:
            if n is None:
                return list(self._turns)
            return list(self._turns[-n:])
    
    def get_context(self, last_n: int = 10, include_system: bool = True) -> str:
        """
        获取格式化后的对话上下文字符串
        
        Args:
            last_n: 最近 N 轮
            include_system: 是否包含系统消息
            
        Returns:
            格式化对话字符串
        """
        turns = self.get_recent(n=last_n)
        
        if not include_system:
            turns = [t for t in turns if t.role != "system"]
        
        context_parts = []
        for turn in turns:
            role_display = {
                "user": "User",
                "assistant": "Assistant", 
                "system": "System"
            }.get(turn.role, turn.role)
            context_parts.append(f"{role_display}: {turn.content}")
        
        return "\n".join(context_parts)
    
    def search(self, query: str, top_k: int = 5) -> List[ConversationTurn]:
        """
        简单关键词搜索（未来可升级为向量搜索）
        
        Args:
            query: 搜索关键词
            top_k: 返回数量
            
        Returns:
            匹配的对话记录
        """
        with self._lock:
            query_lower = query.lower()
            matched = [
                turn for turn in self._turns
                if query_lower in turn.content.lower()
            ]
            return matched[-top_k:]  # 返回最新的匹配结果
    
    def clear(self) -> None:
        """清空所有记忆"""
        with self._lock:
            self._turns.clear()
            if self._auto_persist and self._persist_path:
                self._save()
    
    def size(self) -> int:
        """返回当前记忆数量"""
        with self._lock:
            return len(self._turns)
    
    def _evict_if_needed(self) -> None:
        """超过容量时清理旧记录"""
        while len(self._turns) > self._capacity:
            self._turns.pop(0)
    
    def _save(self) -> None:
        """持久化到文件"""
        try:
            data = {
                "capacity": self._capacity,
                "turns": [t.to_dict() for t in self._turns],
            }
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ShortTermMemory] 持久化失败: {e}")
    
    def _load(self) -> None:
        """从文件加载"""
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._capacity = data.get("capacity", self._capacity)
                self._turns = [
                    ConversationTurn.from_dict(t) 
                    for t in data.get("turns", [])
                ]
        except FileNotFoundError:
            pass  # 首次运行，无历史数据
        except Exception as e:
            print(f"[ShortTermMemory] 加载失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        with self._lock:
            return {
                "capacity": self._capacity,
                "turns": [t.to_dict() for t in self._turns],
            }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], persist_path: Optional[str] = None) -> "ShortTermMemory":
        """从字典创建"""
        memory = cls(capacity=data.get("capacity", 20), persist_path=persist_path)
        memory._turns = [
            ConversationTurn.from_dict(t) 
            for t in data.get("turns", [])
        ]
        return memory
