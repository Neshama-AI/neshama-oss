"""
Anthropic Provider
Claude 系列模型

文档: https://docs.anthropic.com/claude/reference
"""

import aiohttp
import json
from typing import Any, Dict, AsyncIterator, Optional
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole


class AnthropicProvider(BaseProvider):
    """Anthropic Claude 提供商"""
    
    provider_name = "anthropic"
    provider_display_name = "Anthropic (Claude)"
    
    supported_models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-latest",
        "claude-3-opus-20240229",
        "claude-3-opus-latest",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]
    
    # 模型名称映射
    MODEL_ALIASES = {
        "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
        "claude-3-opus": "claude-3-opus-20240229",
        "claude-3-sonnet": "claude-3-sonnet-20240229",
        "claude-3-haiku": "claude-3-haiku-20240307"
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    def _normalize_model(self, model: str) -> str:
        """规范化模型名称"""
        return self.MODEL_ALIASES.get(model, model)
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true"
        }
        headers.update(self.config.extra_headers)
        return headers
    
    def _transform_messages_to_anthropic(self, messages: list[Message]) -> tuple:
        """
        转换消息格式为 Anthropic 格式
        
        Returns:
            (system_prompt, transformed_messages)
        """
        system_prompt = ""
        transformed = []
        
        for msg in messages:
            role = msg.role.value
            content = msg.content
            
            if role == "system":
                system_prompt += content + "\n"
            else:
                # Anthropic 只支持 user 和 assistant
                if role == "function":
                    role = "user"  # 转换为user角色
                transformed.append({
                    "role": role,
                    "content": content
                })
        
        return system_prompt.strip(), transformed
    
    def _build_payload(
        self,
        messages: list[Message],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """构建请求载荷"""
        system, transformed_messages = self._transform_messages_to_anthropic(messages)
        
        # 使用 system 字段或第一条 system 消息
        if system and "system" not in kwargs:
            kwargs["system"] = system
        
        payload = {
            "model": self._normalize_model(model),
            "messages": transformed_messages,
            "stream": stream,
            "max_tokens": kwargs.pop("max_tokens", kwargs.pop("max_output_tokens", 4096)),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p"),
            "top_k": kwargs.get("top_k"),
            "system": kwargs.get("system")
        }
        
        # 移除None值
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # Anthropic 的工具使用
        if "tools" in kwargs:
            payload["tools"] = kwargs["tools"]
        
        return payload
    
    async def _make_request(
        self,
        url: str,
        headers: Dict,
        payload: Dict,
        timeout: int
    ) -> Dict:
        """发送HTTP请求"""
        session = await self._get_session()
        
        async with session.post(
            url,
            headers=headers,
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                try:
                    error_json = json.loads(error_text)
                    error_msg = error_json.get("error", {}).get("message", error_text)
                except:
                    error_msg = error_text
                raise Exception(f"Anthropic API error: {response.status} - {error_msg}")
            
            result = await response.json()
            return result
    
    def _parse_response(self, response: Dict, model: str) -> ModelResponse:
        """解析响应"""
        try:
            content = response.get("content", [])
            text = ""
            tool_calls = []
            
            for block in content:
                if block.get("type") == "text":
                    text += block.get("text", "")
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", {})
                    })
            
            usage = {
                "input_tokens": response.get("usage", {}).get("input_tokens", 0),
                "output_tokens": response.get("usage", {}).get("output_tokens", 0)
            }
            usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
            
            return ModelResponse(
                content=text,
                model=model,
                provider=self.provider_name,
                raw_response=response,
                usage=usage,
                finish_reason=response.get("stop_reason"),
                tool_calls=tool_calls if tool_calls else None
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
        index = 0
        async for line in response.content:
            line = line.decode('utf-8').strip()
            if not line:
                continue
            
            if line.startswith("data: "):
                line = line[6:]
            
            if line == "[DONE]":
                continue
            
            try:
                chunk_data = json.loads(line)
                event_type = chunk_data.get("type", "")
                
                if event_type == "content_block_delta":
                    delta = chunk_data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        yield StreamChunk(
                            content=text,
                            delta=text,
                            model=model,
                            provider=self.provider_name,
                            index=index,
                            raw_chunk=chunk_data
                        )
                        index += 1
                
                elif event_type == "message_delta":
                    finish_reason = chunk_data.get("delta", {}).get("stop_reason")
                    if finish_reason:
                        yield StreamChunk(
                            content="",
                            delta="",
                            model=model,
                            provider=self.provider_name,
                            index=index,
                            finish_reason=finish_reason,
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
            model = "claude-3-5-sonnet-20241022"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/messages"
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
            model = "claude-3-5-sonnet-20241022"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/messages"
            session = await self._get_session()
            headers["anthropic-beta"] = "interleaved-predictions-1"
            headers["accept"] = "text/event-stream"
            
            async with session.post(
                url, headers=headers, json=payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Anthropic API error: {resp.status} - {error_text}")
                
                self._record_success()
                async for chunk in self._parse_stream_response(resp, model):
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


def create_provider(api_key: str, **kwargs) -> AnthropicProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="anthropic",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://api.anthropic.com/v1"),
        timeout=kwargs.get("timeout", 120)
    )
    return AnthropicProvider(config)
