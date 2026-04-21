"""
Neshama Core - 核心对话引擎
============================

最小可运行的 Agent 对话核心模块。

功能：
- 加载 Soul 配置
- 检索 Memory (RAG)
- 调用 LLM
- 生成回复
- 存储对话记忆

主要类：
- NeshamaEngine: 核心对话引擎
- ConversationManager: 对话管理器
"""

from .engine import NeshamaEngine, EngineConfig, ChatResponse
from .conversation import ConversationManager, Session, Message

__version__ = "1.0.0"

__all__ = [
    "NeshamaEngine",
    "EngineConfig", 
    "ChatResponse",
    "ConversationManager",
    "Session",
    "Message",
]
