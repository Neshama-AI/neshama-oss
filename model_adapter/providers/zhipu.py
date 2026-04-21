"""
智谱 GLM (ZhipuAI) Provider - 完善版
智谱大模型系列

文档: https://open.bigmodel.cn/dev/api
"""

import aiohttp
import json
from typing import Any, Dict, AsyncIterator, Optional, List
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole

import logging
logger = logging.getLogger(__name__)


class ZhipuProvider(BaseProvider):
    """智谱GLM提供商 - 完善版"""
    
    provider_name = "zhipu"
    provider_display_name = "智谱GLM"
    
    # 完整模型列表
    supported_models = [
        # GLM-4 系列
        "glm-4",                       # GLM-4 标准版
        "glm-4-plus",                  # GLM-4 Plus
        "glm-4-flash",                 # GLM-4 Flash (快速版)
        "glm-4-air",                   # GLM-4 Air (轻量版)
        "glm-4-airx",                  # GLM-4 AirX
        "glm-4-long",                  # GLM-4 长文本版
        "glm-4v",                      # GLM-4V 视觉版
        "glm-4v-plus",                 # GLM-4V Plus
        # GLM-3 系列
        "glm-3-turbo",                # GLM-3 Turbo
        # Agent 模型
        "glm-4-alltools",             # 全工具版
        "glm-4-function",             # 函数调用版
        # CharacterGLM
        "characterglm",               # 角色扮演模型
        "characterglm-6b",            # 角色扮演 6B
        # Embedding
        "embedding-2",               # Embedding v2
        "text-embedding",            # 文本 Embedding
        # 其他
        "cogview-3",                  # 图像生成
        "cogview-3-plus",             # 图像生成 Plus
        "cogview-2",                   # 图像生成 v2
    ]
    
    # 模型分组
    MODEL_GROUPS = {
        "premium": ["glm-4", "glm-4-plus"],
        "standard": ["glm-4-flash", "glm-4-air", "glm-4-airx"],
        "long": ["glm-4-long"],
        "vision": ["glm-4v", "glm-4v-plus"],
        "function": ["glm-4-function", "glm-4-alltools"],
        "turbo": ["glm-3-turbo"],
        "character": ["characterglm", "characterglm-6b"],
        "embedding": ["embedding-2", "text-embedding"],
        "image": ["cogview-3", "cogview-3-plus", "cogview-2"],
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
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
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
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
            "max_tokens": kwargs.get("max_tokens", self._get_default_max_tokens(model)),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": stream
        }
        
        # 智谱特有参数
        if kwargs.get("do_sample"):
            payload["do_sample"] = kwargs["do_sample"]
        
        if "top_k" in kwargs:
            payload["top_k"] = kwargs["top_k"]
        
        # 增量输出 (流式)
        if stream and "incremental" in kwargs:
            payload["incremental"] = kwargs["incremental"]
        
        # 工具调用
        if "tools" in kwargs and kwargs["tools"]:
            payload["tools"] = kwargs["tools"]
        
        # 工具选择
        if "tool_choice" in kwargs:
            payload["tool_choice"] = kwargs["tool_choice"]
        
        # 请求 ID
        if "request_id" in kwargs:
            payload["request_id"] = kwargs["request_id"]
        
        # 对话 ID (用于多轮对话)
        if "conversation_id" in kwargs:
            payload["conversation_id"] = kwargs["conversation_id"]
        
        # 角色设定
        if "role_meta" in kwargs:
            payload["role_meta"] = kwargs["role_meta"]
        
        # 状态信息
        if "chat_id" in kwargs:
            payload["chat_id"] = kwargs["chat_id"]
        
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
            "glm-4": 128000,
            "glm-4-plus": 128000,
            "glm-4-flash": 32000,
            "glm-4-air": 32000,
            "glm-4-airx": 32000,
            "glm-4-long": 128000,
            "glm-4v": 4096,
            "glm-4v-plus": 4096,
            "glm-3-turbo": 128000,
            "glm-4-function": 128000,
            "glm-4-alltools": 128000,
            "characterglm": 8192,
            "characterglm-6b": 8192,
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
                        error_msg = error_json.get("error", {}).get("message", error_text)
                    except:
                        error_msg = error_text
                    raise Exception(f"[Zhipu Error {response.status}] {error_msg}")
                
                result = await response.json()
                
                # 检查API错误
                if "error" in result:
                    raise Exception(f"[Zhipu API Error] {result['error']}")
                
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"Zhipu request failed: {e}")
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
            logger.error(f"Failed to parse Zhipu response: {e}")
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
        index = 0
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
                    index=index,
                    finish_reason="stop",
                    raw_chunk=None
                )
                break
            
            if line.startswith("data: "):
                line = line[6:]
            
            try:
                chunk_data = json.loads(line)
                
                # 检查错误
                if "error" in chunk_data:
                    yield StreamChunk(
                        content="",
                        delta="",
                        model=model,
                        provider=self.provider_name,
                        index=index,
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
                    index=index,
                    finish_reason=finish_reason,
                    raw_chunk=chunk_data
                )
                
                index += 1
                
                if finish_reason == "stop":
                    break
                    
            except json.JSONDecodeError:
                continue
    
    async def chat(
        self,
        messages: list,
        model: str = "glm-4",
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
                        raise Exception(f"Zhipu API error: {response.status} - {error_text}")
                    
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
        model: str = "embedding-2",
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
    def count_tokens(text: str, model: str = "glm-4") -> int:
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
            "glm-4": {
                "input": 0.1,
                "output": 0.1,
                "description": "GLM-4 标准版"
            },
            "glm-4-plus": {
                "input": 0.1,
                "output": 0.1,
                "description": "GLM-4 Plus"
            },
            "glm-4-flash": {
                "input": 0.001,
                "output": 0.001,
                "description": "GLM-4 Flash (快速版)"
            },
            "glm-4-air": {
                "input": 0.001,
                "output": 0.002,
                "description": "GLM-4 Air"
            },
            "glm-4-airx": {
                "input": 0.002,
                "output": 0.004,
                "description": "GLM-4 AirX"
            },
            "glm-4-long": {
                "input": 0.03,
                "output": 0.06,
                "description": "GLM-4 长文本版"
            },
            "glm-4v": {
                "input": 0.1,
                "output": 0.1,
                "description": "GLM-4V 视觉版"
            },
            "glm-4v-plus": {
                "input": 0.05,
                "output": 0.05,
                "description": "GLM-4V Plus"
            },
            "glm-3-turbo": {
                "input": 0.001,
                "output": 0.001,
                "description": "GLM-3 Turbo"
            },
            "glm-4-function": {
                "input": 0.05,
                "output": 0.05,
                "description": "函数调用版"
            },
            "embedding-2": {
                "input": 0.0001,
                "output": 0,
                "description": "Embedding v2"
            },
        }
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()


def create_provider(api_key: str, **kwargs) -> ZhipuProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="zhipu",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://open.bigmodel.cn/api/paas/v4"),
        timeout=kwargs.get("timeout", 60),
        extra_headers=kwargs.get("extra_headers", {})
    )
    return ZhipuProvider(config)


import time
