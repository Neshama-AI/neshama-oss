# Neshama Memory Layer

> Soul（灵魂）+ Memory（记忆）+ 关系

Neshama 是一个开源 Agent 框架，其 Memory 层为 AI Agent 提供分层记忆能力，支持多 Agent 协作与持久化存储。

## 🎯 核心理念

- **三层记忆架构**：短期 → 中期 → 长期，模拟人类记忆机制
- **开发者友好**：简洁 API，快速集成
- **开源可扩展**：支持自定义嵌入、存储后端
- **多 Agent 支持**：基于 Agent ID 的隔离存储

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/neshama-ai/memory.git
cd memory

# 安装依赖（可选）
pip install numpy pyyaml
```

## 🚀 快速开始

### 基础使用

```python
from neshama.memory import Memory

# 初始化
memory = Memory(agent_id="my_agent")

# 添加对话
memory.add_turn("user", "你好，我叫张三")
memory.add_turn("assistant", "你好张三！很高兴认识你。")
memory.add_turn("user", "我喜欢机器学习和编程")

# 获取上下文
context = memory.get_short_term_context()
print(context)
```

### 用户画像与偏好

```python
# 设置用户画像
memory.set_user_profile(
    name="张三",
    language="zh-CN",
    interests=["机器学习", "编程", "科幻"],
)

# 更新偏好
memory.update_preference("response_style", "简洁")
memory.update_preference("language", "中文")

# 隐式学习偏好（从行为推断）
memory.learn_preference("preferred_time", "morning")
```

### RAG 知识检索

```python
# 添加知识
memory.add_knowledge(
    content="Python 装饰器是在不修改原函数的情况下，为其添加额外功能的技术。",
    metadata={"category": "编程", "language": "Python"}
)

memory.add_knowledge(
    content="FastAPI 是一个现代、快速的 Python Web 框架。",
    metadata={"category": "框架", "language": "Python"}
)

# RAG 检索
rag_context = memory.retrieve("Python 装饰器是什么？")
print(rag_context.build_prompt("请解释装饰器的用途"))
```

### 完整 Agent 上下文

```python
# 获取完整上下文用于 Agent
full_context = memory.get_context(
    short_term_turns=10,
    include_rag=True,
    rag_query="用户最近在聊什么？"
)

# 或直接获取适合注入 Prompt 的字符串
prompt_context = memory.get_prompt_context()
```

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        Memory                               │
│                    (统一记忆接口)                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Short-term │  │  Medium-term│  │  Long-term  │          │
│  │  (短期记忆)  │→│  (中期记忆)  │→│  (长期记忆)  │          │
│  │             │  │             │  │             │          │
│  │ 滑动窗口    │  │ 用户画像    │  │ RAG 检索    │          │
│  │ 对话历史    │  │ 偏好习惯    │  │ 知识库      │          │
│  │ 固定容量    │  │ 增量更新    │  │ 向量嵌入    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         ↓               ↓               ↓                   │
│  ┌─────────────────────────────────────────────────┐        │
│  │                  Storage Layer                  │        │
│  │              (存储层 - 可插拔)                    │        │
│  │   FileStorage (JSON/YAML)  │  VectorStore        │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │                 Retrieval Layer                  │        │
│  │               RAG Retriever                      │        │
│  │        (多知识源 + 重排序 + 混合检索)             │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 三层记忆详解

| 层级 | 容量 | 生命周期 | 内容 | 适用场景 |
|------|------|----------|------|----------|
| **短期** | 10-50 轮 | 当前会话 | 最近对话历史 | 连续对话、上下文理解 |
| **中期** | 用户维度 | 数天-数周 | 画像、偏好、习惯 | 个性化响应、用户理解 |
| **长期** | 无限制 | 持久化 | 知识库、技能、RAG | 专业问答、知识增强 |

## 📂 项目结构

```
memory/
├── memory.py              # 主模块 - 统一入口
├── layers/                # 分层记忆
│   ├── short_term.py     # 短期记忆 - 滑动窗口
│   ├── medium_term.py     # 中期记忆 - 用户画像
│   └── long_term.py      # 长期记忆 - RAG
├── storage/               # 存储层
│   ├── file_storage.py    # 文件存储 (JSON/YAML)
│   └── vector_store.py    # 向量存储 (纯Python实现)
├── retrieval/             # 检索层
│   └── rag.py             # RAG 检索逻辑
└── README.md              # 本文档
```

## 🔧 进阶配置

### 自定义配置

```python
from neshama.memory import Memory, MemoryConfig
from neshama.memory.retrieval import RetrievalStrategy

