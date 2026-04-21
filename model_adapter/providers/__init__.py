"""
Neshama Model Adapter - Providers
模型提供商模块
"""

from .base import (
    BaseProvider,
    ProviderConfig,
    Message,
    MessageRole,
    ModelResponse,
    StreamChunk
)

from .dashscope import DashScopeProvider
from .volcengine import VolcEngineProvider
from .qianfan import QianFanProvider
from .minimax import MiniMaxProvider
from .zhipu import ZhipuProvider

# 导入其他 Provider
try:
    from .openai import OpenAIProvider
except ImportError:
    pass

try:
    from .anthropic import AnthropicProvider
except ImportError:
    pass

try:
    from .gemini import GeminiProvider
except ImportError:
    pass

try:
    from .xinghuo import XingHuoProvider
except ImportError:
    pass

__all__ = [
    # Base
    "BaseProvider",
    "ProviderConfig",
    "Message",
    "MessageRole",
    "ModelResponse",
    "StreamChunk",
    
    # Providers - Phase 2 完善
    "DashScopeProvider",
    "VolcEngineProvider",
    "QianFanProvider",
    "MiniMaxProvider",
    "ZhipuProvider",
    
    # 其他 Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "XingHuoProvider",
]
