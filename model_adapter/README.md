# Neshama Model Adapter Layer

## 概述

Neshama Model Adapter Layer 是 Neshama 开源 Agent 框架的模型接入层，提供统一的模型调用接口，支持多模型切换、负载均衡和灵活配置。

**核心理念**: Soul (灵魂) + Memory (记忆) + 关系

## 特性

- 🔌 **统一接口**: 所有模型通过统一的 `call()` 方法调用
- 🔄 **多模型支持**: 支持 10+ 主流模型提供商
- ⚖️ **负载均衡**: 多种路由策略 (优先级/轮询/加权/故障转移)
- 🔧 **灵活配置**: YAML 配置管理，支持环境变量
- 📊 **统一响应格式**: 标准化的 `ModelResponse` 格式
- 🔒 **安全**: API Key 通过环境变量或配置文件管理

## 支持的模型

### Tier 1 - 低价/试用优先
| 提供商 | 模型 | 说明 |
|--------|------|------|
| 阿里云百炼 | 通义千问 | qwen-plus, qwen-turbo, qwen-max |
| 火山引擎方舟 | 豆包 | doubao-pro-32k, doubao-pro-128k |
| 百度千帆 | 文心一言 | ernie-4.0, ernie-speed-128k |

### Tier 2 - 月费稳定
| 提供商 | 模型 | 说明 |
|--------|------|------|
| MiniMax | abab6-chat | 高速响应 |
| 智谱GLM | glm-4, glm-4-flash | 长上下文 |

### Tier 3 - Coding 类
| 提供商 | 模型 | 说明 |
|--------|------|------|
| Cursor | cursor-small | AI 代码助手 |
| GitHub Copilot | gpt-4 | 代码补全 |

### Tier 4 - 主流大模型
| 提供商 | 模型 | 说明 |
|--------|------|------|
| OpenAI | GPT-4, GPT-4o, GPT-3.5 | 行业标杆 |
| Anthropic | Claude 3.5, Claude 3 | 安全可靠 |
| Google | Gemini 1.5 | Google AI |
| Kimi | moonshot-v1-128k | 月之暗面 |
| 讯飞星火 | Spark 4.0 | 语音交互 |

## 安装

```bash
pip install aiohttp pyyaml
```

## 快速开始

### 1. 配置环境变量

```bash
export OPENAI_API_KEY="your-openai-key"
export DASHSCOPE_API_KEY="your-dashscope-key"
# ... 其他 API Key
```

### 2. 基本使用

```python
from model_adapter import ModelAdapter, Message, MessageRole

# 创建适配器
adapter = ModelAdapter()

# 简单对话
response = adapter.chat_sync("你好，请介绍一下你自己")
print(response.content)

# 多轮对话
messages = [
    Message(role=MessageRole.SYSTEM, content="你是一个友好的AI助手"),
    Message(role=MessageRole.USER, content="什么是机器学习？")
]
response = adapter.call_sync(messages, model="gpt-4o")
print(response.content)
```

### 3. 流式响应

```python
import asyncio

async def stream_chat():
    adapter = ModelAdapter()
    
    messages = [Message(role=MessageRole.USER, content="写一首关于春天的诗")]
    
    async for chunk in adapter.call_stream(messages, model="gpt-4o"):
        print(chunk.delta, end="", flush=True)

asyncio.run(stream_chat())
```

### 4. 指定 Provider

```python
# 直接使用指定 Provider
response = adapter.call_sync(
    messages=[Message(role=MessageRole.USER, content="Hello")],
    provider="dashscope",
    model="qwen-plus"
)
```

## 配置

### config.yaml

