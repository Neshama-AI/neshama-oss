"""
Neshama Core - 对话管理器
==========================

管理多轮对话和会话状态。

功能：
- Session 会话管理
- 多轮对话上下文
- 历史记录维护
- 会话超时处理
"""

import logging
import threading
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """对话消息"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class Session:
    """
    会话对象
    
    管理单个对话会话的状态和历史。
    """
    id: str = ""  # 空字符串会在 __post_init__ 中自动生成
    user_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 配置
    max_history: int = 50  # 最大历史消息数
    timeout_minutes: int = 30  # 会话超时时间
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        添加消息到会话
        
        Args:
            role: 消息角色 ("user" | "assistant")
            content: 消息内容
            metadata: 额外元数据
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # 裁剪过长历史
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]
        
        logger.debug(f"Session {self.id}: Added {role} message")
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取对话历史
        
        Args:
            limit: 限制返回的消息数量（最近N条）
            
        Returns:
            消息列表
        """
        history = [msg.to_dict() for msg in self.messages]
        
        # 排除 system 消息（它们在构建 prompt 时单独处理）
        history = [m for m in history if m["role"] != "system"]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_context(self, include_recent: int = 10) -> str:
        """
        获取对话上下文文本
        
        Args:
            include_recent: 包含最近多少条消息
            
        Returns:
            格式化的对话上下文
        """
        recent = self.messages[-include_recent:] if include_recent else self.messages
        
        parts = []
        for msg in recent:
            if msg.role == "user":
                parts.append(f"用户: {msg.content}")
            elif msg.role == "assistant":
                parts.append(f"助手: {msg.content}")
        
        return "\n".join(parts)
    
    def is_expired(self) -> bool:
        """检查会话是否已超时"""
        elapsed = datetime.now() - self.updated_at
        return elapsed > timedelta(minutes=self.timeout_minutes)
    
    def touch(self):
        """更新会话时间戳"""
        self.updated_at = datetime.now()
    
    def clear_history(self):
        """清空对话历史"""
        self.messages = []
        self.updated_at = datetime.now()
        logger.info(f"Session {self.id}: History cleared")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": len(self.messages),
            "metadata": self.metadata
        }
    
    def __repr__(self) -> str:
        return f"Session(id={self.id[:8]}..., user={self.user_id}, messages={len(self.messages)})"


