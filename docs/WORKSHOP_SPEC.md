# Workshop 工匠认证系统规格文档

> **版本**: v1.0  
> **更新时间**: 2025年1月  
> **模块**: Neshama Workshop

---

## 目录

1. [系统概述](#1-系统概述)
2. [工匠认证体系](#2-工匠认证体系)
3. [技能审核引擎](#3-技能审核引擎)
4. [创作者经济模型](#4-创作者经济模型)
5. [发现与推荐系统](#5-发现与推荐系统)
6. [数据库模型](#6-数据库模型)
7. [API 接口](#7-api-接口)
8. [前端模板](#8-前端模板)
9. [管理命令](#9-管理命令)
10. [配置参数](#10-配置参数)

---

## 1. 系统概述

### 1.1 模块定位

Workshop 是 Neshama 的独占优势模块，提供完整的工匠认证与技能交易平台，是无竞品涉足的市场空白。

### 1.2 核心价值

- 🎯 **质量保障**: 严格的审核机制确保技能质量
- 🏆 **工匠成长**: 清晰的等级体系和晋升通道
- 💰 **经济激励**: 合理的分成比例激励创作者
- 🔍 **智能发现**: 精准的搜索和推荐算法

### 1.3 Phase 2 目标

深化核心逻辑，实现：
- 完整的工匠认证流程
- 增强的审核算法
- 创作者经济体系
- 智能发现推荐

---

## 2. 工匠认证体系

### 2.1 等级体系

| 等级 | 名称 | 晋升条件 | 特权等级 |
|------|------|----------|----------|
| novice | 新手工匠 | 默认 | 基础 |
| skilled | 熟练工匠 | 3技能 + 50安装 + 4.0评分 | 标准 |
| master | 大师工匠 | 10技能 + 500安装 + 4.5评分 | 高级 |
| legend | 传奇工匠 | 30技能 + 5000安装 + 4.8评分 | 顶级 |

### 2.2 晋升规则

#### 自动晋升检查

```python
# 晋升条件（可配置）
REQUIREMENTS = {
    'skilled': {
        'min_skills': 3,
        'min_installs': 50,
        'min_rating': 4.0,
        'min_active_days': 30,
    },
    'master': {
        'min_skills': 10,
        'min_installs': 500,
        'min_rating': 4.5,
        'min_active_days': 90,
        'badges_required': ['quality_certified'],
    },
    'legend': {
        'min_skills': 30,
        'min_installs': 5000,
        'min_rating': 4.8,
        'min_revenue': 10000.0,
        'min_active_days': 365,
        'badges_required': ['quality_certified', 'innovation_award', 'top_seller'],
    },
}
```

#### 人工调整

管理员可手动调整工匠等级：
- 特殊情况晋升（如贡献突出）
- 降级处理（如违规）
- 封禁处理（如严重违规）

### 2.3 特权体系

| 特权项 | 新手 | 熟练 | 大师 | 传奇 |
|--------|------|------|------|------|
| 最大技能数 | 5 | 20 | 100 | ∞ |
| 可变现 | ❌ | ✅ | ✅ | ✅ |
| 分成比例 | 70% | 65% | 60% | 55% |
| 精选位置 | 0 | 1 | 3 | 5 |
| 高级分析 | ❌ | ❌ | ✅ | ✅ |
| 优先支持 | ❌ | ❌ | ✅ | ✅ |
| 自定义品牌 | ❌ | ❌ | ✅ | ✅ |
| Beta 功能 | ❌ | ❌ | ❌ | ✅ |

### 2.4 惩戒机制

| 惩罚类型 | 说明 | 影响 |
|----------|------|------|
| warning | 警告 | 记录 |
| score_deduction | 扣分 | 信誉分-10 |
| demotion | 降级 | 降一级 |
| suspension | 暂停 | 暂时禁用 |
| ban | 封禁 | 完全禁用 |

---

## 3. 技能审核引擎

### 3.1 审核流程

```
提交审核 → 自动化扫描 → 合规检查 → 质量评分 → 决策
                ↓                        ↓
            发现问题 ──────────────────→ 人工复审
```

### 3.2 安全扫描

#### 扫描项目

| 检查类型 | 风险等级 | 说明 |
|----------|----------|------|
| sql_injection | 高 | SQL 注入风险 |
| command_injection | 高 | 命令注入风险 |
| xss_risk | 中 | XSS 攻击风险 |
| sensitive_leak | 低 | 敏感信息泄露 |
| obfuscation | 中 | 代码混淆检测 |
| network_ops | 低 | 网络操作检测 |

#### 危险代码模式

```python
DANGEROUS_PATTERNS = {
    'sql_injection': [
        r'execute\s*\(\s*["\'].*%.*["\']',
        r'cursor\.execute\s*\(\s*[^\)]*\%[^\)]*\)',
    ],
    'command_injection': [
        r'os\.system\s*\(',
        r'subprocess\.call\s*\(',
        r'eval\s*\(',
        r'exec\s*\(',
    ],
    'malicious': [
        r'__import__\s*\([\'"]os[\'"]',
    ],
}
```

### 3.3 内容合规

#### 合规检查项

| 检查项 | 状态 | 说明 |
|--------|------|------|
| sensitive_content | 敏感词 | 违规直接拒绝 |
| brand_usage | 品牌词 | 警告需授权 |
| contact_info | 联系方式 | 建议移除 |
| duplicate_content | 重复内容 | 需人工确认 |
| description_quality | 描述质量 | 影响评分 |

### 3.4 质量评分

#### 评分维度

```python
DEFAULT_WEIGHTS = {
    'code_quality': 0.30,      # 代码质量
    'security': 0.25,          # 安全性
    'completeness': 0.20,      # 完整性
    'documentation': 0.15,      # 文档
    'user_experience': 0.10,   # 用户体验
}
```

#### 评分计算

总分 = 代码质量×0.30 + 安全性×0.25 + 完整性×0.20 + 文档×0.15 + 用户体验×0.10

### 3.5 审核队列

#### 优先级计算

| 因素 | 权重 | 说明 |
|------|------|------|
| 等待时间 | 40% | 超过72小时+40分 |
| 创作者等级 | 20% | 传奇+20，大师+15 |
| 历史评分 | 15% | 4.5以上+15 |
| 首次提交 | 10% | 新手首次+10 |
| 专业匹配 | 10% | 审核员专长匹配 |
| 付费技能 | 15% | 付费技能优先 |
| 敏感标记 | 25% | 含敏感词优先 |

---

## 4. 创作者经济模型

### 4.1 收入结构

```
总收入 = 安装量 × 单价
净收入 = 总收入 × (1 - 平台抽成)
平台收入 = 总收入 × 平台抽成
```

### 4.2 分成比例

| 等级 | 工匠分成 | 平台抽成 |
|------|----------|----------|
| 新手 | 70% | 30% |
| 熟练 | 65% | 35% |
| 大师 | 60% | 40% |
| 传奇 | 55% | 45% |

### 4.3 提现规则

| 项目 | 规则 |
|------|------|
| 最低提现金额 | 10元 |
| 手续费率 | 1% (最低1元) |
| 处理周期 | 1-3个工作日 |
| 支付方式 | 支付宝/微信/银行卡 |

### 4.4 排行榜

| 榜单类型 | 计算方式 | 时间范围 |
|----------|----------|----------|
| 安装量榜 | 安装总量 | 周/月/总 |
| 收入榜 | 收入金额 | 周/月/总 |
| 评分榜 | 平均评分 | 周/月/总 |
| 质量榜 | 综合评分 | 周/月/总 |
| 新锐榜 | 新工匠表现 | 30天注册 |

---

## 5. 发现与推荐系统

### 5.1 搜索算法

#### 相关性计算

```python
WEIGHTS = {
    'name_match': 3.0,       # 名称匹配
    'tag_match': 2.0,        # 标签匹配
    'desc_match': 1.0,       # 描述匹配
    'rating_boost': 0.1,    # 评分加成
    'install_boost': 0.0001, # 安装量加成
}
```

### 5.2 推荐策略

| 推荐类型 | 说明 | 数据源 |
|----------|------|--------|
| popular | 热门推荐 | 综合热度 |
| similar | 相似推荐 | 分类+标签 |
| personalized | 个性化 | 用户行为 |
| trending | 趋势推荐 | 增长率 |
| new | 新品推荐 | 发布时间 |
| curated | 编辑精选 | 精选标记 |

### 5.3 技能对比

对比维度：
- 用户评分
- 安装量
- 价格
- 更新频率
- 文档完整性
- 支持质量

---

## 6. 数据库模型

### 6.1 核心模型

| 模型名 | 表名 | 说明 |
|--------|------|------|
| SkillCategory | workshop_category | 技能分类 |
| CreatorProfile | workshop_creator | 创作者档案 |
| Skill | workshop_skill | 技能 |
| SkillVersion | workshop_skill_version | 技能版本 |
| Rating | workshop_rating | 评分 |
| InstallRecord | workshop_install_record | 安装记录 |

### 6.2 Phase 2 新增模型

| 模型名 | 表名 | 说明 |
|--------|------|------|
| CraftsmanApplication | workshop_craftsman_application | 认证申请 |
| CraftsmanBadge | workshop_craftsman_badge | 徽章定义 |
| CraftsmanBadgeEarned | workshop_badge_earned | 徽章获得 |
| CraftsmanPunishment | workshop_craftsman_punishment | 惩戒记录 |
| LevelUpHistory | workshop_level_history | 等级变动 |
| Invitation | workshop_invitation | 邀请关系 |
| SkillChallenge | workshop_skill_challenge | 挑战赛 |
| ChallengeEntry | workshop_challenge_entry | 参赛记录 |
| RevenueRecord | workshop_revenue_record | 收入记录 |
| WithdrawRequest | workshop_withdraw_request | 提现申请 |
| Balance | workshop_balance | 余额 |
| BalanceChange | workshop_balance_change | 余额变动 |

---

## 7. API 接口

### 7.1 技能相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/workshop/skills/` | GET | 技能列表 |
| `/api/workshop/skills/` | POST | 创建技能 |
| `/api/workshop/skills/{slug}/` | GET | 技能详情 |
| `/api/workshop/skills/{slug}/submit_review/` | POST | 提交审核 |
| `/api/workshop/skills/{slug}/install/` | POST | 安装技能 |
| `/api/workshop/skills/{slug}/rate/` | POST | 评分 |
| `/api/workshop/skills/compare/` | GET | 技能对比 |

### 7.2 工匠相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/workshop/craftsmen/` | GET | 工匠列表 |
| `/api/workshop/craftsmen/{id}/` | GET | 工匠详情 |
| `/api/workshop/craftsmen/{id}/apply/` | POST | 申请认证 |
| `/api/workshop/craftsmen/{id}/badges/` | GET | 徽章列表 |
| `/api/workshop/craftsmen/{id}/promote/` | POST | 晋升(管理员) |

### 7.3 排行榜

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/workshop/leaderboard/` | GET | 排行榜 |
| `/api/workshop/leaderboard/installs/` | GET | 安装量榜 |
| `/api/workshop/leaderboard/revenue/` | GET | 收入榜 |
| `/api/workshop/leaderboard/rating/` | GET | 评分榜 |

### 7.4 发现推荐

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/workshop/discover/` | GET | 发现页 |
| `/api/workshop/recommend/` | GET | 推荐列表 |
| `/api/workshop/search/` | GET | 搜索技能 |

---

## 8. 前端模板

### 8.1 模板文件

| 文件 | 说明 |
|------|------|
| `craftsman_profile.html` | 工匠主页 |
| `skill_compare.html` | 技能对比页 |
| `leaderboard.html` | 排行榜页 |
| `submit_skill.html` | 技能提交向导 |

### 8.2 设计规范

- 渐变色主题：#667eea → #764ba2
- 卡片圆角：12-16px
- 阴影：0 4px 15px rgba(0,0,0,0.08)
- 动画：0.3s ease transition

---

## 9. 管理命令

### 9.1 check_craftsman_levels

```bash
# 检查所有工匠等级
python manage.py check_craftsman_levels

# 仅显示待晋升（不执行）
python manage.py check_craftsman_levels --dry-run

# 只检查特定等级
python manage.py check_craftsman_levels --level=skilled
```

### 9.2 process_review_queue

```bash
# 处理审核队列
python manage.py process_review_queue

# 只显示队列
python manage.py process_review_queue --show-queue

# 自动批准通过
python manage.py process_review_queue --auto-approve

# 指定审核员
python manage.py process_review_queue --reviewer=admin
```

---

## 10. 配置参数

### 10.1 Django 设置

```python
# settings.py
WORKSHOP = {
    'COMMISSION_RATES': {
        'novice': 0.30,
        'skilled': 0.35,
        'master': 0.40,
        'legend': 0.45,
    },
    'MIN_WITHDRAW_AMOUNT': 10.00,
    'WITHDRAW_FEE_RATE': 0.01,
    'LEVEL_CHECK_INTERVAL': 86400,  # 24小时
    'REVIEW_QUEUE_CACHE': 3600,      # 1小时
}
```

### 10.2 缓存配置

| 缓存键 | 超时 | 说明 |
|--------|------|------|
| workshop_leaderboard_* | 3600s | 排行榜缓存 |
| workshop_recommend_* | 1800s | 推荐缓存 |
| workshop_search_* | 600s | 搜索缓存 |

---

## 附录

### A. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2025-01 | Phase 2 完成 |

### B. TODO

- [ ] 集成真实支付接口
- [ ] 实现 Token 经济体系
- [ ] 添加数据分析后台
- [ ] 开发移动端适配

### C. 参考资料

- APP Store 审核指南
- Google Play 开发者政策
- 支付宝/微信支付文档

---

*文档结束*