```yaml
version: "1.0.0"
default_model: "gpt-4o"

providers:
  openai:
    enabled: true
    api_key: "${OPENAI_API_KEY}"
    base_url: "https://api.openai.com/v1"
    timeout: 120
    models:
      - name: "gpt-4o"
        model_id: "gpt-4o"
        max_tokens: 128000
        temperature: 0.7
        priority: 50

  dashscope:
    enabled: true
    api_key: "${DASHSCOPE_API_KEY}"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    timeout: 60
    models:
      - name: "qwen-plus"
        model_id: "qwen-plus"
        max_tokens: 8192
        temperature: 0.7
        priority: 10

router:
  strategy: "priority"        # priority | round_robin | weighted | failover
  failover_enabled: true
  health_check_interval: 60
  max_consecutive_failures: 3
```

### 环境变量

使用 `${ENV_VAR}` 语法引用环境变量：

```yaml
api_key: "${OPENAI_API_KEY}"
```

## API 参考

### ModelAdapter

主适配器类，提供统一的模型调用接口。

#### 方法

| 方法 | 说明 |
|------|------|
| `call(messages, model, provider, stream, **kwargs)` | 异步调用模型 |
| `call_sync(messages, model, provider, **kwargs)` | 同步调用模型 |
| `call_stream(messages, model, provider, **kwargs)` | 流式调用模型 |
| `chat(prompt, system, model, **kwargs)` | 简单对话接口 |
| `chat_sync(prompt, system, model, **kwargs)` | 同步对话接口 |

### Message

对话消息。

```python
Message(
    role=MessageRole.USER,      # system | user | assistant
    content="消息内容",
    name=None,                   # 可选的名称
    tool_calls=None             # 可选的函数调用
)
```

### ModelResponse

模型响应。

```python
response = ModelResponse(
    content="响应内容",
    model="gpt-4o",
    provider="openai",
    usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    latency_ms=150.5,
    finish_reason="stop",
    error=None
)
```

## 路由策略

### 优先级策略 (Priority)

按配置的优先级选择模型，数字越小优先级越高。

```python
from model_adapter import ModelRouter, RouterStrategy

router = ModelRouter(strategy=RouterStrategy.PRIORITY)
```

### 加权轮询 (Weighted)

根据权重分配请求。

```python
router = ModelRouter(strategy=RouterStrategy.WEIGHTED)
```

### 故障转移 (Failover)

主模型失败时自动切换到备用模型。

```python
router = ModelRouter(
    strategy=RouterStrategy.PRIORITY,
    failover_enabled=True,
    max_consecutive_failures=3
)
```

## 目录结构

```
model_adapter/
├── model_adapter.py      # 主适配器
├── config.py             # 配置管理
├── router.py             # 模型路由
├── providers/            # 模型提供商
│   ├── base.py           # 基础抽象类
│   ├── dashscope.py      # 阿里云百炼
│   ├── volcengine.py     # 火山引擎
│   ├── qianfan.py        # 百度千帆
│   ├── minimax.py        # MiniMax
│   ├── zhipu.py          # 智谱GLM
│   ├── openai.py         # OpenAI
│   ├── anthropic.py      # Anthropic
│   ├── gemini.py         # Google Gemini
│   ├── xinghuo.py        # 讯飞星火
│   └── coding/           # Coding类
│       ├── cursor.py     # Cursor
│       └── copilot.py    # GitHub Copilot
├── prompts/              # 提示词模板
└── README.md
```

## 开发

### 添加新 Provider

1. 创建新的 Provider 文件，如 `myprovider.py`
2. 继承 `BaseProvider` 类
3. 实现抽象方法：

```python
from .base import BaseProvider, ProviderConfig, Message, ModelResponse

class MyProvider(BaseProvider):
    provider_name = "myprovider"
    supported_models = ["my-model-1", "my-model-2"]
    
    def _build_headers(self) -> Dict:
        # 实现
        pass
    
    def _build_payload(self, messages, model, **kwargs) -> Dict:
        # 实现
        pass
    
    def _parse_response(self, response, model) -> ModelResponse:
        # 实现
        pass
    
    async def _make_request(self, url, headers, payload, timeout) -> Dict:
        # 实现
        pass
```

4. 在 `model_adapter.py` 中注册工厂函数

## License

MIT License - Neshama Agent Framework
