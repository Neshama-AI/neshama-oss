# Soul层 - Creativity子模块
"""
创造力系统模块

包含：
- inspiration.py - 灵感触发
- style.py - 风格养成
"""

from .inspiration import (
    InspirationEngine,
    Inspiration,
    InspirationTrigger,
    AssociationType,
    inspiration_engine,
    trigger_inspiration,
    get_inspiration_suggestions
)

from .style import (
    StyleLearner,
    StyleProfile,
    StylePreference,
    StyleDimension,
    style_learner,
    learn_generation,
    apply_style,
    get_current_style
)

__all__ = [
    # Inspiration
    "InspirationEngine",
    "Inspiration",
    "InspirationTrigger",
    "AssociationType",
    "inspiration_engine",
    "trigger_inspiration",
    "get_inspiration_suggestions",
    
    # Style
    "StyleLearner",
    "StyleProfile",
    "StylePreference",
    "StyleDimension",
    "style_learner",
    "learn_generation",
    "apply_style",
    "get_current_style"
]
