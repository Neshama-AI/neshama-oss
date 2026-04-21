"""
百度千帆 (QianFan) Provider - 完善版
文心一言系列模型

文档: https://cloud.baidu.com/doc/WENXINWORKSHOP/s/clntutve
"""

import aiohttp
import json
import hashlib
import hmac
import time
import base64
from typing import Any, Dict, AsyncIterator, Optional, List
from urllib.parse import urlencode
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole

import logging
logger = logging.getLogger(__name__)


class QianFanProvider(BaseProvider):
    """百度千帆提供商 - 完善版"""
    
    provider_name = "qianfan"
    provider_display_name = "百度千帆 (文心一言)"
    
    # 完整模型列表
    supported_models = [
        # ERNIE 4.0 系列
        "ernie-4.0-8k-latest",        # ERNIE 4.0 最新版
        "ernie-4.0-8k",               # ERNIE 4.0 标准版
        "ernie-4.0-8k-0414",          # ERNIE 4.0 特定版本
        "ernie-4.0-8k-exp",           # ERNIE 4.0 实验版
        # ERNIE 3.5 系列
        "ernie-3.5-8k",               # ERNIE 3.5 标准版
        "ernie-3.5-8k-0329",          # ERNIE 3.5 特定版本
        "ernie-3.5-8k-abtest",        # ERNIE 3.5 AB测试版
        # ERNIE Speed 系列
        "ernie-speed-128k",          # 高速版 128K
        "ernie-speed-32k",           # 高速版 32K
        "ernie-speed-8k",            # 高速版 8K
        "ernie-speed",                # 高速版基础版
        # ERNIE Lite 系列
        "ernie-lite-8k",              # 轻量版 8K
        "ernie-lite-8k-0308",         # 轻量版特定版本
        "ernie-lite-4k",              # 轻量版 4K
        "ernie-lite",                  # 轻量版基础
        # ERNIE Bot 系列 (旧版兼容)
        "ernie-bot",                   # ERNIE Bot
        "ernie-bot-turbo",            # ERNIE Bot Turbo
        "ernie-bot-4",                # ERNIE Bot 4
        # 垂直领域
        "ernie-sports",               # 体育领域
        "ernie-law",                  # 法律领域
        "ernie-health",               # 健康领域
        # Embedding
        "embedding-v1",               # Embedding v1
        "bge-large-zh",              # BGE 中文大模型
        # 其他
        "qianfan",                    # 千帆通用
        "llama-2-7b",                 # LLaMA 2
        "llama-2-13b",                # LLaMA 2 13B
        "chatglm2-6b-32k",           # ChatGLM2
        "aquila-chat-7b",             # Aquila
    ]
    
    # 模型分组
    MODEL_GROUPS = {
        "premium": ["ernie-4.0-8k-latest", "ernie-4.0-8k", "ernie-4.0-8k-exp"],
        "standard": ["ernie-3.5-8k", "ernie-3.5-8k-0329"],
        "fast": ["ernie-speed-128k", "ernie-speed-32k", "ernie-speed"],
        "lite": ["ernie-lite-8k", "ernie-lite-4k", "ernie-lite"],
        "legacy": ["ernie-bot", "ernie-bot-turbo", "ernie-bot-4"],
        "embedding": ["embedding-v1", "bge-large-zh"],
    }
    
    # API 端点配置
    API_ENDPOINTS = {
        "chat": "/chat/completions",
        "embedding": "/embeddings",
    }
    
    def __init__(
        self,
        config: ProviderConfig,
        access_key: str = "",
        secret_key: str = ""
    ):
        super().__init__(config)
        self.access_key = access_key
        self.secret_key = secret_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建会话"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=30
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def _get_access_token(self) -> str:
        """获取 Access Token"""
        if self._token and time.time() < self._token_expires_at - 300:
            return self._token
        
        # 使用 API Key 和 Secret Key 获取 Token
        # 实际实现需要调用百度 OAuth 接口
        # https://aip.baidubce.com/oauth/2.0/token
        
        # 简化实现：如果有 access_key，直接使用
        if self.access_key:
            self._token = self.access_key
            return self._token
        
        # 否则使用 api_key
        self._token = self.config.api_key
        return self._token
    
    def _sign_request(
        self,
        method: str,
        path: str,
        params: Dict = {},
        body: str = ""
    ) -> str:
        """
        生成签名 (HMAC-SHA256)
        
        百度千帆使用 BCE 签名算法
        """
        if not self.secret_key:
            return ""
        
        # 简化的签名过程
        # 完整实现参考: https://cloud.baidu.com/doc/WENXINWORKSHOP/s/6lldm6w7u
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        
        # 构建待签名字符串
        signed_headers = "host;x-bce-date"
        headers = {
            "host": "qianfan.baidubce.com",
            "x-bce-date": timestamp
        }
        
        # 简化版本
        return f"bce-auth-v1/{self.access_key}/{timestamp}/1800"
    
    def _build_headers(self, auth_token: str = "") -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        elif self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
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
            "messages": self._format_messages(messages),
            "stream": stream,
        }
        
        # 文心特有参数
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        elif "max_output_tokens" in kwargs:
            payload["max_output_tokens"] = kwargs["max_output_tokens"]
        else:
            payload["max_output_tokens"] = self._get_default_max_tokens(model)
        
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        
        # 惩罚参数
        if "penalty_score" in kwargs:
            payload["penalty_score"] = kwargs["penalty_score"]
        
        # 停止词
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        
        # 随机种子
        if "seed" in kwargs:
            payload["seed"] = kwargs["seed"]
        
        # 函数调用
        if "tools" in kwargs and kwargs["tools"]:
            payload["functions"] = kwargs["tools"]
        
        return payload
    
    def _format_messages(self, messages) -> List[Dict]:
        """格式化消息"""
        formatted = []
        
        for msg in messages:
            if isinstance(msg, Message):
                msg_dict = msg.to_dict()
                # 过滤 None 值
                msg_dict = {k: v for k, v in msg_dict.items() if v is not None}
                formatted.append(msg_dict)
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
            "ernie-4.0-8k-latest": 8192,
            "ernie-4.0-8k": 8192,
            "ernie-3.5-8k": 2048,
            "ernie-speed-128k": 128000,
            "ernie-speed-32k": 32000,
            "ernie-speed": 8192,
            "ernie-lite-8k": 2048,
            "ernie-lite": 2048,
            "ernie-bot": 2048,
            "ernie-bot-turbo": 2048,
        }
        return defaults.get(model, 2048)
    
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
        
        try:
            if stream:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"QianFan API error: {response.status} - {error_text}")
                    return response
            else:
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
                            error_msg = error_json.get("error_msg", error_text)
                        except:
                            error_msg = error_text
                        raise Exception(f"[QianFan Error] {error_msg}")
                    
                    result = await response.json()
                    return result
                    
        except aiohttp.ClientError as e:
            logger.error(f"QianFan request failed: {e}")
            raise
    
    def _parse_response(self, response: Dict, model: str) -> ModelResponse:
        """解析响应"""
        try:
            # 检查错误
            if "error_code" in response and response["error_code"] != 0:
                return ModelResponse(
                    content="",
                    model=model,
                    provider=self.provider_name,
                    error=f"API Error {response.get('error_code')}: {response.get('error_msg', 'Unknown')}"
                )
            
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
                tool_calls=message.get("function_call") or message.get("tool_calls")
            )
            
        except Exception as e:
            logger.error(f"Failed to parse QianFan response: {e}")
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
                
                # 检查错误
                if "error_code" in chunk_data and chunk_data["error_code"] != 0:
                    yield StreamChunk(
                        content="",
                        delta="",
                        model=model,
                        provider=self.provider_name,
                        index=0,
                        finish_reason="error",
                        raw_chunk=chunk_data
                    )
                    break
                
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
        model: str = "ernie-speed-128k",
        stream: bool = False,
        **kwargs
    ) -> Any:
        """对话接口"""
        # 获取 token
        auth_token = await self._get_access_token()
        
        url = f"{self.config.base_url.rstrip('/')}{self.API_ENDPOINTS['chat']}"
        headers = self._build_headers(auth_token)
        payload = self._build_payload(messages, model, stream, **kwargs)
        
        start_time = time.time()
        
        try:
            if stream:
                response = await self._make_request(
                    url, headers, payload, self.config.timeout, stream=True
                )
                self._record_success()
                return self._parse_stream_response(response, model)
            else:
                response = await self._make_request(
                    url, headers, payload, self.config.timeout, stream=False
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
        model: str = "embedding-v1",
        **kwargs
    ) -> Dict[str, Any]:
        """获取文本 Embedding"""
        auth_token = await self._get_access_token()
        
        url = f"{self.config.base_url.rstrip('/')}{self.API_ENDPOINTS['embedding']}"
        headers = self._build_headers(auth_token)
        
        payload = {
            "model": model,
            "input": {"texts": texts}
        }
        
        try:
            response = await self._make_request(
                url, headers, payload, self.config.timeout, stream=False
            )
            self._record_success()
            return response
        except Exception as e:
            self._record_failure(str(e))
            return {"error": str(e), "model": model, "provider": self.provider_name}
    
    # ==================== Token 计算 ====================
    
    @staticmethod
    def count_tokens(text: str, model: str = "ernie-3.5-8k") -> int:
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
            "ernie-4.0-8k-latest": {
                "input": 0.12,
                "output": 0.12,
                "description": "ERNIE 4.0 最新版"
            },
            "ernie-4.0-8k": {
                "input": 0.12,
                "output": 0.12,
                "description": "ERNIE 4.0 标准版"
            },
            "ernie-3.5-8k": {
                "input": 0.012,
                "output": 0.012,
                "description": "ERNIE 3.5"
            },
            "ernie-speed-128k": {
                "input": 0.004,
                "output": 0.008,
                "description": "高速版 128K"
            },
            "ernie-speed-32k": {
                "input": 0.004,
                "output": 0.008,
                "description": "高速版 32K"
            },
            "ernie-lite-8k": {
                "input": 0.0008,
                "output": 0.002,
                "description": "轻量版 8K"
            },
            "embedding-v1": {
                "input": 0.0005,
                "output": 0,
                "description": "Embedding v1"
            },
        }
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()


def create_provider(
    api_key: str = "",
    access_key: str = "",
    secret_key: str = "",
    **kwargs
) -> QianFanProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="qianfan",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://qianfan.baidubce.com/v2"),
        timeout=kwargs.get("timeout", 60),
        extra_headers=kwargs.get("extra_headers", {})
    )
    return QianFanProvider(
        config,
        access_key=access_key,
        secret_key=secret_key
    )


import time
