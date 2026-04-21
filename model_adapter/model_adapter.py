"""
Neshama Model Adapter Layer - Main Adapter
模型接入层主适配器

统一封装不同模型的调用接口，支持多模型切换和负载均衡
"""

import asyncio
from typing import Dict, List, Optional, Any, Union, AsyncIterator
from dataclasses import dataclass, field

from .config import Config, get_config, ModelConfig
from .providers.base import (
    BaseProvider, 
    Message, 
    MessageRole, 
    ModelResponse, 
    StreamChunk
)
from .router import ModelRouter, RouterStrategy, get_router, reset_router


# Provider 工厂映射
PROVIDER_FACTORIES = {}


def _init_provider_factories():
    """初始化 Provider 工厂"""
    global PROVIDER_FACTORIES
    
    # 延迟导入避免循环依赖
    from .providers.dashscope import DashScopeProvider
    from .providers.volcengine import VolcEngineProvider
    from .providers.qianfan import QianFanProvider
    from .providers.minimax import MiniMaxProvider
    from .providers.zhipu import ZhipuProvider
    from .providers.openai import OpenAIProvider
    from .providers.anthropic import AnthropicProvider
    from .providers.gemini import GeminiProvider
    from .providers.xinghuo import XingHuoProvider
    from .providers.coding.cursor import CursorProvider
    from .providers.coding.copilot import CopilotProvider
    
    PROVIDER_FACTORIES = {
        "dashscope": lambda cfg, **kw: DashScopeProvider(cfg),
        "volcengine": lambda cfg, **kw: VolcEngineProvider(cfg),
        "qianfan": lambda cfg, **kw: QianFanProvider(cfg),
        "minimax": lambda cfg, **kw: MiniMaxProvider(cfg),
        "zhipu": lambda cfg, **kw: ZhipuProvider(cfg),
        "openai": lambda cfg, **kw: OpenAIProvider(cfg),
        "anthropic": lambda cfg, **kw: AnthropicProvider(cfg),
        "gemini": lambda cfg, **kw: GeminiProvider(cfg),
        "xinghuo": lambda cfg, **kw: XingHuoProvider(cfg),
        "cursor": lambda cfg, **kw: CursorProvider(cfg),
        "copilot": lambda cfg, **kw: CopilotProvider(cfg),
    }


