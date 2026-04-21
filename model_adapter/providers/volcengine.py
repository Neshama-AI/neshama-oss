"""
火山引擎方舟 (VolcEngine) Provider - 完善版
豆包/云雀系列模型

文档: https://www.volcengine.com/docs/82379/1099475
"""

import aiohttp
import json
import hashlib
import hmac
import time
from typing import Any, Dict, AsyncIterator, Optional, List
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole

import logging
logger = logging.getLogger(__name__)


class VolcEngineProvider(BaseProvider):
    """火山引擎方舟提供商 - 完善版"""
    
    provider_name = "volcengine"
    provider_display_name = "火山引擎方舟 (豆包)"
    
    # 完整模型列表
    supported_models = [
        # Doubao 系列
        "doubao-pro-32k",             # 32K上下文
        "doubao-pro-128k",            # 128K上下文
        "doubao-lite-32k",            # 轻量版
        "doubao-pro-4k",              # 4K短文本
        "doubao-pro",                 # 标准版
        # Doubao-Vision 系列
        "doubao-vision-pro",          # 视觉理解
        "doubao-vision",              # 视觉版
        # Doubao-Embedding 系列
        "doubao-embedding",          # Embedding
        "doubao-embedding-s",        # Embedding 短文本
        # 云雀系列 (历史版本)
        "skylark2-pro",               # 云雀2
        "skylark-pro",                # 云雀
        "skylark-lite",               # 云雀轻量版
    ]
    
    # 模型分组
    MODEL_GROUPS = {
        "chat": ["doubao-pro-128k", "doubao-pro-32k", "doubao-pro-4k", "doubao-pro", "doubao-lite-32k"],
        "vision": ["doubao-vision-pro", "doubao-vision"],
        "embedding": ["doubao-embedding", "doubao-embedding-s"],
        "legacy": ["skylark2-pro", "skylark-pro", "skylark-lite"],
    }
    
    def __init__(
        self,
        config: ProviderConfig,
        account_id: str = "",
        secret_key: str = ""
    ):
        super().__init__(config)
        self.account_id = account_id
        self.secret_key = secret_key
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=30
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    def _generate_sign(self, timestamp: str) -> str:
        """
        生成签名 (TC3-HMAC-SHA256)
        
        火山引擎 API 使用 TC3-HMAC-SHA256 签名算法
        """
        if not self.secret_key:
            return ""
        
        # 简化签名，实际使用需参考官方文档
        # https://www.volcengine.com/docs/82379/1267682
        secret = self.secret_key.encode('utf-8')
        message = f"ARC3\n{timestamp}\n".encode('utf-8')
        
        import base64
        sign = base64.b64encode(
            hmac.new(secret, message, hashlib.sha256).digest()
        ).decode('utf-8')
        
        return sign
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        timestamp = str(int(time.time()))
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Date": timestamp,
            "X-Api-Key": self.config.api_key,
        }
        
        # 如果有 secret_key，添加签名
        if self.secret_key:
            headers["X-Signature"] = self._generate_sign(timestamp)
        
        # 如果有 account_id
        if self.account_id:
            headers["X-Account-Id"] = self.account_id
        
        headers.update(self.config.extra_headers)
        return headers
    
    def _build_payload(
        self,
        messages: list,
        model: str,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """构建请求载荷"""
        payload = {
            "model": model,
            "messages": self._format_messages(messages),
            "stream": stream,
            "max_tokens": kwargs.get("max_tokens", self._get_default_max_tokens(model)),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.8),
        }
        
        # 停止词
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        
        # 频率惩罚
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        
        # 存在惩罚
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        
        # 重复惩罚
        if "repetition_penalty" in kwargs:
            payload["repetition_penalty"] = kwargs["repetition_penalty"]
        
        # 响应格式
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]
        
        # 函数调用
        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]
        
        # 视觉消息处理
        if any(msg.get("role") == "user" and isinstance(msg.get("content"), list) 
               for msg in (messages if isinstance(messages[0], dict) else [])):
            # 处理多模态内容
            pass
        
        return payload
    
    def _format_messages(self, messages) -> List[Dict]:
        """格式化消息"""
        formatted = []
        
        for msg in messages:
            if isinstance(msg, Message):
                formatted.append(msg.to_dict())
            elif isinstance(msg, dict):
                formatted.append(msg)
            elif isinstance(msg, str):
                formatted.append({
                    "role": "user",
                    "content": msg
                })
        
        return formatted
    
    def _get_default_max_tokens(self, model: str) -> int:
        """获取模型默认最大token数"""
        defaults = {
            "doubao-pro-128k": 128000,
            "doubao-pro-32k": 32000,
            "doubao-lite-32k": 32000,
            "doubao-pro-4k": 4000,
            "doubao-pro": 8192,
            "doubao-vision-pro": 8000,
        }
        return defaults.get(model, 8192)
    
    async def _make_request(
        self,
        url: str,
        headers: Dict,
        payload: Dict,
        timeout: int
    ) -> Dict:
        """发送HTTP请求"""
        session = await self._get_session()
        
        try:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    try:
                        error_json = json.loads(error_text)
                        error_code = error_json.get("code", response.status)
                        error_msg = error_json.get("message", error_text)
                    except:
                        error_code = response.status
                        error_msg = error_text
                    
                    raise Exception(f"[VolcEngine Error {error_code}] {error_msg}")
                
                result = await response.json()
                
                # 检查错误
                if result.get("error"):
                    raise Exception(f"[VolcEngine API Error] {result['error']}")
                
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"VolcEngine request failed: {e}")
            raise
    
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
            
            # 解析 usage
            usage = self._parse_usage(response.get("usage", {}))
            
            return ModelResponse(
                content=message.get("content", ""),
                model=model,
                provider=self.provider_name,
                raw_response=response,
                usage=usage,
                finish_reason=choice.get("finish_reason"),
                tool_calls=message.get("tool_calls")
            )
            
        except Exception as e:
            logger.error(f"Failed to parse VolcEngine response: {e}")
            return ModelResponse(
                content="",
                model=model,
                provider=self.provider_name,
                raw_response=response,
                error=f"Parse error: {str(e)}"
            )
    
    def _parse_usage(self, usage: Dict) -> Dict[str, int]:
        """解析 usage"""
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
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
            
            if line == "data: [DONE]":
                yield StreamChunk(
                    content="",
                    delta="",
                    model=model,
                    provider=self.provider_name,
                    index=0,
                    finish_reason="stop",
                    raw_chunk=None
                )
                break
            
            if line.startswith("data: "):
                line = line[6:]
            
            try:
                chunk_data = json.loads(line)
                
                choices = chunk_data.get("choices", [])
                if not choices:
                    continue
                
                choice = choices[0]
                delta = choice.get("delta", {})
                content = delta.get("content", "")
                finish_reason = choice.get("finish_reason")
                
                yield StreamChunk(
                    content=content,
                    delta=content,
                    model=model,
                    provider=self.provider_name,
                    index=chunk_data.get("id", ""),
                    finish_reason=finish_reason,
                    raw_chunk=chunk_data
                )
                
                if finish_reason == "stop":
                    break
                    
            except json.JSONDecodeError:
                continue
    
    async def chat(
        self,
        messages: list,
        model: str = "doubao-pro-32k",
        stream: bool = False,
        **kwargs
    ) -> Any:
        """对话接口"""
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = self._build_headers()
        payload = self._build_payload(messages, model, stream, **kwargs)
        
        start_time = time.time()
        
        try:
            if stream:
                session = await self._get_session()
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"VolcEngine API error: {response.status} - {error_text}")
                    
                    self._record_success()
                    return self._parse_stream_response(response, model)
            else:
                response = await self._make_request(
                    url, headers, payload, self.config.timeout
                )
                self._record_success()
                
                latency_ms = (time.time() - start_time) * 1000
                result = self._parse_response(response, model)
                result.latency_ms = latency_ms
                return result
                
        except Exception as e:
            self._record_failure(str(e))
            latency_ms = (time.time() - start_time) * 1000
            
            if stream:
                async def error_stream():
                    yield StreamChunk(
                        content="",
                        delta="",
                        model=model,
                        provider=self.provider_name,
                        index=0,
                        finish_reason="error",
                        raw_chunk=None
                    )
                return error_stream()
            else:
                return ModelResponse(
                    content="",
                    model=model,
                    provider=self.provider_name,
                    latency_ms=latency_ms,
                    error=str(e)
                )
    
    # ==================== Embedding 接口 ====================
    
    async def embedding(
        self,
        texts: List[str],
        model: str = "doubao-embedding",
        **kwargs
    ) -> Dict[str, Any]:
        """获取文本 Embedding"""
        url = f"{self.config.base_url.rstrip('/')}/embeddings"
        headers = self._build_headers()
        
        payload = {
            "model": model,
            "input": {"texts": texts}
        }
        
        try:
            response = await self._make_request(
                url, headers, payload, self.config.timeout
            )
            self._record_success()
            return response
        except Exception as e:
            self._record_failure(str(e))
            return {"error": str(e), "model": model, "provider": self.provider_name}
    
    # ==================== Token 计算 ====================
    
    @staticmethod
    def count_tokens(text: str, model: str = "doubao-pro") -> int:
        """估算 token 数量"""
        import re
        cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        eng_words = len(re.findall(r'[a-zA-Z0-9]+', text))
        other_chars = len(text) - cjk_chars - eng_words
        
        return int(cjk_chars * 0.7 + eng_words * 0.25 + other_chars * 0.3)
    
    # ==================== 成本计算 ====================
    
    @staticmethod
    def get_pricing() -> Dict[str, Dict]:
        """获取模型定价"""
        return {
            "doubao-pro-128k": {
                "input": 0.005,
                "output": 0.01,
                "description": "128K上下文"
            },
            "doubao-pro-32k": {
                "input": 0.003,
                "output": 0.006,
                "description": "32K上下文"
            },
            "doubao-lite-32k": {
                "input": 0.001,
                "output": 0.002,
                "description": "轻量版"
            },
            "doubao-pro": {
                "input": 0.003,
                "output": 0.006,
                "description": "标准版"
            },
            "doubao-embedding": {
                "input": 0.0001,
                "output": 0,
                "description": "Embedding"
            },
        }
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()


def create_provider(
    api_key: str,
    account_id: str = "",
    secret_key: str = "",
    **kwargs
) -> VolcEngineProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="volcengine",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://ark.cn-beijing.volces.com/api/v3"),
        timeout=kwargs.get("timeout", 60),
        extra_headers=kwargs.get("extra_headers", {})
    )
    return VolcEngineProvider(
        config,
        account_id=account_id,
        secret_key=secret_key
    )


import time
