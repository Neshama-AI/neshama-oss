# Neshama Core Examples

Neshama 核心对话引擎的示例代码。

## 目录

- [基础对话示例](#基础对话示例-basic_chatpy)
- [Soul 配置示例](#soul-配置示例-soul_chatpy)

---

## 基础对话示例 (basic_chat.py)

最简单的 Neshama Engine 使用示例。

### 功能

- 基础单轮对话
- 自定义配置
- 多轮对话
- 会话管理
- 响应详情

### 运行

```bash
cd Neshama/examples
python basic_chat.py
```

### 代码示例

```python
from Neshama.core import NeshamaEngine, EngineConfig

# 创建引擎
engine = NeshamaEngine()

# 单轮对话
response = engine.chat("你好！")
print(response.content)

# 多轮对话
session = engine.create_session(user_id="user123")
r1 = engine.chat("你好", session_id=session.id)
r2 = engine.chat("今天天气怎么样？", session_id=session.id)

# 获取引擎统计
stats = engine.get_stats()
print(stats)
```

---

## Soul 配置示例 (soul_chat.py)

演示如何使用 Soul 配置来定制 Agent 行为。

### 功能

- 使用默认 Soul 配置
- 使用自定义 Soul 配置
- 自定义系统提示词
- SoulLoader 加载配置
- Soul 与 Memory 结合使用

### 运行

```bash
cd Neshama/examples
python soul_chat.py
```

### 代码示例

#### 使用自定义 Soul

```python
from Neshama.core import NeshamaEngine

engine = NeshamaEngine()

# 自定义 Soul 配置
custom_soul = {
    "name": "Python Tutor",
    "description": "专业的Python编程导师",
    "characteristics": {
        "willpower": {"level": 0.9, "description": "耐心指导学生"},
        "humor": {"level": 0.3, "description": "适度幽默"},
    },
    "behavior_patterns": {
        "response_style": {
            "verbosity": "detailed",
            "formality": "semi-formal",
        }
    }
}

# 更新配置
engine.update_soul(custom_soul)

# 对话
response = engine.chat("变量是什么？")
```

#### 使用 SoulLoader

```python
from Neshama.core import NeshamaEngine
from Neshama.soul import SoulLoader, SoulLoaderConfig

# 创建 Loader
loader_config = SoulLoaderConfig(
    config_dir="./Neshama/soul",
    default_config_name="soul.yaml"
)
loader = SoulLoader(config=loader_config)
soul_config = loader.load()

# 创建引擎
engine = NeshamaEngine(soul_loader=loader)
```

#### 自定义系统提示词

```python
from Neshama.core import NeshamaEngine, EngineConfig

config = EngineConfig(
    system_prompt="""你是一个创意写作助手。
    - 语言优美，富有诗意
    - 善于使用比喻和修辞
    - 保持神秘感和想象力""",
    temperature=0.9
)

engine = NeshamaEngine(config=config)
response = engine.chat("写一首关于秋天的诗")
```

---

## Soul 配置文件格式

Soul 配置文件使用 YAML 格式：

```yaml
# 基本信息
name: "My Soul"
version: "1.0.0"
description: "描述"

# 人格特性
characteristics:
  willpower:
    level: 0.7
    description: "面对困难时的坚持程度"
  
  empathy:
    level: 0.8
    description: "理解用户情感的能力"

# 行为模式
behavior_patterns:
  response_style:
    verbosity: "moderate"  # brief | moderate | detailed
    formality: "casual"    # formal | semi-formal | casual

# 语言风格
language:
  tone: "friendly"
  use_emoji: false
```

---

## 注意事项

1. **首次运行**：首次运行会自动创建内存存储目录
2. **API 配置**：如果没有配置 API key，会自动使用模拟响应模式
3. **调试模式**：设置 `debug=True` 可以查看详细日志

---

## 下一步

- 查看 [../core/engine.py](../core/engine.py) 了解引擎 API
- 查看 [../core/conversation.py](../core/conversation.py) 了解会话管理
- 查看 [../configs/default_soul.yaml](../configs/default_soul.yaml) 了解配置格式
- 查看 [../tests/test_engine.py](../tests/test_engine.py) 了解测试用例