class ModelAdapter:
    """
    模型适配器
    
    统一的模型调用接口，支持：
    - 多 Provider 统一管理
    - 模型路由与负载均衡
    - 配置热加载
    - 统一的响应格式
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        router: Optional[ModelRouter] = None
    ):
        """
        初始化模型适配器
        
        Args:
            config: 配置对象
            router: 路由器对象
        """
        _init_provider_factories()
        
        self.config = config or get_config()
        self.router = router or get_router()
        
        self._providers: Dict[str, BaseProvider] = {}
        self._default_model: str = self.config.default_model
        
        # 初始化 Providers
        self._init_providers()
    
    def _init_providers(self):
        """初始化所有 Providers"""
        # 获取所有提供商配置
        all_providers = {
            **self.config.providers,
            **self.config.coding_providers
        }
        
        for provider_name, provider_config in all_providers.items():
            if not provider_config.get("enabled", True):
                continue
            
            try:
                self._create_provider(provider_name, provider_config)
            except Exception as e:
                import logging
                logging.warning(f"Failed to create provider {provider_name}: {e}")
    
    def _create_provider(self, provider_name: str, provider_config: Dict):
        """创建 Provider 实例"""
        if provider_name not in PROVIDER_FACTORIES:
            import logging
            logging.warning(f"Unknown provider: {provider_name}")
            return
        
        api_key = provider_config.get("api_key", "")
        if not api_key:
            return
        
        from .providers.base import ProviderConfig
        
        config = ProviderConfig(
            name=provider_name,
            api_key=api_key,
            base_url=provider_config.get("base_url", ""),
            timeout=provider_config.get("timeout", 60),
            max_retries=provider_config.get("retry_times", 3)
        )
        
        factory = PROVIDER_FACTORIES[provider_name]
        provider = factory(config)
        
        self._providers[provider_name] = provider
        
        # 注册到路由
        for model_config in self.config.get_model_configs(provider_name):
            if model_config.enabled:
                self.router.register_provider(
                    provider=provider,
                    model=model_config.model_id,
                    priority=model_config.priority,
                    weight=model_config.weight
                )
    
    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """获取指定 Provider"""
        return self._providers.get(provider_name)
    
    def get_default_model(self) -> str:
        """获取默认模型"""
        return self._default_model
    
    def set_default_model(self, model: str):
        """设置默认模型"""
        self._default_model = model
    
    async def call(
        self,
        messages: Union[List[Message], List[Dict], str],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, AsyncIterator[StreamChunk]]:
        """
        调用模型 - 统一接口
        
        Args:
            messages: 消息列表或字符串
            model: 模型名称，默认使用配置的默认模型
            provider: 指定 Provider，不指定则使用路由
            stream: 是否流式响应
            **kwargs: 额外参数 (temperature, max_tokens, top_p等)
        
        Returns:
            ModelResponse 或 StreamChunk (流式)
        """
        model = model or self._default_model
        
        # 如果指定了 Provider，直接调用
        if provider:
            provider_instance = self._providers.get(provider)
            if not provider_instance:
                return ModelResponse(
                    content="",
                    model=model,
                    provider=provider,
                    error=f"Provider {provider} not found"
                )
            
            if stream:
                return provider_instance.call_stream(messages, model, **kwargs)
            return await provider_instance.call(messages, model, **kwargs)
        
        # 使用路由
        if stream:
            return self.router.call(messages, model, stream=True, **kwargs)
        return await self.router.call(messages, model, **kwargs)
    
    def call_sync(
        self,
        messages: Union[List[Message], List[Dict], str],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """
        同步调用模型
        
        Args:
            messages: 消息列表或字符串
            model: 模型名称
            provider: 指定 Provider
            **kwargs: 额外参数
        
        Returns:
            ModelResponse
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.call(messages, model, provider, **kwargs))
        finally:
            loop.close()
    
    async def call_stream(
        self,
        messages: Union[List[Message], List[Dict], str],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        流式调用模型
        
        Args:
            messages: 消息列表或字符串
            model: 模型名称
            provider: 指定 Provider
            **kwargs: 额外参数
        
        Yields:
            StreamChunk
        """
        async for chunk in self.call(messages, model, provider, stream=True, **kwargs):
            yield chunk
    
    async def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """
        简单的对话接口
        
        Args:
            prompt: 用户输入
            system: 系统提示
            model: 模型名称
            **kwargs: 额外参数
        
        Returns:
            ModelResponse
        """
        messages = []
        
        if system:
            messages.append(Message(role=MessageRole.SYSTEM, content=system))
        
        messages.append(Message(role=MessageRole.USER, content=prompt))
        
        return await self.call(messages, model, **kwargs)
    
    def chat_sync(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """
        同步对话接口
        
        Args:
            prompt: 用户输入
            system: 系统提示
            model: 模型名称
            **kwargs: 额外参数
        
        Returns:
            ModelResponse
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.chat(prompt, system, model, **kwargs))
        finally:
            loop.close()
    
    async def embed(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
        provider: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        获取文本嵌入向量
        
        Args:
            texts: 文本列表
            model: 嵌入模型
            provider: 指定 Provider
            **kwargs: 额外参数
        
        Returns:
            嵌入结果
        """
        if provider:
            provider_instance = self._providers.get(provider)
            if provider_instance and hasattr(provider_instance, "embed"):
                return await provider_instance.embed(texts, model, **kwargs)
        
        # 默认返回错误
        return {
            "error": "Embedding not supported by current provider",
            "model": model
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "default_model": self._default_model,
            "providers": {
                name: provider.get_stats()
                for name, provider in self._providers.items()
            },
            "router": self.router.get_stats()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        results = {}
        
        # Provider 健康检查
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except:
                results[name] = False
        
        # Router 健康检查
        results["router"] = await self.router.health_check()
        
        return results
    
    def reload_config(self):
        """重新加载配置"""
        self.config = get_config()
        self._default_model = self.config.default_model
        
        # 重建 Providers
        for provider in self._providers.values():
            provider.close()
        self._providers.clear()
        self.router.reset()
        
        self._init_providers()
    
    def close(self):
        """关闭所有资源"""
        for provider in self._providers.values():
            provider.close()
        self._providers.clear()


# 全局适配器实例
_adapter_instance: Optional[ModelAdapter] = None


def get_adapter() -> ModelAdapter:
    """获取全局适配器"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = ModelAdapter()
    return _adapter_instance


def reset_adapter():
    """重置全局适配器"""
    global _adapter_instance
    if _adapter_instance:
        _adapter_instance.close()
    _adapter_instance = None


# 便捷函数
def create_adapter(
    providers: Dict[str, Dict],
    default_model: str = "gpt-4o",
    router_strategy: RouterStrategy = RouterStrategy.PRIORITY
) -> ModelAdapter:
    """
    创建适配器
    
    Args:
        providers: Provider配置字典
        default_model: 默认模型
        router_strategy: 路由策略
    
    Returns:
        ModelAdapter
    """
    config = Config()
    config._config["providers"] = providers
    config._config["default_model"] = default_model
    
    router = ModelRouter(strategy=router_strategy)
    
    return ModelAdapter(config=config, router=router)


# 导出
__all__ = [
    "ModelAdapter",
    "get_adapter",
    "reset_adapter", 
    "create_adapter",
    "Message",
    "MessageRole",
    "ModelResponse",
    "StreamChunk",
    "RouterStrategy",
    "Config",
    "get_config",
    "BaseProvider",
]
