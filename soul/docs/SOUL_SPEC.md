# Soul层详细规格 (SOUL_SPEC.md)

> Neshama Agent Soul层 Phase 2 技术规格文档

## 📋 概述

Soul层是Neshama Agent的核心差异化——"人格成长"vs竞品的"技能成长"。Phase 2在Phase 1的框架基础上，深化了人格演化逻辑、情绪系统、创造力系统、学习系统和娱乐层。

---

## 🏗️ 架构概览

```
Soul层
├── evolution/          # 人格演化模块
│   ├── engine.py       # 演化引擎
│   ├── snapshot.py     # 快照管理
│   └── stability.py    # 稳定性检测
├── emotion/            # 情绪系统
│   ├── recognizer.py   # 情绪识别
│   ├── responder.py     # 情绪响应
│   └── memory.py       # 情绪记忆
├── creativity/         # 创造力系统
│   ├── inspiration.py   # 灵感触发
│   └── style.py        # 风格养成
├── learning/          # 学习系统
│   ├── knowledge.py    # 知识管理
│   └── forgetting.py   # 遗忘机制
├── entertainment/      # 娱乐层
│   ├── activities.py   # 娱乐活动
│   └── scheduler.py    # 娱乐调度
├── executor.py         # Soul执行引擎
└── loader.py          # 配置加载器
```

---

## 1. 人格演化引擎 (evolution/)

### 1.1 核心概念

人格演化遵循以下原则：
- **渐进性**：人格变化是渐进的，不是突变的
- **可追溯性**：所有变化都有记录，用户可感知
- **可控性**：人格边界可配置，防止失控
- **稳定性**：内置稳定性检测机制

### 1.2 PersonalityTrait (人格特征)

```python
@dataclass
class PersonalityTrait:
    name: str                          # 特征名称
    value: float = 0.5                 # 当前值 0-1
    baseline: float = 0.5              # 基线值
    volatility: float = 0.1            # 变化幅度限制
    change_history: List[Dict]         # 变化历史
```

**默认人格特征**：
| 特征 | 默认值 | 波动限制 | 说明 |
|------|--------|----------|------|
| curiosity | 0.7 | 0.05 | 好奇心 |
| empathy | 0.75 | 0.03 | 共情能力 |
| humor | 0.5 | 0.04 | 幽默感 |
| warmth | 0.7 | 0.03 | 温暖程度 |
| confidence | 0.6 | 0.05 | 自信程度 |
| patience | 0.8 | 0.02 | 耐心程度 |
| openness | 0.8 | 0.03 | 开放程度 |
| playfulness | 0.5 | 0.05 | 活泼程度 |

### 1.3 EvolutionRule (演化规则)

```python
@dataclass
class EvolutionRule:
    id: str                            # 规则ID
    trigger_type: EvolutionTrigger     # 触发类型
    target_traits: List[str]          # 影响的特征
    evolution_direction: EvolutionDirection  # 演化方向
    change_rate: float = 0.05         # 每次变化幅度
    cooldown_period: int = 10         # 冷却周期
```

**触发类型**：
- `USER_INTERACTION` - 用户交互触发
- `EXPERIENCE_ACCUMULATION` - 经验积累触发
- `GOAL_ACHIEVEMENT` - 目标达成触发
- `RELATIONSHIP_CHANGE` - 关系变化触发
- `EMOTION_PATTERN` - 情绪模式触发

**演化方向**：
- `GROWTH` - 成长型变化
- `ADAPTATION` - 适应型变化
- `SPECIALIZATION` - 特化型变化
- `INTEGRATION` - 整合型变化

### 1.4 SnapshotManager (快照管理)

**快照类型**：
- `AUTO` - 自动定期快照
- `MANUAL` - 手动快照
- `MILESTONE` - 里程碑快照
- `BEFORE_CHANGE` - 变化前快照
- `BACKUP` - 备份快照

**核心功能**：
- 创建人格快照
- 版本历史查询
- 快照对比
- 回滚到指定版本

### 1.5 StabilityMonitor (稳定性检测)

