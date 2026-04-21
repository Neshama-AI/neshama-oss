"""
Cursor Provider
Cursor AI 代码助手

文档: https://cursor.com/api
"""

import aiohttp
import json
from typing import Any, Dict, AsyncIterator, Optional
from ..base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole


class CursorProvider(BaseProvider):
    """Cursor AI 提供商"""
    
    provider_name = "cursor"
    provider_display_name = "Cursor"
    
    supported_models = [
        "cursor-small",
        "cursor"
    ]
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        headers.update(self.config.extra_headers)
        return headers
    
    def _build_payload(
        self,
        messages: list[Message],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """构建请求载荷"""
        payload = {
            "model": model,
            "messages": [msg.to_dict() for msg in messages],
            "stream": stream,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.2)  # Cursor使用较低temperature
        }
        
        # Cursor 可能需要的特殊参数
        if "language" in kwargs:
            payload["language"] = kwargs["language"]
        
        return payload
    
    async def _make_request(
        self,
        url: str,
        headers: Dict,
        payload: Dict,
        timeout: int
    ) -> Any:
        """发送HTTP请求"""
        session = await self._get_session()
        
        async with session.post(
            url,
            headers=headers,
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Cursor API error: {response.status} - {error_text}")
            
            if "stream" in payload and payload["stream"]:
                return response
            return await response.json()
    
    def _parse_response(self, response: Dict, model: str) -> ModelResponse:
        """解析响应"""
        try:
            choices = response.get("choices", [])
            
            if not choices:
                return ModelResponse(
                    content="",
                    model=model,
                    provider=self.provider_name,
                    error="No choices in response"
                )
            
            choice = choices[0]
            message = choice.get("message", {})
            
            return ModelResponse(
                content=message.get("content", ""),
                model=model,
                provider=self.provider_name,
                raw_response=response,
                usage=response.get("usage", {}),
                finish_reason=choice.get("finish_reason")
            )
        except Exception as e:
            return ModelResponse(
                content="",
                model=model,
                provider=self.provider_name,
                raw_response=response,
                error=f"Parse error: {str(e)}"
            )
    
    async def _parse_stream_response(
        self,
        response: aiohttp.ClientResponse,
        model: str
    ) -> AsyncIterator[StreamChunk]:
        """解析流式响应"""
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if not line or line == "data: [DONE]":
                continue
            
            if line.startswith("data: "):
                line = line[6:]
            
            try:
                chunk_data = json.loads(line)
                delta = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                
                if delta:
                    yield StreamChunk(
                        content=delta,
                        delta=delta,
                        model=model,
                        provider=self.provider_name,
                        index=0,
                        raw_chunk=chunk_data
                    )
            except json.JSONDecodeError:
                continue
    
    async def call(
        self,
        messages,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ):
        """调用模型"""
        if stream:
            return self._call_stream(messages, model, **kwargs)
        else:
            return await self._call_sync(messages, model, **kwargs)
    
    async def _call_sync(
        self,
        messages,
        model: Optional[str] = None,
        **kwargs
    ):
        """同步调用模型 (非流式)"""
        import time
        
        start_time = time.time()
        
        if model is None:
            model = self.supported_models[0] if self.supported_models else "cursor-small"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            result = await self._make_request(url, headers, payload, self.config.timeout)
            self._record_success()
            latency_ms = (time.time() - start_time) * 1000
            response = self._parse_response(result, model)
            response.latency_ms = latency_ms
            return response
                
        except Exception as e:
            self._record_failure(str(e))
            latency_ms = (time.time() - start_time) * 1000
            return ModelResponse(
                content="", model=model, provider=self.provider_name,
                latency_ms=latency_ms, error=str(e)
            )
    
    async def _call_stream(
        self,
        messages,
        model: Optional[str] = None,
        **kwargs
    ):
        """流式调用模型"""
        import time
        
        start_time = time.time()
        
        if model is None:
            model = self.supported_models[0] if self.supported_models else "cursor-small"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/chat/completions"
            response = await self._make_request(url, headers, payload, self.config.timeout)
            self._record_success()
            async for chunk in self._parse_stream_response(response, model):
                yield chunk
                
        except Exception as e:
            self._record_failure(str(e))
            yield StreamChunk(
                content="", delta="", model=model, provider=self.provider_name,
                raw_chunk={"error": str(e)}
            )
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()


def create_provider(api_key: str, **kwargs) -> CursorProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="cursor",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://api.cursor.com/v1"),
        timeout=kwargs.get("timeout", 60)
    )
    return CursorProvider(config)