config = MemoryConfig(
    agent_id="my_agent",
    storage_path="./my_data",
    
    # 短期记忆
    short_term_capacity=30,
    short_term_persist=True,
    
    # 长期记忆
    embedding_dim=768,  # OpenAI embeddings 维度
    
    # RAG
    rag_top_k=10,
    rag_strategy=RetrievalStrategy.HYBRID,
)

memory = Memory(config=config)
```

### 自定义嵌入函数

```python
# 使用 OpenAI 嵌入
import openai

def openai_embed(text: str):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response['data'][0]['embedding']

memory.long_term._embed_func = openai_embed
```

### 多 Agent 知识共享

```python
# Agent A 添加知识
memory_a = Memory(agent_id="agent_a")
memory_a.add_knowledge("这是 Agent A 的专业知识")

# Agent B 检索时包含 Agent A 的知识
memory_b = Memory(agent_id="agent_b")

# 注册跨 Agent 知识源
memory_b.rag.register_source("from_a", memory_a.long_term, priority=1)

# 检索
results = memory_b.retrieve("Agent A 的知识是什么？", sources=["from_a"])
```

### 持久化存储

```python
# 内存模式（不持久化）
memory = Memory(agent_id="temp")
memory.add_turn("user", "测试")

# 持久化模式
memory = Memory(
    agent_id="my_agent",
    config=MemoryConfig(storage_path="./data/agent_001")
)
```

## 🔌 与外部向量库集成

### FAISS

```python
# 未来版本支持
# from neshama.memory.storage import FAISSVectorStore

# store = FAISSVectorStore(dimension=768)
# memory = Memory(vector_store=store)
```

### Milvus / Qdrant

```python
# 使用 pymilvus
# store = MilvusStore(collection_name="neshama_kb")
```

## 📊 API 概览

### Memory 类

| 方法 | 说明 |
|------|------|
| `add_turn(role, content)` | 添加对话轮次 |
| `get_short_term_context()` | 获取短期记忆上下文 |
| `set_user_profile()` | 设置用户画像 |
| `update_preference()` | 更新用户偏好 |
| `add_knowledge()` | 添加知识 |
| `retrieve()` | RAG 检索 |
| `get_context()` | 获取完整上下文 |
| `get_prompt_context()` | 获取适合 Prompt 的上下文 |

### 存储层

| 类 | 说明 |
|---|---|
| `FileStorage` | JSON/YAML 文件存储 |
| `VectorStore` | 纯 Python 向量存储 |
| `HybridVectorStore` | 多字段混合向量存储 |

### 检索层

| 类 | 说明 |
|---|---|
| `RAGRetriever` | RAG 检索器 |
| `RetrievalStrategy` | 检索策略枚举 |

## 🧪 示例

### 对话 Agent

```python
from neshama.memory import Memory

memory = Memory(agent_id="assistant")

def chat(user_input: str) -> str:
    # 1. 添加用户消息
    memory.add_turn("user", user_input)
    
    # 2. 获取上下文
    context = memory.get_prompt_context()
    
    # 3. 调用 LLM（伪代码）
    prompt = f"{context}\nUser: {user_input}\nAssistant:"
    response = llm.generate(prompt)
    
    # 4. 保存助手回复
    memory.add_turn("assistant", response)
    
    return response
```

### RAG 问答系统

```python
memory = Memory(agent_id="qa_system")

# 导入知识库
docs = [
    ("Neshama 是一个 AI Agent 框架。", {"source": "官网"}),
    ("Memory 层提供三层记忆能力。", {"source": "文档"}),
]
for content, meta in docs:
    memory.add_knowledge(content, meta)

# 问答
query = "Neshama 是什么？"
rag_context = memory.retrieve(query, top_k=3)
prompt = rag_context.build_prompt(query)
answer = llm.generate(prompt)
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 License

MIT License

---

> *Built with ❤️ by the Neshama Community*
