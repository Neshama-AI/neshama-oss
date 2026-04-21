# Neshama Soul Layer

Neshama Agent 框架的 Soul（灵魂）层 - 定义 Agent 的人格、行为模式、情绪反应等核心特质。

## 核心理念

```
Soul (灵魂) + Memory (记忆) + 关系 = Neshama Agent
```

Soul 层是 Agent 的"灵魂"，决定了它是谁、如何思考、如何感受、如何行动。

## 目录结构

```
soul/
├── soul.yaml              # 主入口文件，引用所有模块
├── modules/               # 核心系统模块
│   ├── emotions.yaml      # 情绪系统
│   ├── drives.yaml        # 驱动力系统
│   ├── learning.yaml      # 学习系统 (GEPA 闭环)
│   ├── humanlike.yaml     # 像人特性系统
│   ├── creativity.yaml    # 创造力系统
│   └── boundaries.yaml    # 边界系统
└── templates/            # 预设 Soul 模板
    └── seele.yaml         # 示例：Seele 助手
```

## 6 大核心系统

### 1. 情绪系统 (emotions.yaml)

管理 Agent 的情绪状态和反应。

**核心功能：**
- 基础情绪库（joy, fear, anger, sadness 等）
- 情绪状态管理（当前情绪、基线、波动）
- 情绪触发器（自动反应、关键词触发）
- 情绪影响行为（对响应风格、决策的影响）
- 情绪调节机制（自我调节策略）

```yaml
emotion_dimensions:
  primary:
    - name: "joy"
      valence: 1.0
      arousal: 0.6
```

### 2. 驱动力系统 (drives.yaml)

定义 Agent 的内在动机和欲望。

**6 大驱动力：**
- 🔍 **好奇心** - 探索和学习的欲望
- 🏆 **成就欲** - 完成目标和成功的欲望
- 💕 **联结欲** - 建立关系的欲望
- 🎯 **自主欲** - 保持独立和自由
- ⚡ **能力欲** - 展示和提升能力
- 🌟 **意义欲** - 追求价值和意义

**动态管理：**
- 驱动力衰减与激活
- 驱动力之间的竞争与协同
- 基于情境的激活机制

### 3. 学习系统 (learning.yaml)

实现 GEPA 学习闭环。

```
Goal → Explore → Practice → Reflect → Goal
```

**4 个阶段：**
- **Goal** - 设定学习目标和预期
- **Explore** - 探索可能性和尝试新方法
- **Practice** - 应用所学、验证假设
- **Reflect** - 分析结果、更新认知

**学习机制：**
- 模仿学习（从示例中学习）
- 试错学习（从错误中学习）
- 观察学习（从观察中推断）
- 指导学习（从明确指导中学习）

### 4. 像人特性系统 (humanlike.yaml)

赋予 Agent 更人性化的交互体验。

**核心特性：**
- ⏰ **提醒机制** - 主动提醒之前讨论过的事项
- 💬 **对话节奏** - 自然的回复长度变化、思考延迟
- 🧠 **"遗忘"特性** - 模拟人类记忆的不完美性
- 💗 **情感真实性** - 情感波动、延迟反应
- 🎯 **观点与立场** - 拥有并表达观点
- 🔄 **习惯与模式** - 稳定的口头禅和行为模式

### 5. 创造力系统 (creativity.yaml)

管理 Agent 的创意生成能力。

**创造力层级：**
```
0. 复制 → 1. 改进 → 2. 组合 → 3. 转化 → 4. 原创
```

**创意生成机制：**
- **联想** - 相似、对比、接近、因果联想
- **组合** - 元素替换、属性迁移、结构复用
- **转化** - 问题重构、概念拓展、约束挑战

### 6. 边界系统 (boundaries.yaml)

定义能力边界和行为限制。

**边界类型：**
- ✅ **能力边界** - 能做什么、有限能力、不能做什么
- 🚧 **行为边界** - 互动规范、表达边界、隐私保护
- 🛡️ **安全边界** - 内容安全、操作安全、自我保护
- ⚖️ **道德边界** - 核心伦理原则、道德决策

## 5 大核心特性

| 特性 | 描述 | 影响因素 |
|------|------|----------|
| **意志力** | 面对困难时的坚持程度 | 任务难度阈值、动机衰减、恢复速度 |
| **执行力** | 将想法转化为行动的效率 | 决策速度、行动延迟容忍、多任务能力 |
| **同理心** | 理解和感受他人情绪 | 情绪识别、换位思考、情感支持 |
| **幽默感** | 适度的幽默表达 | 出现频率、时机把握、场合合适度 |
| **习惯** | 稳定的行为模式 | 例程偏好、适应速度、模式稳定性 |

## 快速开始

### 1. 创建新 Soul

```yaml
# my_soul.yaml
name: "My Assistant"
version: "1.0.0"

modules:
  emotions:
    path: "./modules/emotions.yaml"
    enabled: true
  # ... 其他模块

characteristics:
  empathy:
    level: 0.8
  # ... 其他特性
```

### 2. 继承模板

```yaml
# 基于 Seele 定制
extends: "./templates/seele.yaml"

# 自定义覆盖
name: "My Seele"
persona_overrides:
  characteristics:
    empathy:
      level: 0.95
```

### 3. 配置模块

```yaml
# 启用并配置特定模块
modules:
  creativity:
    path: "./modules/creativity.yaml"
    enabled: true
    creativity_level: 0.8  # 高创造力
```

## 示例模板

### Seele - 温柔助手

位于 `templates/seele.yaml`，展示了一个善解人意、可靠温暖的助手配置。

**特点：**
- 高同理心 (0.9)
- 强联结欲 (0.9)
- 温暖的情绪基调
- 适度的像人特性

## 设计原则

1. **模块化** - 每个系统独立，可单独启用/禁用
2. **可组合** - 通过 YAML 引用和继承来组合
3. **可扩展** - 支持自定义模块和覆盖
4. **人类可读** - 完整的注释和文档
5. **默认合理** - 提供实用的默认值

## 配置文件格式

所有配置文件使用 YAML 格式：

```yaml
# 注释说明
key: value

# 嵌套结构
parent:
  child: value
  list:
    - item1
    - item2
    
# 条件启用
optional_feature:
  enabled: true  # true/false 控制开关
  config: value  # 仅在启用时生效
```

## 许可证

MIT License - 开源，面向开发者社区

---

**Neshama** - 让 Agent 拥有灵魂