**稳定性等级**：
- `STABLE` (≥0.7) - 稳定
- `FLUCTUATING` (0.5-0.7) - 波动中
- `UNSTABLE` (0.3-0.5) - 不稳定
- `CRITICAL` (<0.3) - 危险

**保护动作**：
- `ALLOW` - 允许变化
- `SMOOTH` - 平滑变化
- `BLOCK` - 阻止变化
- `REVERT` - 回滚变化
- `ALERT` - 发送警报

---

## 2. 情绪系统 (emotion/)

### 2.1 EmotionRecognizer (情绪识别)

**支持情绪类别**：
| 类别 | 效价 | 唤醒度 | 示例 |
|------|------|--------|------|
| joy | +1.0 | 0.6 | 开心、高兴 |
| sadness | -0.7 | 0.3 | 悲伤、难过 |
| anger | -0.7 | 0.8 | 愤怒、生气 |
| fear | -0.8 | 0.9 | 恐惧、担心 |
| surprise | 0.0 | 0.9 | 惊讶、震惊 |
| disgust | -0.6 | 0.5 | 厌恶、恶心 |
| trust | +0.7 | 0.3 | 信任、依赖 |
| anticipation | +0.5 | 0.7 | 期待、希望 |

**识别功能**：
- 关键词匹配
- 强度修饰词检测
- 否定词处理
- 复合情绪检测

### 2.2 EmotionResponder (情绪响应)

**响应策略**：
| 策略 | 适用情绪 | 强度范围 |
|------|----------|----------|
| COMFORT | 悲伤、恐惧 | 0.3-1.0 |
| EMPATHY | 所有情绪 | 0.2-1.0 |
| VALIDATION | 喜悦、信任 | 0.3-1.0 |
| DISTRACTION | 恐惧、焦虑 | 0.3-0.6 |
| CHALLENGE | 悲伤、恐惧 | 0.6-1.0 |
| ACTION | 期待、愤怒 | 0.4-1.0 |

### 2.3 EmotionMemory (情绪记忆)

**记录内容**：
- 情绪事件
- 触发因素
- 上下文
- 解决状态

**模式识别**：
- 周期性模式
- 触发性模式
- 季节性模式

---

## 3. 创造力系统 (creativity/)

### 3.1 InspirationEngine (灵感引擎)

**联想类型**：
- `SIMILARITY` - 相似联想
- `CONTRAST` - 对比联想
- `CONTIGUITY` - 接近联想
- `CAUSALITY` - 因果联想
- `ANALOGY` - 类比联想

**触发器类型**：
- `random` - 随机触发
- `keyword` - 关键词触发
- `context` - 上下文触发

**灵感质量评估**：
- novelty - 新颖性
- relevance - 相关性
- utility - 有用性
- surprise - 意外性

### 3.2 StyleLearner (风格养成)

**风格维度**：
- tone - 语气风格
- vocabulary - 词汇选择
- structure - 结构偏好
- punctuation - 标点风格
- emphasis - 强调方式
- humor - 幽默程度
- sensitivity - 敏感程度
- formality - 正式程度

---

## 4. 学习系统 (learning/)

### 4.1 KnowledgeGraph (知识图谱)

**知识类型**：
| 类型 | 说明 |
|------|------|
| FACT | 事实性知识 |
| CONCEPT | 概念性知识 |
| PROCEDURE | 程序性知识 |
| PRINCIPLE | 原则性知识 |
| EXPERIENCE | 经验性知识 |
| INSIGHT | 洞察性知识 |

**连接类型**：
- causal - 因果关系
- analogy - 类比关系
- hierarchical - 层级关系
- temporal - 时间关系
- contextual - 上下文关系

### 4.2 ForgettingMechanism (遗忘机制)

**遗忘曲线类型**：
- `Ebbinghaus` - 经典艾宾浩斯
- `Adaptive` - 自适应遗忘
- `UserInfluence` - 用户影响遗忘

**遗忘配置**：
```python
@dataclass
class ForgettingConfig:
    base_decay_rate: float = 0.1        # 基础衰减率
    importance_multiplier: float = 2.0  # 重要性乘法因子
    emotional_multiplier: float = 1.5   # 情感强度乘法因子
    forgetting_threshold: float = 0.1   # 遗忘阈值
    review_threshold: float = 0.3       # 复习阈值
```