class ConversationManager:
    """
    对话管理器
    
    管理多个会话，支持：
    - 会话创建/获取/删除
    - 多用户会话隔离
    - 会话过期清理
    - 并发安全
    """
    
    def __init__(
        self,
        engine_id: str = "default",
        max_sessions: int = 1000,
        session_timeout_minutes: int = 30,
        auto_cleanup: bool = True,
        cleanup_interval_minutes: int = 5
    ):
        """
        初始化对话管理器
        
        Args:
            engine_id: 引擎标识
            max_sessions: 最大会话数
            session_timeout_minutes: 会话超时时间
            auto_cleanup: 是否自动清理过期会话
            cleanup_interval_minutes: 清理间隔
        """
        self.engine_id = engine_id
        self.max_sessions = max_sessions
        self.session_timeout_minutes = session_timeout_minutes
        
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._lock = threading.RLock()
        
        # 自动清理线程
        self._auto_cleanup = auto_cleanup
        self._cleanup_interval = cleanup_interval_minutes * 60
        self._last_cleanup = time.time()
        
        logger.info(f"ConversationManager initialized (engine={engine_id})")
    
    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Session:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            metadata: 会话元数据
            session_id: 指定会话ID（可选）
            
        Returns:
            新建的 Session 对象
        """
        with self._lock:
            # 检查会话数限制
            if len(self._sessions) >= self.max_sessions:
                self._cleanup_expired()
                if len(self._sessions) >= self.max_sessions:
                    logger.warning("Max sessions reached, removing oldest")
                    self._remove_oldest_session()
            
            # 创建会话
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            session = Session(
                id=session_id,
                user_id=user_id,
                metadata=metadata or {},
                timeout_minutes=self.session_timeout_minutes
            )
            
            self._sessions[session_id] = session
            
            # 关联用户
            if user_id:
                if user_id not in self._user_sessions:
                    self._user_sessions[user_id] = []
                self._user_sessions[user_id].append(session_id)
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Session 对象或 None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session:
                # 检查过期
                if session.is_expired():
                    logger.info(f"Session {session_id} expired")
                    self.delete_session(session_id)
                    return None
                
                session.touch()
                return session
            
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功删除
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
            
            if session and session.user_id:
                user_id = session.user_id
                if user_id in self._user_sessions:
                    self._user_sessions[user_id] = [
                        sid for sid in self._user_sessions[user_id]
                        if sid != session_id
                    ]
                    if not self._user_sessions[user_id]:
                        del self._user_sessions[user_id]
            
            if session:
                logger.info(f"Deleted session {session_id}")
                return True
            return False
    
    def list_sessions(
        self,
        user_id: Optional[str] = None,
        include_expired: bool = False
    ) -> List[Session]:
        """
        列出会话
        
        Args:
            user_id: 过滤特定用户
            include_expired: 是否包含已过期的会话
            
        Returns:
            Session 列表
        """
        with self._lock:
            if user_id:
                session_ids = self._user_sessions.get(user_id, [])
                sessions = [self._sessions[sid] for sid in session_ids if sid in self._sessions]
            else:
                sessions = list(self._sessions.values())
            
            if not include_expired:
                sessions = [s for s in sessions if not s.is_expired()]
            
            return sessions
    
    def clear_all_sessions(self):
        """清空所有会话"""
        with self._lock:
            self._sessions.clear()
            self._user_sessions.clear()
            logger.info("All sessions cleared")
    
    @property
    def sessions(self) -> Dict[str, Session]:
        """获取所有会话（只读）"""
        return dict(self._sessions)
    
    @property
    def session_count(self) -> int:
        """会话数量"""
        return len(self._sessions)
    
    def _cleanup_expired(self):
        """清理过期会话"""
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.is_expired()
        ]
        
        for sid in expired_ids:
            self.delete_session(sid)
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
    
    def _remove_oldest_session(self):
        """删除最老的会话"""
        if not self._sessions:
            return
        
        oldest = min(
            self._sessions.values(),
            key=lambda s: s.updated_at
        )
        self.delete_session(oldest.id)
    
    def auto_cleanup_if_needed(self):
        """必要时执行自动清理"""
        if not self._auto_cleanup:
            return
        
        now = time.time()
        if now - self._last_cleanup >= self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "user_count": len(self._user_sessions),
                "oldest_session": min(
                    (s.created_at for s in self._sessions.values()),
                    default=None
                ),
                "active_sessions": sum(
                    1 for s in self._sessions.values() if not s.is_expired()
                )
            }
    
    def __repr__(self) -> str:
        return f"ConversationManager(sessions={self.session_count})"


# ============================================================
# 便捷函数
# ============================================================

def create_session_message(role: str, content: str) -> Message:
    """创建消息的便捷函数"""
    return Message(role=role, content=content)


def format_conversation_history(
    messages: List[Message],
    max_length: Optional[int] = None
) -> str:
    """
    格式化对话历史为文本
    
    Args:
        messages: 消息列表
        max_length: 最大长度
        
    Returns:
        格式化的文本
    """
    parts = []
    for msg in messages:
        if msg.role == "user":
            parts.append(f"👤 用户: {msg.content}")
        elif msg.role == "assistant":
            parts.append(f"🤖 助手: {msg.content}")
        elif msg.role == "system":
            parts.append(f"⚙️ 系统: {msg.content}")
    
    text = "\n\n".join(parts)
    
    if max_length and len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("Conversation Manager Demo")
    print("=" * 50)
    
    # 创建管理器
    manager = ConversationManager(engine_id="demo")
    
    # 创建会话
    session1 = manager.create_session(user_id="user1")
    print(f"\n创建会话: {session1.id}")
    
    # 添加消息
    session1.add_message("user", "你好")
    session1.add_message("assistant", "你好！有什么可以帮助你的吗？")
    session1.add_message("user", "今天天气怎么样？")
    session1.add_message("assistant", "今天天气晴朗，温度适宜。")
    
    # 获取历史
    print("\n对话历史:")
    for msg in session1.get_history():
        print(f"  [{msg['role']}] {msg['content']}")
    
    # 获取上下文
    print("\n最近上下文:")
    print(session1.get_context(include_recent=2))
    
    # 列出用户会话
    sessions = manager.list_sessions(user_id="user1")
    print(f"\n用户 'user1' 的会话数: {len(sessions)}")
    
    # 统计信息
    print("\n统计信息:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 清理会话
    manager.delete_session(session1.id)
    print(f"\n删除会话后，剩余会话数: {manager.session_count}")
    
    print("\n" + "=" * 50)
    print("Demo Complete!")
    print("=" * 50)
