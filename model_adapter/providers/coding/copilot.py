"""
GitHub Copilot Provider
GitHub Copilot 代码助手

文档: https://docs.github.com/en/copilot
"""

import aiohttp
import json
from typing import Any, Dict, AsyncIterator, Optional
from ..base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole


class CopilotProvider(BaseProvider):
    """GitHub Copilot 提供商"""
    
    provider_name = "copilot"
    provider_display_name = "GitHub Copilot"
    
    supported_models = [
        "gpt-4",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo"
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
            "Content-Type": "application/json",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "Copilot/1.145.0",
            "Accept": "application/json"
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
        # Copilot 使用 completions API 格式
        prompt = "\n".join([
            f"{msg.role.value}: {msg.content}" 
            for msg in messages
        ])
        
        payload = {
            "prompt": prompt,
            "stream": stream,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.2),
            "top_p": kwargs.get("top_p", 1.0)
        }
        
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
                raise Exception(f"Copilot API error: {response.status} - {error_text}")
            
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
            text = choice.get("text", "")
            
            return ModelResponse(
                content=text,
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
                delta = chunk_data.get("choices", [{}])[0].get("text", "")
                
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
            model = self.supported_models[0] if self.supported_models else "gpt-4"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/engines/copilot-codex/completions"
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
            model = self.supported_models[0] if self.supported_models else "gpt-4"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/engines/copilot-codex/completions"
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


def create_provider(api_key: str, **kwargs) -> CopilotProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="copilot",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://api.githubcopilot.com"),
        timeout=kwargs.get("timeout", 60)
    )
    return CopilotProvider(config)
