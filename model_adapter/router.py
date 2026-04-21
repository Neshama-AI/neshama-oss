"""
Neshama Model Adapter Layer - Router
模型路由与负载均衡

支持多种路由策略：优先级、加权轮询、故障转移
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from .providers.base import BaseProvider, ModelResponse, StreamChunk, Message


class RouterStrategy(Enum):
    """路由策略"""
    PRIORITY = "priority"       # 按优先级
    ROUND_ROBIN = "round_robin" # 轮询
    WEIGHTED = "weighted"       # 加权轮询
    FAILOVER = "failover"       # 故障转移
    RANDOM = "random"           # 随机


@dataclass
class ProviderEndpoint:
    """Provider端点"""
    provider: BaseProvider
    model: str
    priority: int = 100
    weight: int = 1
    enabled: bool = True
    consecutive_failures: int = 0
    last_failure_time: float = 0
    request_count: int = 0
    
    @property
    def health_score(self) -> float:
        """计算健康分数"""
        base_score = self.provider.health_score
        # 连续失败惩罚
        failure_penalty = min(0.5, self.consecutive_failures * 0.15)
        return max(0, base_score - failure_penalty)
    
    @property
    def is_available(self) -> bool:
        """是否可用"""
        if not self.enabled:
            return False
        # 冷却期检查
        if self.consecutive_failures >= 3:
            if time.time() - self.last_failure_time < 60:
                return False
        return self.health_score > 0.3


class ModelRouter:
    """模型路由器"""
    
    def __init__(
        self,
        strategy: RouterStrategy = RouterStrategy.PRIORITY,
        failover_enabled: bool = True,
        max_consecutive_failures: int = 3
    ):
        self.strategy = strategy
        self.failover_enabled = failover_enabled
        self.max_consecutive_failures = max_consecutive_failures
        
        self._endpoints: Dict[str, List[ProviderEndpoint]] = {}  # model_name -> endpoints
        self._round_robin_counters: Dict[str, int] = {}  # model_name -> counter
        self._lock = asyncio.Lock()
    
    def register_provider(
        self,
        provider: BaseProvider,
        model: str,
        priority: int = 100,
        weight: int = 1
    ):
        """
        注册 Provider
        
        Args:
            provider: Provider实例
            model: 模型名称
            priority: 优先级（数字越小优先级越高）
            weight: 权重（用于加权轮询）
        """
        endpoint = ProviderEndpoint(
            provider=provider,
            model=model,
            priority=priority,
            weight=weight
        )
        
        if model not in self._endpoints:
            self._endpoints[model] = []
            self._round_robin_counters[model] = 0
        
        # 检查是否已存在
        for i, ep in enumerate(self._endpoints[model]):
            if ep.provider.provider_name == provider.provider_name:
                # 更新现有endpoint
                self._endpoints[model][i] = endpoint
                return
        
        self._endpoints[model].append(endpoint)
    
    def unregister_provider(self, model: str, provider_name: str):
        """取消注册 Provider"""
        if model in self._endpoints:
            self._endpoints[model] = [
                ep for ep in self._endpoints[model]
                if ep.provider.provider_name != provider_name
            ]
    
    def get_endpoints(self, model: str) -> List[ProviderEndpoint]:
        """获取可用的端点列表"""
        if model not in self._endpoints:
            return []
        return [ep for ep in self._endpoints[model] if ep.is_available]
    
    async def _select_endpoint(self, model: str) -> Optional[ProviderEndpoint]:
        """选择最佳端点"""
        endpoints = self.get_endpoints(model)
        if not endpoints:
            return None
        
        if self.strategy == RouterStrategy.PRIORITY:
            return min(endpoints, key=lambda x: x.priority)
        
        elif self.strategy == RouterStrategy.ROUND_ROBIN:
            async with self._lock:
                counter = self._round_robin_counters.get(model, 0)
                index = counter % len(endpoints)
                self._round_robin_counters[model] = counter + 1
            return endpoints[index]
        
        elif self.strategy == RouterStrategy.WEIGHTED:
            total_weight = sum(ep.weight for ep in endpoints)
            if total_weight == 0:
                return random.choice(endpoints)
            rand = random.uniform(0, total_weight)
            cumulative = 0
            for ep in endpoints:
                cumulative += ep.weight
                if rand <= cumulative:
                    return ep
            return endpoints[-1]
        
        elif self.strategy == RouterStrategy.RANDOM:
            return random.choice(endpoints)
        
        else:
            return endpoints[0]
    
    async def _call_single(
        self,
        messages: Any,
        model: str,
        **kwargs
    ) -> ModelResponse:
        """
        单次调用 (非流式)
        """
        tried_endpoints = []
        
        while True:
            endpoint = await self._select_endpoint(model)
            
            if endpoint is None:
                return ModelResponse(
                    content="",
                    model=model,
                    provider="router",
                    error="No available endpoints"
                )
            
            # 避免重复尝试
            if endpoint in tried_endpoints:
                break
            
            tried_endpoints.append(endpoint)
            
            try:
                response = await endpoint.provider.call(messages, model, **kwargs)
                
                if response.error:
                    raise Exception(response.error)
                
                # 记录成功
                endpoint.consecutive_failures = 0
                endpoint.request_count += 1
                return response
                    
            except Exception as e:
                endpoint.consecutive_failures += 1
                endpoint.last_failure_time = time.time()
                
                # 如果启用了故障转移且还有可用的端点，继续尝试
                if self.failover_enabled and len(tried_endpoints) < len(self.get_endpoints(model)):
                    continue
                
                return ModelResponse(
                    content="",
                    model=model,
                    provider="router",
                    error=f"All endpoints failed. Last error: {str(e)}"
                )
    
    async def call(
        self,
        messages: Any,
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        路由调用
        
        Args:
            messages: 消息
            model: 模型名称
            stream: 是否流式
            **kwargs: 额外参数
        
        Returns:
            ModelResponse 或 AsyncIterator[StreamChunk]
        """
        if stream:
            return self._call_stream(messages, model, **kwargs)
        else:
            return await self._call_single(messages, model, **kwargs)
    
    async def _call_stream(
        self,
        messages: Any,
        model: str,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        流式调用
        """
        tried_endpoints = []
        
        while True:
            endpoint = await self._select_endpoint(model)
            
            if endpoint is None:
                yield StreamChunk(
                    content="",
                    delta="",
                    model=model,
                    provider="router",
                    raw_chunk={"error": "No available endpoints"}
                )
                return
            
            # 避免重复尝试
            if endpoint in tried_endpoints:
                yield StreamChunk(
                    content="",
                    delta="",
                    model=model,
                    provider="router",
                    raw_chunk={"error": "All endpoints failed"}
                )
                return
            
            tried_endpoints.append(endpoint)
            success = False
            
            try:
                async for chunk in endpoint.provider.call_stream(messages, model, **kwargs):
                    if isinstance(chunk, StreamChunk) and chunk.raw_chunk.get("error"):
                        raise Exception(chunk.raw_chunk["error"])
                    success = True
                    yield chunk
                
                if success:
                    endpoint.consecutive_failures = 0
                    return
                    
            except Exception as e:
                endpoint.consecutive_failures += 1
                endpoint.last_failure_time = time.time()
                
                # 如果启用了故障转移且还有可用的端点，继续尝试
                if self.failover_enabled and len(tried_endpoints) < len(self.get_endpoints(model)):
                    continue
                
                yield StreamChunk(
                    content="",
                    delta="",
                    model=model,
                    provider="router",
                    raw_chunk={"error": f"All endpoints failed. Last error: {str(e)}"}
                )
                return
    
    def get_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        stats = {
            "strategy": self.strategy.value,
            "total_models": len(self._endpoints),
            "endpoints": {}
        }
        
        for model, endpoints in self._endpoints.items():
            stats["endpoints"][model] = [
                {
                    "provider": ep.provider.provider_name,
                    "priority": ep.priority,
                    "weight": ep.weight,
                    "enabled": ep.enabled,
                    "available": ep.is_available,
                    "health_score": ep.health_score,
                    "consecutive_failures": ep.consecutive_failures,
                    "request_count": ep.request_count
                }
                for ep in endpoints
            ]
        
        return stats
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        results = {}
        for model, endpoints in self._endpoints.items():
            for ep in endpoints:
                key = f"{model}/{ep.provider.provider_name}"
                try:
                    is_healthy = await ep.provider.health_check()
                    ep.consecutive_failures = 0 if is_healthy else ep.consecutive_failures
                    results[key] = is_healthy
                except:
                    results[key] = False
        return results
    
    def reset(self):
        """重置路由"""
        for endpoints in self._endpoints.values():
            for ep in endpoints:
                ep.consecutive_failures = 0
                ep.last_failure_time = 0


# 全局路由器实例
_router_instance: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """获取全局路由器"""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter()
    return _router_instance


def reset_router():
    """重置全局路由器"""
    global _router_instance
    _router_instance = None
