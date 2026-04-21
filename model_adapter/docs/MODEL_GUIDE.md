# Neshama 模型接入指南

## 概述

Neshama 模型接入层 Phase 2 完善了以下模型提供商的接入：

| 梯队 | 提供商 | 模型 | 优先级 |
|------|--------|------|--------|
| 第一梯队 | 百炼(阿里云) | 通义千问系列 | ⭐⭐⭐ |
| 第一梯队 | 火山引擎 | 豆包系列 | ⭐⭐⭐ |
| 第一梯队 | 百度千帆 | 文心一言系列 | ⭐⭐⭐ |
| 第二梯队 | MiniMax | 冰川系列 | ⭐⭐ |
| 第二梯队 | 智谱AI | GLM系列 | ⭐⭐ |

## 快速开始

### 1. 环境配置

```bash
# 安装依赖
pip install aiohttp pyyaml

# 设置环境变量
export DASHSCOPE_API_KEY="your-dashscope-key"
export VOLCENGINE_API_KEY="your-volcengine-key"
export QIANFAN_ACCESS_KEY="your-qianfan-access-key"
export QIANFAN_SECRET_KEY="your-qianfan-secret-key"
export MINIMAX_API_KEY="your-minimax-key"
export ZHIPU_API_KEY="your-zhipu-key"
```

### 2. 基础使用

```python
from model_adapter import ModelAdapter

# 初始化适配器
adapter = ModelAdapter()

# 对话调用
response = await adapter.chat(
    messages=[{"role": "user", "content": "你好"}],
    model="qwen-plus"
)
print(response.content)
```

### 3. 流式响应

```python
# 流式调用
async for chunk in adapter.chat(
    messages=[{"role": "user", "content": "写一首诗"}],
    model="qwen-plus",
    stream=True
):
    print(chunk.delta, end="", flush=True)
```

---

## 百炼（阿里云通义千问）

### 模型列表

| 模型ID | 描述 | 上下文 | 优先级 | 输入价格 | 输出价格 |
|--------|------|--------|--------|----------|----------|
| qwen-max | 超大规模模型 | 8K | 20 | ¥40/M | ¥120/M |
| qwen-max-longcontext | 超长上下文 | 32K | 25 | ¥40/M | ¥120/M |
| qwen-plus | 增强版 | 32K | 10 | ¥4/M | ¥12/M |
| qwen-turbo | 快速版 | 8K | 5 | ¥2/M | ¥6/M |
| qwen-coder-plus | 编程增强版 | 8K | 15 | ¥8/M | ¥24/M |
| qwen-coder | 编程版 | 8K | 12 | ¥2/M | ¥6/M |
| qwq-32b | 思考模型 | 32K | 18 | ¥4/M | ¥12/M |
| text-embedding-v3 | Embedding | 8K | 30 | ¥0.1/M | - |

### API配置

```python
from model_adapter.providers.dashscope import DashScopeProvider

provider = DashScopeProvider({
    "name": "dashscope",
    "api_key": "your-api-key",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "timeout": 60
})

# 对话
response = await provider.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model="qwen-plus"
)

# Embedding
result = await provider.embedding(
    texts=["要嵌入的文本"],
    model="text-embedding-v3"
)
```

### 特殊参数

```python
response = await provider.chat(
    messages=messages,
    model="qwen-plus",
    temperature=0.7,        # 温度
    top_p=0.8,               # Top-P采样
    top_k=50,                # Top-K采样
    repetition_penalty=1.1,  # 重复惩罚
    max_tokens=8192,         # 最大输出
    stream=False             # 是否流式
)
```

---

## 火山引擎（豆包）

### 模型列表

| 模型ID | 描述 | 上下文 | 优先级 | 输入价格 | 输出价格 |
|--------|------|--------|--------|----------|----------|
| doubao-pro-128k | 128K上下文 | 128K | 8 | ¥5/M | ¥10/M |
| doubao-pro-32k | 32K上下文 | 32K | 10 | ¥3/M | ¥6/M |
| doubao-lite-32k | 轻量版 | 32K | 5 | ¥1/M | ¥2/M |
| doubao-pro-4k | 短文本版 | 4K | 4 | ¥1/M | ¥2/M |

### API配置

```python
from model_adapter.providers.volcengine import VolcEngineProvider

provider = VolcEngineProvider({
    "name": "volcengine",
    "api_key": "your-api-key",
    "account_id": "your-account-id",  # 可选
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "timeout": 60
})

response = await provider.chat(
    messages=[{"role": "user", "content": "你好"}],
    model="doubao-pro-32k"
)
```

