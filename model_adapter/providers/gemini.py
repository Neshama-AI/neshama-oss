"""
Google Gemini Provider
Gemini 系列模型

文档: https://ai.google.dev/docs
"""

import aiohttp
import json
from typing import Any, Dict, AsyncIterator, Optional, Union, List
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole


class GeminiProvider(BaseProvider):
    """Google Gemini 提供商"""
    
    provider_name = "gemini"
    provider_display_name = "Google Gemini"
    
    supported_models = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash-latest",
        "gemini-1.0-pro",
        "gemini-pro"
    ]
    
    # 模型名称映射
    MODEL_VERSION_MAP = {
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini-1.5-flash": "gemini-1.5-flash",
        "gemini-1.0-pro": "gemini-1.0-pro",
        "gemini-pro": "gemini-pro"
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
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        if self.config.api_key:
            headers["x-goog-api-key"] = self.config.api_key
        headers.update(self.config.extra_headers)
        return headers
    
    def _transform_messages_to_gemini(self, messages: List[Message]) -> tuple:
        """
        转换消息格式为 Gemini 格式
        """
        contents = []
        system_instruction = ""
        
        for msg in messages:
            role = msg.role.value
            
            if role == "system":
                system_instruction += msg.content + "\n"
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": msg.content}]
                })
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg.content}]
                })
        
        return system_instruction.strip() or None, contents
    
    def _build_payload(
        self,
        messages: list[Message],
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """构建请求载荷"""
        system_instruction, contents = self._transform_messages_to_gemini(messages)
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": kwargs.get("max_tokens", 8192),
                "temperature": kwargs.get("temperature", 0.7),
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40)
            }
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        # Gemini 的 safety_settings
        if "safety_settings" in kwargs:
            payload["safetySettings"] = kwargs["safety_settings"]
        
        # Gemini 函数调用 (using tool)
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
                raise Exception(f"Gemini API error: {response.status} - {error_msg}")
            
            result = await response.json()
            
            # 检查是否有错误
            if "error" in result:
                raise Exception(f"Gemini API error: {result['error']}")
            
            return result
    
    def _parse_response(self, response: Dict, model: str) -> ModelResponse:
        """解析响应"""
        try:
            candidates = response.get("candidates", [])
            
            if not candidates:
                return ModelResponse(
                    content="",
                    model=model,
                    provider=self.provider_name,
                    error="No candidates in response"
                )
            
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            text = ""
            for part in parts:
                if "text" in part:
                    text += part["text"]
            
            # 解析 usage
            usage_metadata = response.get("usageMetadata", {})
            usage = {
                "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0)
            }
            
            finish_reason = candidate.get("finishReason", "")
            
            return ModelResponse(
                content=text,
                model=model,
                provider=self.provider_name,
                raw_response=response,
                usage=usage,
                finish_reason=finish_reason
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
            if not line:
                continue
            
            try:
                chunk_data = json.loads(line)
                
                # 跳过 prompt feedback
                if "promptFeedback" in chunk_data:
                    continue
                
                candidates = chunk_data.get("candidates", [])
                if not candidates:
                    continue
                
                delta = ""
                finish_reason = None
                
                for part in candidates[0].get("content", {}).get("parts", []):
                    if "text" in part:
                        delta += part["text"]
                
                if delta:
                    yield StreamChunk(
                        content=delta,
                        delta=delta,
                        model=model,
                        provider=self.provider_name,
                        index=0,
                        finish_reason=finish_reason,
                        raw_chunk=chunk_data
                    )
                
                # 检查是否完成
                if chunk_data.get("candidates", [{}])[0].get("finishReason"):
                    yield StreamChunk(
                        content="",
                        delta="",
                        model=model,
                        provider=self.provider_name,
                        index=0,
                        finish_reason=chunk_data["candidates"][0]["finishReason"],
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
            model = self.supported_models[0] if self.supported_models else "gemini-1.5-pro"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/models/{model}:generateContent"
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
            model = self.supported_models[0] if self.supported_models else "gemini-1.5-pro"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/models/{model}:generateContent?alt=sse"
            session = await self._get_session()
            
            async with session.post(
                url, headers=headers, json=payload
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Gemini API error: {resp.status} - {error_text}")
                
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


def create_provider(api_key: str, **kwargs) -> GeminiProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="gemini",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://generativelanguage.googleapis.com/v1beta"),
        timeout=kwargs.get("timeout", 120)
    )
    return GeminiProvider(config)
