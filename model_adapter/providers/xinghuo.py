"""
讯飞星火 (XingHuo) Provider
讯飞认知大模型系列

文档: https://www.xfyun.cn/doc/spark/Web.html
"""

import aiohttp
import json
import hashlib
import hmac
import base64
import time
from typing import Any, Dict, AsyncIterator, Optional
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole


class XingHuoProvider(BaseProvider):
    """讯飞星火提供商"""
    
    provider_name = "xinghuo"
    provider_display_name = "讯飞星火"
    
    supported_models = [
        "generalv4.0",    # 星火4.0
        "generalv3.5",   # 星火3.5
        "generalv3.0",   # 星火3.0
        "generalv2.0",    # 星火2.0
        "general"        # 通用版
    ]
    
    # 模型到版本的映射
    MODEL_VERSION_MAP = {
        "generalv4.0": "4.0",
        "generalv3.5": "3.5",
        "generalv3.0": "3.0",
        "generalv2.0": "2.0",
        "general": "1.1"
    }
    
    def __init__(self, config: ProviderConfig, app_id: str = ""):
        super().__init__(config)
        self.app_id = app_id
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    def _generate_auth_url(self, host: str, path: str) -> str:
        """生成鉴权URL"""
        # 讯飞使用特殊的鉴权方式
        import urllib.parse
        
        # 生成 RFC1123 格式的时间戳
        now = time.time()
        expires = int(now + 30)  # 30秒有效期
        
        # 简化鉴权，实际使用请参考官方文档
        return f"{self.config.base_url}{path}"
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
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
        # 转换消息格式
        formatted_messages = []
        for msg in messages:
            role = msg.role.value
            if role == "system":
                role = "system"
            elif role == "assistant":
                role = "assistant"
            else:
                role = "user"
            
            formatted_messages.append({
                "role": role,
                "content": msg.content
            })
        
        # 讯飞特有的payload结构
        payload = {
            "header": {
                "app_id": self.app_id or "default",
                "uid": kwargs.get("uid", "default")
            },
            "parameter": {
                "chat": {
                    "domain": model,
                    "temperature": kwargs.get("temperature", 0.5),
                    "max_tokens": kwargs.get("max_tokens", 2048),
                    "top_k": kwargs.get("top_k", 4),
                    "chat_id": kwargs.get("chat_id", "")
                }
            },
            "payload": {
                "message": {
                    "text": formatted_messages
                }
            }
        }
        
        return payload
    
    async def _make_request(
        self,
        url: str,
        headers: Dict,
        payload: Dict,
        timeout: int,
        stream: bool = False
    ) -> Any:
        """发送HTTP请求"""
        session = await self._get_session()
        
        if stream:
            async with session.post(
                url,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"XingHuo API error: {response.status} - {error_text}")
                return response
        else:
            async with session.post(
                url,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"XingHuo API error: {response.status} - {error_text}")
                
                result = await response.json()
                
                # 检查错误
                if result.get("header", {}).get("code", 0) != 0:
                    raise Exception(f"XingHuo API error: {result['header'].get('message', 'Unknown error')}")
                
                return result
    
    def _parse_response(self, response: Dict, model: str) -> ModelResponse:
        """解析响应"""
        try:
            choices = response.get("payload", {}).get("choices", {})
            text_parts = choices.get("text", [])
            
            content = ""
            for part in text_parts:
                content += part.get("content", "")
            
            # 解析 usage
            usage_data = response.get("payload", {}).get("usage", {})
            usage = {
                "prompt_tokens": usage_data.get("text", {}).get("prompt_tokens", 0),
                "completion_tokens": usage_data.get("text", {}).get("completion_tokens", 0),
                "total_tokens": usage_data.get("text", {}).get("total_tokens", 0)
            }
            
            return ModelResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                raw_response=response,
                usage=usage
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
                
                # 检查header
                if chunk_data.get("header", {}).get("code", 0) != 0:
                    raise Exception(f"API Error: {chunk_data['header'].get('message')}")
                
                choices = chunk_data.get("payload", {}).get("choices", {})
                text_parts = choices.get("text", [])
                
                for part in text_parts:
                    content = part.get("content", "")
                    if content:
                        yield StreamChunk(
                            content=content,
                            delta=content,
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
            model = self.supported_models[0] if self.supported_models else "generalv3.5"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/v2.0/huaiwei"
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
            model = self.supported_models[0] if self.supported_models else "generalv3.5"
        
        messages = self._transform_messages(messages)
        headers = self._build_headers()
        payload = self._build_payload(messages, model, **kwargs)
        
        try:
            url = f"{self.config.base_url.rstrip('/')}/v2.0/huaiwei"
            response = await self._make_request(url, headers, payload, self.config.timeout, stream=True)
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


def create_provider(api_key: str, app_id: str = "", **kwargs) -> XingHuoProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="xinghuo",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://spark-api.xf-yun.com"),
        timeout=kwargs.get("timeout", 60)
    )
    return XingHuoProvider(config, app_id)