### 特殊参数

```python
response = await provider.chat(
    messages=messages,
    model="doubao-pro-128k",
    temperature=0.7,
    top_p=0.8,
    frequency_penalty=0.0,   # 频率惩罚
    presence_penalty=0.0,   # 存在惩罚
    stop=["\n\n"],          # 停止词
    max_tokens=32000
)
```

---

## 百度千帆（文心一言）

### 模型列表

| 模型ID | 描述 | 上下文 | 优先级 | 输入价格 | 输出价格 |
|--------|------|--------|--------|----------|----------|
| ernie-4.0-8k-latest | ERNIE 4.0最新版 | 8K | 20 | ¥120/M | ¥120/M |
| ernie-4.0-8k | ERNIE 4.0标准版 | 8K | 22 | ¥120/M | ¥120/M |
| ernie-speed-128k | 高速版128K | 128K | 5 | ¥4/M | ¥8/M |
| ernie-speed-32k | 高速版32K | 32K | 8 | ¥4/M | ¥8/M |
| ernie-3.5-8k | ERNIE 3.5 | 2K | 12 | ¥12/M | ¥12/M |
| ernie-lite-8k | 轻量版 | 2K | 4 | ¥0.8/M | ¥2/M |

### API配置

```python
from model_adapter.providers.qianfan import QianFanProvider

provider = QianFanProvider({
    "name": "qianfan",
    "api_key": "your-access-key",
    "access_key": "your-access-key",     # 必填
    "secret_key": "your-secret-key",      # 必填
    "base_url": "https://qianfan.baidubce.com/v2",
    "timeout": 60
})

response = await provider.chat(
    messages=[{"role": "user", "content": "你好"}],
    model="ernie-speed-128k"
)
```

### 认证说明

百度千帆需要使用 Access Key 和 Secret Key 进行认证：

1. 获取密钥：https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application
2. 支持 IAM 认证和 AK/SK 认证

---

## MiniMax

### 模型列表

| 模型ID | 描述 | 上下文 | 优先级 | 输入价格 | 输出价格 |
|--------|------|--------|--------|----------|----------|
| abab6.5s-chat | 增强版6.5S | 16K | 10 | ¥10/M | ¥10/M |
| abab6.5-chat | 标准版6.5 | 16K | 12 | ¥5/M | ¥5/M |
| abab5.5-chat | 5.5版本 | 8K | 8 | ¥1/M | ¥2/M |
| abab5s-chat | 5S版本 | 4K | 6 | ¥1/M | ¥1/M |
| MiniMax-Text-01 | 文本模型01 | 32K | 15 | ¥5/M | ¥15/M |

### API配置

```python
from model_adapter.providers.minimax import MiniMaxProvider

provider = MiniMaxProvider({
    "name": "minimax",
    "api_key": "your-api-key",
    "group_id": "your-group-id",  # 可选
    "base_url": "https://api.minimax.chat/v1",
    "timeout": 60
})

response = await provider.chat(
    messages=[{"role": "user", "content": "你好"}],
    model="abab6.5s-chat"
)
```

---

## 智谱AI

### 模型列表

| 模型ID | 描述 | 上下文 | 优先级 | 输入价格 | 输出价格 |
|--------|------|--------|--------|----------|----------|
| glm-4 | GLM-4标准版 | 128K | 10 | ¥100/M | ¥100/M |
| glm-4-plus | GLM-4 Plus | 128K | 12 | ¥100/M | ¥100/M |
| glm-4-flash | GLM-4 Flash | 32K | 4 | ¥1/M | ¥1/M |
| glm-4-air | GLM-4 Air | 32K | 6 | ¥1/M | ¥2/M |
| glm-4-airx | GLM-4 AirX | 32K | 8 | ¥2/M | ¥4/M |
| glm-4-long | 长文本版 | 128K | 14 | ¥30/M | ¥60/M |
| glm-4v | 视觉版 | 4K | 12 | ¥100/M | ¥100/M |
| glm-3-turbo | GLM-3 Turbo | 128K | 6 | ¥1/M | ¥1/M |
| embedding-2 | Embedding v2 | 2K | 30 | ¥0.1/M | - |

### API配置

