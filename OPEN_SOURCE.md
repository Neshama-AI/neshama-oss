# Neshama Agent 开源版说明

## 版本说明

Neshama-OSS 是 Neshama Agent 的开源版本，采用 MIT 许可证，完全开放源代码。

## 开源版本包含

### ✅ 核心模块（开源）

| 模块 | 说明 | 许可证 |
|------|------|--------|
| soul/ | Soul引擎，定义Agent人格 | MIT |
| memory/ | 3层记忆系统 | MIT |
| model_adapter/ | 多模型统一适配 | MIT |
| workflow/ | 可视化工作流引擎 | MIT |
| core/ | 核心对话引擎 | MIT |
| auth/ | 基础用户认证 | MIT |
| kibbutz/ | 社群基础版 | MIT |
| workshop/ | 工匠市场基础版 | MIT |
| files/ | 文件管理 | MIT |
| examples/ | 示例代码 | MIT |
| configs/ | 配置模板 | MIT |

### ❌ 云托管版独有（商业）

| 模块 | 说明 |
|------|------|
| payment/ | 支付系统（微信/支付宝） |
| notification/ | 完整通知推送（WebSocket/Webhook） |
| auth/oauth/ | OAuth认证（微信/支付宝登录） |
| kibbutz/economy/ | 社群经济（积分商城/打赏） |
| workshop/economy/ | 创作者经济（收入/提现） |

## 技术栈

### 开源版本

- **后端**: Django 4.2+ / Django REST Framework
- **认证**: JWT (simplejwt)
- **数据库**: PostgreSQL 14+
- **缓存**: Redis 6+
- **向量存储**: 支持多种向量数据库

### 依赖库

```
Django>=4.2
djangorestframework>=3.14
djangorestframework-simplejwt>=5.3
psycopg2-binary>=2.9
redis>=5.0
pypdf2>=3.0
openai>=1.0
anthropic>=0.18
chromadb>=0.4
```

## 开发指南

### 本地开发

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 4. 初始化数据库
python manage.py migrate

# 5. 创建超级用户
python manage.py createsuperuser

# 6. 启动开发服务器
python manage.py runserver
```

### 运行测试

```bash
python manage.py test
```

### Docker 部署

```bash
docker-compose up -d
```

## 云托管版本

如果您需要以下功能，可以考虑使用 **Neshama-Cloud**：

1. **微信/支付宝 OAuth 登录** - 一键登录体验
2. **完整支付系统** - 会员订阅、付费内容
3. **高级通知推送** - WebSocket实时推送、Webhook集成
4. **创作者经济** - 技能销售、收入分成、提现
5. **社群积分商城** - 积分获取、打赏、兑换
6. **技术支持** - 优先技术支持服务

访问 https://neshama.ai/cloud 了解更多

## 许可证

Neshama-OSS 采用 [MIT 许可证](./LICENSE)。

## 联系方式

- GitHub Issues: https://github.com/neshama-ai/neshama-oss/issues
- 官网: https://neshama.ai

## 致谢

感谢所有贡献者的付出！
