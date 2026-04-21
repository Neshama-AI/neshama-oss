# Workshop 技能市场模块

## 概述

Neshama Agent 项目的 Workshop（技能市场）是区别于传统插件商店的工匠认证技能交易平台。强调质量优先、审查机制和工匠等级体系。

## 核心特性

### 1. 工匠认证体系
- **等级划分**：新手 → 熟练 → 大师 → 传奇
- **升级条件**：
  - 新手 → 熟练：3个通过技能 + 50安装量 + 4.0评分
  - 熟练 → 大师：10个通过技能 + 500安装量 + 4.5评分
  - 大师 → 传奇：30个通过技能 + 5000安装量 + 4.8评分
- **认证标识**：认证工匠拥有特殊标识

### 2. 技能审核机制
- **双重审核**：自动化初审 + 人工复审
- **审核维度**：
  - 信息完整性检查
  - 名称合规性检查
  - 敏感词过滤
  - 技术规范检查
  - 资源链接验证
- **状态流转**：草稿 → 待审核 → 通过/拒绝 → 封禁

### 3. 评分与评价系统
- 1-5星评分
- 已安装用户标记
- 有帮助计数
- 匿名评价支持

### 4. 版本管理
- 语义化版本号
- 变更日志
- 稳定版标记
- 版本安装统计

## 目录结构

```
workshop/
├── __init__.py
├── models.py          # 数据模型
├── views.py           # 视图层
├── urls.py            # 路由配置
├── serializers.py     # API序列化器
├── admin.py           # 后台管理
├── permissions.py     # 权限控制
├── review.py          # 审核逻辑
├── apps.py            # 应用配置
├── README.md          # 本文档
├── templates/
│   └── workshop/
│       ├── base.html          # 基础模板
│       ├── index.html         # 首页
│       └── skill_detail.html  # 技能详情
└── static/
    └── workshop/
        ├── css/
        │   └── workshop.css   # 主样式
        └── js/
            └── workshop.js    # 主脚本
```

## 数据模型

### Skill（技能）
| 字段 | 类型 | 说明 |
|------|------|------|
| name | CharField | 技能名称 |
| slug | SlugField | URL别名 |
| creator | FK | 创作者 |
| category | FK | 所属分类 |
| status | Choice | 审核状态 |
| install_count | Int | 安装量 |
| avg_rating | Decimal | 平均评分 |
| is_featured | Bool | 是否精选 |
| is_premium | Bool | 是否付费 |

### CreatorProfile（创作者资料）
| 字段 | 类型 | 说明 |
|------|------|------|
| user | FK | 关联用户 |
| level | Choice | 工匠等级 |
| skills_count | Int | 技能总数 |
| total_installs | Int | 总安装量 |
| avg_rating | Decimal | 平均评分 |
| verified | Bool | 是否认证 |

### Rating（评分）
| 字段 | 类型 | 说明 |
|------|------|------|
| skill | FK | 技能 |
| user | FK | 用户 |
| rating | Int | 评分(1-5) |
| is_verified | Bool | 是否已安装用户 |

## API 接口

### 技能相关
- `GET /workshop/api/skills/` - 获取技能列表
- `POST /workshop/api/skills/` - 创建技能
- `GET /workshop/api/skills/{slug}/` - 获取技能详情
- `PUT /workshop/api/skills/{slug}/` - 更新技能
- `DELETE /workshop/api/skills/{slug}/` - 删除技能
- `POST /workshop/api/skills/{slug}/install/` - 安装技能
- `POST /workshop/api/skills/{slug}/uninstall/` - 卸载技能
- `POST /workshop/api/skills/{slug}/rate/` - 评分
- `POST /workshop/api/skills/{slug}/favorite/` - 收藏
- `POST /workshop/api/skills/{slug}/submit_review/` - 提交审核

### 创作者相关
- `GET /workshop/api/creators/` - 获取创作者列表
- `GET /workshop/api/creators/{id}/` - 获取创作者详情
- `GET /workshop/api/creators/me/` - 获取当前用户创作者资料
- `GET /workshop/api/creators/stats/` - 获取等级统计

### 分类相关
- `GET /workshop/api/categories/` - 获取分类列表

## 使用示例

### 创建技能
```python
# 通过 API
POST /workshop/api/skills/
{
    "name": "文章润色助手",
    "slug": "article-polish",
    "short_description": "自动优化文章表达",
    "full_description": "...",
    "category": 1,
    "tags": ["写作", "NLP"]
}
```

### 提交审核
```python
# 通过 API
POST /workshop/api/skills/article-polish/submit_review/
```

### 安装技能
```python
# 通过 API
POST /workshop/api/skills/article-polish/install/
```

## 审核逻辑

### 自动化审核检查项
1. **信息完整性** - 所有必填字段
2. **名称合规** - 长度、品牌词
3. **描述质量** - 长度、联系方式
4. **技术规范** - URL格式、版本号
5. **敏感词** - 内容过滤
6. **资源链接** - 图片URL有效性
7. **定价检查** - 付费技能必须定价

### 质量评分算法
```
总分数 = (完整度×0.15 + 受欢迎度×0.25 + 评分×0.30 + 活跃度×0.20 + 付费加分×0.10) × 10
```

## 前端集成

### 基础模板
```html
{% extends 'workshop/base.html' %}
{% block content %}
<!-- 页面内容 -->
{% endblock %}
```

### 引入资源
```html
<link rel="stylesheet" href="{% static 'workshop/css/workshop.css' %}">
<script src="{% static 'workshop/js/workshop.js' %}"></script>
```

### API 调用示例
```javascript
// 安装技能
const result = await WorkshopApp.apiRequest('/workshop/api/skills/skill-slug/install/', {
    method: 'POST'
});

// 显示消息
WorkshopApp.showToast('操作成功');
```

## 待扩展功能

1. **Token 经济**：技能付费、工匠收益分成
2. **技能依赖**：技能间的依赖管理
3. **数据分析**：安装趋势、用户画像
4. **通知系统**：审核结果、版本更新提醒
5. **评论系统**：回复、楼中楼
6. **分享机制**：社交分享、邀请奖励

## 开发指南

### 添加新字段
1. 修改 `models.py`
2. 更新 `serializers.py`
3. 更新 `admin.py`
4. 执行迁移：`python manage.py makemigrations workshop`

### 添加新 API
1. 在 `views.py` 添加 ViewSet 或 View
2. 在 `urls.py` 注册路由
3. 如需权限控制，添加 PermissionClass
4. 在 `serializers.py` 添加 Serializer

## 注意事项

- 所有涉及金额的字段使用 DecimalField
- 用户输入需进行 XSS 过滤
- 敏感操作需记录日志
- 定期清理无效安装记录