```python
from model_adapter.providers.zhipu import ZhipuProvider

provider = ZhipuProvider({
    "name": "zhipu",
    "api_key": "your-api-key",
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "timeout": 60
})

response = await provider.chat(
    messages=[{"role": "user", "content": "你好"}],
    model="glm-4"
)

# Embedding
result = await provider.embedding(
    texts=["要嵌入的文本"],
    model="embedding-2"
)
```

---

## 模型管理

### 模型管理器

```python
from model_adapter.model_manager import ModelManager, ModelTier

# 初始化
manager = ModelManager()

# 按层级选择模型
cheap_model = manager.select_model(tier=ModelTier.TIER_1_CHEAP)
fast_model = manager.select_model(task_type="fast")
coding_model = manager.select_model(task_type="coding")

# 记录调用
await manager.record_call(
    model="qwen-plus",
    provider="dashscope",
    input_tokens=100,
    output_tokens=200,
    latency_ms=500,
    success=True
)

# 获取成本报告
cost_report = manager.get_cost_summary()
print(cost_report)
```

### 模型分组

```python
from model_adapter.model_manager import ModelGroup, ModelTier

# 创建自定义分组
group = ModelGroup(
    name="my_custom_group",
    tier=ModelTier.TIER_1_CHEAP,
    models=["qwen-turbo", "doubao-lite-32k"],
    fallback_models=["qwen-plus", "doubao-pro-32k"],
    description="我的自定义分组"
)

manager.register_group(group)
```

---

## 评测框架

### 快速评测

```python
from model_adapter.benchmark import BenchmarkSuite, BenchmarkRunner

# 创建评测套件
suite = BenchmarkSuite()

# 获取默认任务
tasks = suite.get_default_tasks("chat")

# 运行评测
runner = BenchmarkRunner()
report = await runner.run_benchmark(
    tasks=tasks,
    model="qwen-plus",
    provider=dashscope_provider
)

print(f"平均延迟: {report.avg_latency_ms}ms")
print(f"成功率: {report.success_tasks/report.total_tasks*100}%")
print(f"总成本: ¥{report.total_cost}")
```

### 自定义评测任务

```python
from model_adapter.benchmark import BenchmarkTask, TaskCategory

task = BenchmarkTask(
    name="my_test",
    category=TaskCategory.CODE,
    prompt="请写一个Python函数计算斐波那契数列",
    expected_output="包含递归或循环实现"
)

suite.add_task(task)
```

---

## 成本计算示例

```python
# 计算单次调用成本
input_tokens = 1000
output_tokens = 500

# 百炼 qwen-plus
cost = (input_tokens * 4 + output_tokens * 12) / 1_000_000
print(f"qwen-plus 成本: ¥{cost:.6f}")

# 火山引擎 doubao-pro-32k
cost = (input_tokens * 3 + output_tokens * 6) / 1_000_000
print(f"doubao-pro-32k 成本: ¥{cost:.6f}")

# 智谱 glm-4-flash
cost = (input_tokens + output_tokens) * 1 / 1_000_000
print(f"glm-4-flash 成本: ¥{cost:.6f}")
```

---

## 常见问题

### Q: 如何选择合适的模型？

**推荐策略：**

| 场景 | 推荐模型 | 原因 |
|------|----------|------|
| 日常对话 | qwen-turbo / glm-4-flash | 速度快，成本低 |
| 长文本处理 | doubao-pro-128k / glm-4-long | 大上下文 |
| 代码生成 | qwen-coder-plus | 编程优化 |
| 复杂推理 | qwen-max / ernie-4.0-8k | 能力强 |
| 成本敏感 | doubao-lite-32k / ernie-lite-8k | 价格最低 |

### Q: API 调用失败怎么办？

1. 检查网络连接
2. 验证 API Key 是否有效
3. 检查模型是否在支持列表中
4. 查看错误信息，确认是否触发了限流

### Q: 如何降低使用成本？

1. 使用轻量版模型（glm-4-flash, doubao-lite）
2. 优化 Prompt，减少输入 token
3. 设置合理的 max_tokens
4. 启用缓存机制

---

## 更新日志

### v2.0.0 (Phase 2)
- 完善百炼、火山引擎、百度千帆、MiniMax、智谱AI接入
- 新增模型管理器（分组、成本统计、监控）
- 新增评测框架
- 完善定价信息和 Token 计算
- 支持流式输出增强

### v1.0.0 (Phase 1)
- 基础接入框架完成
- 统一适配器接口
- 基础配置管理
