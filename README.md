# Neshama Agent 开源版

<!-- Badges -->
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)

<div align="center">

**Soul（灵魂）+ Memory（记忆）+ 关系 = Neshama Agent**

*开源的 Agent 开发平台*

</div>

---

## 🌟 核心特性

### 🧠 Agent 核心

| 模块 | 描述 |
|------|------|
| **Soul Engine** | 6大系统定义Agent人格：情绪、驱动力、学习、创造力、类人特性、边界 |
| **3层记忆** | 模拟人类记忆：短期→中期→长期+RAG检索 |
| **多模型支持** | OpenAI, Claude, Gemini, 阿里百炼, 百度千帆, 智谱GLM等统一适配 |

### 🛠️ 生产级组件

| 模块 | 描述 |
|------|------|
| **Workflow Engine** | 可视化工作流编辑器 |
| **Workshop 市场** | 技能分享与发现 |
| **Kibbutz 社群** | 内置社区论坛 |

### 📱 跨平台客户端

- **Flutter APP** - iOS, Android, Web
- **微信小程序** - 轻量级移动体验

---

## 🏛️ 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│         Flutter APP │ WeChat MiniApp │ Web Dashboard            │
├─────────────────────────────────────────────────────────────────┤
│                      BUSINESS LAYER                             │
│              Workflow │ Workshop │ Kibbutz                       │
├─────────────────────────────────────────────────────────────────┤
│                       AGENT LAYER                               │
│           SOUL │ MEMORY │ MODEL ADAPTER                         │
├─────────────────────────────────────────────────────────────────┤
│                        DATA LAYER                                │
│           PostgreSQL │ Redis │ Vector Store                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 前置要求

- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Docker (可选)

### 安装

```bash
# 克隆仓库
git clone https://github.com/neshama-ai/neshama-oss.git
cd neshama-oss

# 使用 Docker
docker-compose up -d

# 或本地开发
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## 📁 目录结构

```
Neshama-OSS/
├── soul/                 # Soul引擎 - Agent人格系统
├── memory/               # Memory层 - 记忆管理
├── model_adapter/        # 模型适配器 - 多模型统一接入
├── workflow/             # 工作流引擎
├── core/                 # 核心引擎
├── auth/                 # 基础认证（不含OAuth）
├── kibbutz/              # 社群基础版
├── workshop/             # 工匠市场基础版
├── files/                # 文件管理
├── examples/             # 示例代码
├── configs/              # 配置文件
└── docs/                 # 文档
```

---

## ☁️ 云托管版本

需要更多功能？试试 **Neshama-Cloud**：

| 功能 | 开源版 | 云托管版 |
|------|--------|----------|
| Soul引擎 | ✅ | ✅ |
| 3层记忆 | ✅ | ✅ |
| 多模型支持 | ✅ | ✅ |
| 工作流 | ✅ | ✅ |
| 社群 | ✅ | ✅ |
| 微信OAuth | ❌ | ✅ |
| 支付宝OAuth | ❌ | ✅ |
| 支付系统 | ❌ | ✅ |
| 通知推送 | 基础 | 完整 |
| 创作者经济 | ❌ | ✅ |
| 积分商城 | ❌ | ✅ |

访问 https://neshama.ai/cloud 了解更多

---

## 📖 文档

- [快速开始指南](./QUICKSTART.md)
- [架构文档](./ARCHITECTURE.md)
- [Soul引擎指南](./soul/README.md)
- [Memory层文档](./memory/README.md)
- [模型适配器](./model_adapter/README.md)

---

## 🤝 贡献

欢迎提交 Pull Request！

请先阅读 [贡献指南](./CONTRIBUTING.md)。

---

## 📄 许可证

本项目采用 [MIT 许可证](./LICENSE)。
