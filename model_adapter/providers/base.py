"""
Neshama Model Adapter Layer - Base Provider
模型提供商基础抽象类

所有模型提供商需继承此类并实现核心方法
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable, AsyncIterator
from enum import Enum
import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


@dataclass
class Message:
    """对话消息"""
    role: Union[str, MessageRole]
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        result = {
            "role": self.role.value,
            "content": self.content
        }
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class ModelResponse:
    """模型响应统一格式"""
    content: str
    model: str
    provider: str
    raw_response: Any = None
    usage: Dict[str, int] = field(default_factory=lambda: {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    })
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
            "finish_reason": self.finish_reason,
            "error": self.error,
            "tool_calls": self.tool_calls
        }


@dataclass 
class StreamChunk:
    """流式响应块"""
    content: str
    delta: str
    model: str
    provider: str
    index: int = 0
    finish_reason: Optional[str] = None
    raw_chunk: Any = None


@dataclass
class ProviderConfig:
    """提供商配置"""
    name: str
    api_key: str
    base_url: str
    api_version: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3
    extra_headers: Dict[str, str] = field(default_factory=dict)


class BaseProvider(ABC):
    """模型提供商抽象基类"""
    
    # 提供商标识
    provider_name: str = "base"
    provider_display_name: str = "Base Provider"
    
    # 支持的模型列表
    supported_models: List[str] = []
    
    def __init__(self, config: ProviderConfig):
        """
        初始化提供商
        
        Args:
            config: 提供商配置
        """
        self.config = config
        self._session = None
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._request_count = 0
        self._failure_count = 0
        self._last_failure_time = 0
        self._health_score = 1.0  # 健康分数 0-1
    
    @property
    def is_healthy(self) -> bool:
        """检查提供商是否健康"""
        if self._failure_count >= 3:
            # 如果连续失败超过3次，检查是否在冷却期
            if time.time() - self._last_failure_time < 60:
                return False
            # 冷却期结束，重置计数
            self._failure_count = 0
        return self._health_score > 0.3
    
    @property
    def health_score(self) -> float:
        """获取健康分数"""
        return self._health_score
    
    def _record_success(self):
        """记录成功请求"""
        self._request_count += 1
        self._failure_count = 0
        self._health_score = min(1.0, self._health_score + 0.05)
    
    def _record_failure(self, error: str):
        """记录失败请求"""
        self._request_count += 1
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._health_score = max(0, self._health_score - 0.2)
        logger.warning(f"[{self.provider_name}] Request failed: {error}")
    
    @abstractmethod
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头 - 子类实现"""
        pass
    
    @abstractmethod
    def _build_payload(
        self,
        messages: List[Message],
        model: str,
        **kwargs
    ) -> Dict[str, Any]:
        """构建请求载荷 - 子类实现"""
        pass
    
    @abstractmethod
    def _parse_response(self, response: Dict, model: str) -> ModelResponse:
        """解析响应 - 子类实现"""
        pass
    
    @abstractmethod
    async def _make_request(
        self,
        url: str,
        headers: Dict,
        payload: Dict,
        timeout: int
    ) -> Dict:
        """发送HTTP请求 - 子类实现"""
        pass
    
    def _transform_messages(self, messages: Union[List[Message], List[Dict], str]) -> List[Message]:
        """转换消息格式为标准Message对象"""
        if isinstance(messages, str):
            # 如果是字符串，直接作为用户消息
            return [Message(role=MessageRole.USER, content=messages)]
        
        result = []
        for msg in messages:
            if isinstance(msg, Message):
                result.append(msg)
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                result.append(Message(
                    role=role,
                    content=content,
                    name=msg.get("name"),
                    tool_calls=msg.get("tool_calls"),
                    tool_call_id=msg.get("tool_call_id")
                ))
            else:
                raise ValueError(f"Invalid message format: {type(msg)}")
        return result
    
    async def call(
        self,
        messages: Union[List[Message], List[Dict], str],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ModelResponse, StreamChunk]:
        """
        调用模型 - 统一接口
        
        Args:
            messages: 消息列表或字符串
            model: 模型名称，默认使用第一个支持的模型
            stream: 是否使用流式响应
            **kwargs: 额外参数 (temperature, max_tokens, top_p, etc.)
        
        Returns:
            ModelResponse 或 StreamChunk (流式)
        """
        start_time = time.time()
        
        # 获取模型
        if model is None:
            model = self.supported_models[0] if self.supported_models else ""
        
        # 转换消息
        messages = self._transform_messages(messages)
        
        # 构建请求
        headers = self._build_headers()
        payload = self._build_payload(messages, model, stream=stream, **kwargs)
        
        try:
            # 发送请求
            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            response = await self._make_request(url, headers, payload, self.config.timeout)
            
            self._record_success()
            latency_ms = (time.time() - start_time) * 1000
            
            if stream:
                return response  # 流式响应直接返回原始数据
            else:
                return self._parse_response(response, model)
                
        except Exception as e:
            self._record_failure(str(e))
            latency_ms = (time.time() - start_time) * 1000
            
            return ModelResponse(
                content="",
                model=model,
                provider=self.provider_name,
                latency_ms=latency_ms,
                error=str(e)
            )
    
    def call_sync(
        self,
        messages: Union[List[Message], List[Dict], str],
        model: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """
        同步调用模型
        
        Args:
            messages: 消息列表或字符串
            model: 模型名称
            **kwargs: 额外参数
        
        Returns:
            ModelResponse
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.call(messages, model, **kwargs))
        finally:
            loop.close()
    
    async def call_stream(
        self,
        messages: Union[List[Message], List[Dict], str],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        流式调用模型
        
        Args:
            messages: 消息列表或字符串
            model: 模型名称
            **kwargs: 额外参数
        
        Yields:
            StreamChunk
        """
        response = await self.call(messages, model, stream=True, **kwargs)
        async for chunk in self._parse_stream_response(response, model):
            yield chunk
    
    @abstractmethod
    async def _parse_stream_response(
        self,
        raw_response: Any,
        model: str
    ) -> AsyncIterator[StreamChunk]:
        """解析流式响应 - 子类实现"""
        pass
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 是否健康
        """
        try:
            test_messages = [Message(role=MessageRole.USER, content="ping")]
            response = await self.call(test_messages, timeout=10)
            return response.error is None
        except Exception:
            return False
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "provider": self.provider_name,
            "request_count": self._request_count,
            "failure_count": self._failure_count,
            "health_score": self._health_score,
            "is_healthy": self.is_healthy
        }
    
    def reset_stats(self):
        """重置统计"""
        self._request_count = 0
        self._failure_count = 0
        self._health_score = 1.0
    
    def close(self):
        """关闭资源"""
        if self._executor:
            self._executor.shutdown(wait=True)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


from typing import AsyncIterator
