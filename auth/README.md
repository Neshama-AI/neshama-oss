# Neshama Agent 用户认证系统

## 概述

Neshama Agent的用户认证模块，支持 **Free** 和 **Pro** 两档用户体系，采用JWT无状态认证方案。

## 技术栈

- **Django** + Django REST Framework
- **JWT**: `djangorestframework-simplejwt`
- **OAuth**: 微信公众平台 / 支付宝开放平台

## 目录结构

```
auth/
├── models.py          # 用户模型（扩展Django User）
├── views.py           # 视图（注册/登录/OAuth）
├── urls.py            # 路由配置
├── serializers.py     # API序列化器
├── permissions.py    # 权限装饰器
├── wechat_oauth.py    # 微信OAuth封装
├── alipay_oauth.py    # 支付宝OAuth封装
├── admin.py           # Django后台管理
└── README.md          # 本文档
```

## 用户体系

### 用户类型

| 类型 | 标识 | 说明 |
|------|------|------|
| Free | `free` | 免费用户，基础功能 |
| Pro | `pro` | 付费用户，高级功能 |

### Pro用户权益

- 高级Agent
- 无限记忆
- 自定义灵魂
- API访问
- 优先支持

## API接口

### 基础认证

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/auth/register/` | 用户注册 | 否 |
| POST | `/auth/login/` | 用户登录 | 否 |
| POST | `/auth/logout/` | 用户登出 | 是 |
| POST | `/auth/token/refresh/` | 刷新Token | 否 |

### 用户资料

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/auth/profile/` | 获取资料 | 是 |
| PUT | `/auth/profile/` | 更新资料 | 是 |
| POST | `/auth/profile/password/` | 修改密码 | 是 |
| POST | `/auth/password/reset/` | 密码重置 | 否 |
| GET | `/auth/login-history/` | 登录历史 | 是 |

### OAuth登录

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/auth/oauth/wechat/` | 获取微信授权链接 | 否 |
| POST | `/auth/oauth/wechat/` | 处理微信回调 | 可选 |
| GET | `/auth/oauth/alipay/` | 获取支付宝授权链接 | 否 |
| POST | `/auth/oauth/alipay/` | 处理支付宝回调 | 可选 |

### 设备管理

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/auth/devices/` | 设备列表 | 是 |
| DELETE | `/auth/devices/<id>/` | 删除设备 | 是 |
| POST | `/auth/devices/<id>/logout/` | 登出设备 | 是 |

### 邀请系统

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/auth/invite/stats/` | 邀请统计 | 是 |

### 管理后台

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/auth/admin/users/` | 用户列表 | 管理员 |
| POST | `/auth/admin/users/<id>/upgrade/` | 升级用户 | 管理员 |

## 数据模型

### UserProfile

扩展Django User模型，主要字段：

- `user_type`: 用户类型 (free/pro)
- `pro_expire_date`: Pro到期时间
- `phone`: 手机号
- `wechat_openid`: 微信OpenID
- `wechat_unionid`: 微信UnionID
- `alipay_user_id`: 支付宝UserID
- `avatar_url`: 头像
- `invite_code`: 个人邀请码
- `invited_by`: 邀请人

### LoginLog

登录日志，记录每次登录行为。

### UserDevice

用户设备，支持多设备登录管理。

### InviteCode

邀请码池，支持批量生成和分配。

## 使用示例

### 注册

```bash
curl -X POST http://api.example.com/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "email": "john@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123",
    "invite_code": "ABC12345"
  }'
```

### 登录

```bash
curl -X POST http://api.example.com/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "login_type": "email",
    "email": "john@example.com",
    "password": "securepass123"
  }'
```

### 获取资料

```bash
curl http://api.example.com/auth/profile/ \
  -H "Authorization: Bearer <access_token>"
```

### 微信登录

```bash
# 1. 获取授权链接
curl http://api.example.com/auth/oauth/wechat/

# 2. 用户授权后，带code回调
curl -X POST http://api.example.com/auth/oauth/wechat/ \
  -H "Content-Type: application/json" \
  -d '{
    "code": "微信返回的code",
    "bind_type": "login"
  }'
```

## 配置

### 环境变量

```bash
# 微信
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
WECHAT_REDIRECT_URI=https://your-domain.com/auth/wechat/callback/

# 支付宝
ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY=your_private_key
ALIPAY_PUBLIC_KEY=alipay_public_key
ALIPAY_REDIRECT_URI=https://your-domain.com/auth/alipay/callback/

# JWT
JWT_SECRET_KEY=your_secret_key
JWT_ACCESS_TOKEN_LIFETIME=3600
JWT_REFRESH_TOKEN_LIFETIME=604800
```

### Django设置

```python
# settings.py

AUTH_USER_MODEL = 'auth.UserProfile'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

## 安全考虑

1. **密码加密**: Django原生bcrypt
2. **JWT**: 短期Access Token + 长期Refresh Token
3. **CSRF**: Token刷新无需CSRF
4. **限流**: 登录接口限流防止暴力破解
5. **OAuth**: 状态参数防止CSRF

## 待完成

- [ ] 短信服务对接（验证码登录）
- [ ] 邮箱服务对接（验证/重置）
- [ ] Redis Session分布式支持
- [ ] 微信/支付宝正式密钥配置
- [ ] 邀请奖励系统实现
- [ ] 登录异常检测

## License

Internal Project - Neshama Agent
