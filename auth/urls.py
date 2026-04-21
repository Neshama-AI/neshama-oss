"""
Neshama Agent 认证模块URL路由 - 开源版
基础认证路由，不包含OAuth功能
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import RegisterView, LoginView, UserProfileViewSet, LoginLogViewSet, jwt_login


# 用户端路由
urlpatterns = [
    # 注册/登录
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    
    # JWT Token刷新
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # 用户资料
    path('profile/', UserProfileViewSet.as_view({
        'get': 'me',
        'put': 'me',
        'patch': 'me'
    }), name='auth-profile'),
    path('profile/change-password/', UserProfileViewSet.as_view({
        'post': 'change_password'
    }), name='change-password'),
    path('profile/reset-password/', UserProfileViewSet.as_view({
        'post': 'reset_password_request'
    }), name='password-reset'),
    
    # 登录历史
    path('login-logs/', LoginLogViewSet.as_view({
        'get': 'list'
    }), name='login-history'),
    
    # 第三方集成登录
    path('jwt-login/', jwt_login, name='jwt-login'),
]


# URL命名空间说明:
# auth-register        - 用户注册
# auth-login           - 用户登录
# token-refresh        - Token刷新
# auth-profile         - 用户资料（GET获取，PUT/PATCH更新）
# change-password      - 修改密码
# password-reset       - 密码重置请求
# login-history        - 登录历史
# jwt-login            - JWT登录（用于第三方系统集成）
