"""
Neshama Memory Layer
====================
开源 Agent 记忆框架 - Soul（灵魂）+ Memory（记忆）+ 关系

三层记忆架构：
- Short-term: 滑动窗口，保留最近 N 轮对话
- Medium-term: 用户画像、偏好、习惯
- Long-term: RAG 检索，知识库，技能沉淀
"""

__version__ = "0.1.0"
__author__ = "Neshama Community"

from .memory import Memory, MemoryConfig, MemoryStats

__all__ = ["Memory", "MemoryConfig", "MemoryStats"]
