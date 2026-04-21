"""
MiniMax Provider - 完善版
MiniMax 大模型系列

文档: https://www.minimaxi.com/document
"""

import aiohttp
import json
from typing import Any, Dict, AsyncIterator, Optional, List
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole

import logging
logger = logging.getLogger(__name__)


class MiniMaxProvider(BaseProvider):
    """MiniMax 提供商 - 完善版"""
    
    provider_name = "minimax"
    provider_display_name = "MiniMax"
    
    # 完整模型列表
    supported_models = [
        # 通用对话模型
        "abab6.5s-chat",              # 增强版 6.5S
        "abab6.5-chat",               # 标准版 6.5
        "abab5.5-chat",               # 5.5版本
        "abab5s-chat",                 # 5S版本
        # MiniMax 系列
        "MiniMax-Text-01",            # 文本模型 01
        "MiniMax-Text-02",            # 文本模型 02
        "MiniMax-Embedding-01",       # Embedding 模型
        # 角色扮演模型
        "RolePlay-01",                # 角色扮演
        # 其他
        "assistant-function",         # 函数助手
    ]
    
    # 模型分组
    MODEL_GROUPS = {
        "chat": ["abab6.5s-chat", "abab6.5-chat", "abab5.5-chat", "abab5s-chat"],
        "text": ["MiniMax-Text-01", "MiniMax-Text-02"],
        "embedding": ["MiniMax-Embedding-01"],
        "roleplay": ["RolePlay-01"],
    }
    
    def __init__(
        self,
        config: ProviderConfig,
        group_id: str = ""
    ):
        super().__init__(config)
        self.group_id = group_id
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
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.group_id:
            headers["MiniMax-Group-Id"] = self.group_id
        
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
            "top_p": kwargs.get("top_p", 0.95)
        }
        
        # Token 采样控制
        if "min_tokens" in kwargs:
            payload["min_tokens"] = kwargs["min_tokens"]
        
        # 屏蔽词
        if "屏蔽词列表" in kwargs:
            payload["屏蔽词列表"] = kwargs["屏蔽词列表"]
        
        # 角色设定
        if "role_meta" in kwargs:
            payload["role_meta"] = kwargs["role_meta"]
        
        # 状态信息
        if "status_info" in kwargs:
            payload["status_info"] = kwargs["status_info"]
        
        # 参考信息
        if "reference_info" in kwargs:
            payload["reference_info"] = kwargs["reference_info"]
        
        # 函数调用
        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]
        
        # 采样修正
        if "sample_params" in kwargs:
            payload["sample_params"] = kwargs["sample_params"]
        
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
            "abab6.5s-chat": 16384,
            "abab6.5-chat": 16384,
            "abab5.5-chat": 8192,
            "abab5s-chat": 4096,
            "MiniMax-Text-01": 32768,
            "MiniMax-Text-02": 32768,
            "RolePlay-01": 16384,
        }
        return defaults.get(model, 8192)
    
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
                        try:
                            error_json = json.loads(error_text)
                            error_msg = error_json.get("base_resp", {}).get("status_msg", error_text)
                        except:
                            error_msg = error_text
                        raise Exception(f"[MiniMax Error] {error_msg}")
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
                            error_msg = error_json.get("base_resp", {}).get("status_msg", error_text)
                        except:
                            error_msg = error_text
                        raise Exception(f"[MiniMax Error] {error_msg}")
                    
                    result = await response.json()
                    
                    # 检查业务错误
                    base_resp = result.get("base_resp", {})
                    if base_resp.get("status_code", 0) != 0:
                        raise Exception(f"[MiniMax API Error] {base_resp.get('status_msg', 'Unknown error')}")
                    
                    return result
                    
        except aiohttp.ClientError as e:
            logger.error(f"MiniMax request failed: {e}")
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
            
            # MiniMax 的消息格式可能不同
            messages = choice.get("messages", [])
            message = messages[0] if messages else {}
            
            # 提取内容
            content = message.get("text", message.get("content", ""))
            
            # 解析 usage
            usage = self._parse_usage(response.get("usage", {}))
            
            return ModelResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                raw_response=response,
                usage=usage,
                finish_reason=choice.get("finish_reason"),
                tool_calls=message.get("tool_calls")
            )
            
        except Exception as e:
            logger.error(f"Failed to parse MiniMax response: {e}")
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
                base_resp = chunk_data.get("base_resp", {})
                if base_resp.get("status_code", 0) != 0:
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
                messages = choice.get("messages", [])
                if not messages:
                    continue
                
                delta = messages[0]
                content = delta.get("text", delta.get("content", ""))
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
        model: str = "abab6.5s-chat",
        stream: bool = False,
        **kwargs
    ) -> Any:
        """对话接口"""
        url = f"{self.config.base_url.rstrip('/')}/text/chatcompletion_v2"
        headers = self._build_headers()
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
    
    # ==================== Token 计算 ====================
    
    @staticmethod
    def count_tokens(text: str, model: str = "abab6.5s-chat") -> int:
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
            "abab6.5s-chat": {
                "input": 0.01,
                "output": 0.01,
                "description": "增强版 6.5S"
            },
            "abab6.5-chat": {
                "input": 0.005,
                "output": 0.005,
                "description": "标准版 6.5"
            },
            "abab5.5-chat": {
                "input": 0.001,
                "output": 0.002,
                "description": "5.5版本"
            },
            "abab5s-chat": {
                "input": 0.001,
                "output": 0.001,
                "description": "5S版本"
            },
            "MiniMax-Text-01": {
                "input": 0.005,
                "output": 0.015,
                "description": "文本模型 01"
            },
            "MiniMax-Embedding-01": {
                "input": 0.0001,
                "output": 0,
                "description": "Embedding 模型"
            },
        }
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()


def create_provider(api_key: str, group_id: str = "", **kwargs) -> MiniMaxProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="minimax",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://api.minimax.chat/v1"),
        timeout=kwargs.get("timeout", 60),
        extra_headers=kwargs.get("extra_headers", {})
    )
    return MiniMaxProvider(config, group_id=group_id)


import time
