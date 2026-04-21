# Soul层 - Learning子模块
"""
学习系统模块

包含：
- knowledge.py - 知识管理
- forgetting.py - 遗忘机制
"""

from .knowledge import (
    KnowledgeGraph,
    KnowledgeNode,
    KnowledgeConnection,
    KnowledgeType,
    knowledge_graph,
    add_knowledge,
    retrieve_knowledge
)

from .forgetting import (
    ForgettingMechanism,
    MemoryItem,
    ForgettingConfig,
    ForgettingCurve,
    forgetting_mechanism,
    add_memory,
    access_memory,
    process_forgetting,
    get_memory_stats
)

__all__ = [
    # Knowledge
    "KnowledgeGraph",
    "KnowledgeNode",
    "KnowledgeConnection",
    "KnowledgeType",
    "knowledge_graph",
    "add_knowledge",
    "retrieve_knowledge",
    
    # Forgetting
    "ForgettingMechanism",
    "MemoryItem",
    "ForgettingConfig",
    "ForgettingCurve",
    "forgetting_mechanism",
    "add_memory",
    "access_memory",
    "process_forgetting",
    "get_memory_stats"
]