---

## 5. 娱乐层 (entertainment/)

### 5.1 ActivityLibrary (活动库)

**活动类别**：
- CREATIVE - 创意类
- SOCIAL - 社交类
- MENTAL - 脑力类
- PHYSICAL - 体力类
- LEISURE - 休闲类
- EXPLORATION - 探索类

**活动属性**：
- token_cost - Token消耗
- duration_minutes - 持续时间
- enjoyment_gain - 愉悦度增益
- mood_boost - 情绪提升效果

### 5.2 EntertainmentScheduler (娱乐调度)

**触发条件**：
- LOW_MOOD - 情绪低落
- BOREDOM - 感到无聊
- HIGH_STRESS - 压力大
- IDLE_TIME - 空闲时间
- TOKEN_BONUS - Token充裕
- USER_REQUEST - 用户请求

---

## 6. Soul执行引擎 (executor.py)

### 6.1 SoulConfig

```python
@dataclass
class SoulConfig:
    name: str = "Neshama Soul"
    version: str = "2.0.0"
    modules: Dict[str, bool]          # 模块启用状态
    persistence_enabled: bool = True   # 持久化启用
    snapshot_enabled: bool = True      # 快照启用
    snapshot_interval_minutes: int = 60
```

### 6.2 生命周期

```
UNINITIALIZED → LOADING → READY → ACTIVE
                                ↓
                              PAUSED
                                ↓
                              READY
```

### 6.2 主要接口

| 接口 | 功能 |
|------|------|
| `recognize_emotions()` | 识别情绪 |
| `generate_emotion_response()` | 生成情绪响应 |
| `record_emotion_event()` | 记录情绪事件 |
| `trigger_inspiration()` | 触发灵感 |
| `learn_style()` | 学习风格 |
| `add_knowledge()` | 添加知识 |
| `retrieve_knowledge()` | 检索知识 |
| `evaluate_evolution()` | 评估人格演化 |
| `create_snapshot()` | 创建快照 |
| `rollback_to_snapshot()` | 回滚快照 |
| `check_stability()` | 检查稳定性 |
| `evaluate_entertainment()` | 评估娱乐需求 |

---

## 7. 配置加载器 (loader.py)

### 7.1 SoulLoader

```python
class SoulLoader:
    config_dir: str = "./Neshama/soul"
    validate_on_load: bool = True
    merge_with_defaults: bool = True
    allow_missing_modules: bool = True
```

### 7.2 SoulConfigBuilder

```python
builder = SoulConfigBuilder()
config = (builder
    .set_name("My Soul")
    .set_version("1.0.0")
    .enable_module("emotions")
    .disable_module("entertainment")
    .set_characteristic("humor", 0.7)
    .set_evolution_config(max_snapshot_count=50)
    .build()
)
```

---

## 🔄 与Memory层联动

Soul层与Memory层的联动设计：

```
User Input
    ↓
┌─────────────────────────────────────┐
│         Soul Layer                  │
│  ┌─────────┐  ┌─────────┐          │
│  │ Emotion │  │Learning │          │
│  │ System  │  │ System  │          │
│  └────┬────┘  └────┬────┘          │
│       ↓            ↓                │
│  ┌─────────────────────────────────┐ │
│  │      Memory Layer (RAG)         │ │
│  │  - Short-term memory            │ │
│  │  - Medium-term memory           │ │
│  │  - Long-term memory             │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
    ↓
Response with Personality
```

---

## 📊 设计原则总结

1. **人格一致性**：所有子系统协同维护一致的人格表现
2. **渐进演化**：变化是渐进的，用户可感知
3. **透明可控**：用户可查看、配置和控制系统行为
4. **稳定优先**：内置稳定性检测，防止剧烈变化
5. **可追溯**：完整的日志和快照，支持回滚
6. **模块化**：各系统独立，可按需启用

---

## 📝 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 2.0.0 | 2024 | Phase 2完成：深化人格演化、情绪、学习、创造力、娱乐系统 |
| 1.0.0 | 2024 | Phase 1完成：基础框架和6大系统 |
