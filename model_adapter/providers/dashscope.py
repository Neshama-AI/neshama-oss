"""
阿里云百炼 (DashScope) Provider - 完善版
通义千问系列模型

文档: https://help.aliyun.com/zh/dashscope/
"""

import aiohttp
import json
from typing import Any, Dict, AsyncIterator, Optional, List
from .base import BaseProvider, ProviderConfig, Message, ModelResponse, StreamChunk, MessageRole

import logging
logger = logging.getLogger(__name__)


class DashScopeProvider(BaseProvider):
    """阿里云百炼提供商 - 完善版"""
    
    provider_name = "dashscope"
    provider_display_name = "阿里云百炼 (通义千问)"
    
    # 完整模型列表
    supported_models = [
        # Qwen 系列
        "qwen-max",                    # 超大规模模型
        "qwen-max-longcontext",        # 超长上下文版本
        "qwen-plus",                   # 增强版
        "qwen-turbo",                  # 快速版
        "qwen-plus-vl",               # 视觉增强版
        "qwen-vl-plus",               # 视觉增强版
        "qwen-vl-max",                 # 视觉Max版
        "qwen-math-plus",             # 数学增强版
        "qwen-math",                   # 数学版
        # Qwen-Coder 系列
        "qwen-coder-plus",            # 编程增强版
        "qwen-coder-plus-v2",         # 编程增强版v2
        "qwen-coder",                  # 编程版
        "qwq-32b",                     # 思考模型
        # Embedding 模型
        "text-embedding-v3",          # Embedding v3
        "text-embedding",             # Embedding v1/v2
        # Rerank 模型
        "gte-rerank",                 # 重排序模型
        # 其他模型
        "bailian-v2",                  # 百炼v2
    ]
    
    # 模型分组配置
    MODEL_GROUPS = {
        "chat": ["qwen-max", "qwen-max-longcontext", "qwen-plus", "qwen-turbo"],
        "vision": ["qwen-vl-plus", "qwen-vl-max", "qwen-plus-vl"],
        "coding": ["qwen-coder-plus", "qwen-coder-plus-v2", "qwen-coder"],
        "math": ["qwen-math-plus", "qwen-math"],
        "thinking": ["qwq-32b"],
        "embedding": ["text-embedding-v3", "text-embedding"],
        "rerank": ["gte-rerank"],
    }
    
    # Token计算配置
    # 注意：通义千问使用 UTF-8 编码，中文每个字符约 1-4 tokens
    TOKEN_RATIO_CJK = 0.25      # CJK 字符到 token 的估算比率
    TOKEN_RATIO_ENG = 0.25      # 英文单词到 token 的估算比率
    
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
        # 转换消息格式
        formatted_messages = self._format_messages(messages)
        
        parameters = {
            "result_format": "message",
            "max_tokens": kwargs.get("max_tokens", self._get_default_max_tokens(model)),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.8),
            "top_k": kwargs.get("top_k", 50),
            "repetition_penalty": kwargs.get("repetition_penalty", 1.1)
        }
        
        # 流式输出配置
        if stream:
            parameters["incremental_output"] = kwargs.get("incremental_output", True)
        
        # 思考过程配置 (qwq 模型)
        if model == "qwq-32b":
            parameters["thinking_depth"] = kwargs.get("thinking_depth", 16)
        
        payload = {
            "model": model,
            "input": {
                "messages": formatted_messages
            },
            "parameters": parameters
        }
        
        # 处理函数调用
        if "tools" in kwargs and kwargs["tools"]:
            payload["parameters"]["tools"] = kwargs["tools"]
        
        # 音频参数 (如果有)
        if "voice" in kwargs:
            payload["input"]["audio"] = kwargs["voice"]
        
        return payload
    
    def _format_messages(self, messages) -> List[Dict]:
        """格式化消息"""
        formatted = []
        
        for msg in messages:
            if isinstance(msg, Message):
                formatted.append(msg.to_dict())
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                formatted_msg = {
                    "role": role,
                    "content": content
                }
                
                # 处理工具调用
                if "tool_calls" in msg:
                    formatted_msg["tool_calls"] = msg["tool_calls"]
                if "tool_call_id" in msg:
                    formatted_msg["tool_call_id"] = msg["tool_call_id"]
                if "name" in msg:
                    formatted_msg["name"] = msg["name"]
                
                formatted.append(formatted_msg)
            elif isinstance(msg, str):
                formatted.append({
                    "role": "user",
                    "content": msg
                })
        
        return formatted
    
    def _get_default_max_tokens(self, model: str) -> int:
        """获取模型默认最大token数"""
        defaults = {
            "qwen-max": 8192,
            "qwen-max-longcontext": 32768,
            "qwen-plus": 32768,
            "qwen-turbo": 8192,
            "qwen-coder-plus": 8192,
            "qwen-coder-plus-v2": 8192,
            "qwen-coder": 8192,
            "qwq-32b": 32768,
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
                # 处理错误响应
                if response.status != 200:
                    error_text = await response.text()
                    try:
                        error_json = json.loads(error_text)
                        error_code = error_json.get("error", {}).get("code", response.status)
                        error_msg = error_json.get("error", {}).get("message", error_text)
                    except:
                        error_code = response.status
                        error_msg = error_text
                    
                    raise self._create_error(error_code, error_msg, response.status)
                
                result = await response.json()
                
                # 检查 API 错误
                if "error" in result:
                    raise self._create_error(
                        result["error"].get("code", "API_ERROR"),
                        result["error"].get("message", "Unknown error"),
                        response.status
                    )
                
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"DashScope request failed: {e}")
            raise
    
    def _create_error(self, code: Any, message: str, status: int) -> Exception:
        """创建统一错误"""
        error_messages = {
            401: "API密钥无效或已过期",
            403: "没有权限访问该模型",
            429: "请求频率超限，请降低调用频率",
            500: "服务器内部错误",
            503: "服务暂时不可用",
            "InvalidParameter": "参数无效",
            "UnsupportedModel": "不支持的模型",
            "TokenExpired": "Token已过期",
        }
        
        description = error_messages.get(code, error_messages.get(status, message))
        return Exception(f"[DashScope Error {code}] {description}")
    
    def _parse_response(self, response: Dict, model: str) -> ModelResponse:
        """解析响应"""
        try:
            output = response.get("output", {})
            choices = output.get("choices", [])
            
            if not choices:
                return ModelResponse(
                    content="",
                    model=model,
                    provider=self.provider_name,
                    error="No choices in response"
                )
            
            choice = choices[0]
            message = choice.get("message", {})
            
            # 提取内容
            content = message.get("content", "")
            
            # 处理思考过程 (qwq 模型)
            reasoning_content = None
            if model == "qwq-32b" and "reasoning_content" in message:
                reasoning_content = message.get("reasoning_content")
            
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
            logger.error(f"Failed to parse DashScope response: {e}")
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
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
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
            
            # SSE 事件格式
            if line.startswith("data: "):
                line = line[6:]
            
            if line == "[DONE]":
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
            
            try:
                chunk_data = json.loads(line)
                
                # 提取增量内容
                output = chunk_data.get("output", {})
                delta = output.get("delta", "")
                finish_reason = output.get("finish_reason")
                
                # 索引
                output_index = chunk_data.get("output", {}).get("output_index", index)
                
                # 工具调用
                tool_calls = None
                if "tool_calls" in output:
                    tool_calls = output["tool_calls"]
                
                yield StreamChunk(
                    content=delta,
                    delta=delta,
                    model=model,
                    provider=self.provider_name,
                    index=output_index,
                    finish_reason=finish_reason,
                    raw_chunk=chunk_data
                )
                
                if finish_reason:
                    break
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse stream chunk: {e}")
                continue
    
    async def chat(
        self,
        messages: list,
        model: str = "qwen-plus",
        stream: bool = False,
        **kwargs
    ) -> Any:
        """
        对话接口
        
        Args:
            messages: 消息列表
            model: 模型名称
            stream: 是否流式
            **kwargs: 其他参数
        
        Returns:
            ModelResponse 或 AsyncIterator[StreamChunk]
        """
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
                        raise Exception(f"DashScope API error: {response.status} - {error_text}")
                    
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
                # 流式错误处理
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
        model: str = "text-embedding-v3",
        **kwargs
    ) -> Dict[str, Any]:
        """
        获取文本 Embedding
        
        Args:
            texts: 文本列表
            model: Embedding 模型
        
        Returns:
            包含 embeddings 的响应
        """
        url = f"{self.config.base_url.rstrip('/')}/embeddings"
        headers = self._build_headers()
        
        payload = {
            "model": model,
            "input": {"texts": texts},
            "parameters": {
                "truncate": kwargs.get("truncate", "NONE")
            }
        }
        
        try:
            response = await self._make_request(
                url, headers, payload, self.config.timeout
            )
            self._record_success()
            return response
        except Exception as e:
            self._record_failure(str(e))
            return {
                "error": str(e),
                "model": model,
                "provider": self.provider_name
            }
    
    # ==================== Token 计算 ====================
    
    @staticmethod
    def count_tokens(text: str, model: str = "qwen-plus") -> int:
        """
        估算 token 数量
        
        Note: 这是粗略估算，实际 token 数应使用 API 返回的值
        """
        # 简单估算：UTF-8 编码下，中文约 1-4 字符/token，英文约 4 字符/token
        import re
        
        # CJK 字符
        cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # 英文字母和数字
        eng_tokens = len(re.findall(r'[a-zA-Z0-9]+', text))
        
        # 其他字符
        other_chars = len(text) - cjk_chars - eng_tokens
        
        # 估算
        # 实际比例约为: 1 CJK char ≈ 1-2 tokens, 1 English word ≈ 1-1.5 tokens
        estimated = cjk_chars * 0.7 + eng_tokens * 0.25 + other_chars * 0.3
        
        return max(1, int(estimated))
    
    # ==================== 成本计算 ====================
    
    @staticmethod
    def get_pricing() -> Dict[str, Dict]:
        """获取模型定价"""
        # 参考价格 (CNY / 1M tokens)
        return {
            "qwen-max": {
                "input": 0.04,
                "output": 0.12,
                "description": "超大规模模型"
            },
            "qwen-max-longcontext": {
                "input": 0.04,
                "output": 0.12,
                "description": "超长上下文"
            },
            "qwen-plus": {
                "input": 0.004,
                "output": 0.012,
                "description": "增强版"
            },
            "qwen-turbo": {
                "input": 0.002,
                "output": 0.006,
                "description": "快速版"
            },
            "qwen-coder-plus": {
                "input": 0.008,
                "output": 0.024,
                "description": "编程增强版"
            },
            "qwen-coder": {
                "input": 0.002,
                "output": 0.006,
                "description": "编程版"
            },
            "text-embedding-v3": {
                "input": 0.0001,
                "output": 0,
                "description": "Embedding v3"
            },
        }
    
    async def close(self):
        """关闭会话"""
        if self._session and not self._session.closed:
            await self._session.close()


def create_provider(api_key: str, **kwargs) -> DashScopeProvider:
    """创建提供商实例"""
    config = ProviderConfig(
        name="dashscope",
        api_key=api_key,
        base_url=kwargs.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        timeout=kwargs.get("timeout", 60),
        extra_headers=kwargs.get("extra_headers", {})
    )
    return DashScopeProvider(config)


# 导入 time 用于 latency 计算
import time
