"""
Neshama Agent 权限装饰器 - 开源版
基础权限控制
"""

from functools import wraps
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    对象所有者或只读权限
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj == request.user or request.user.is_staff


class IsAdminUser(permissions.BasePermission):
    """
    仅管理员可访问
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_staff
        )


def admin_required(func):
    """
    管理员权限装饰器（函数视图用）
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {'error': '请先登录'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if not request.user.is_staff:
            return Response(
                {'error': '需要管理员权限'},
                status=status.HTTP_403_FORBIDDEN
            )
        return func(request, *args, **kwargs)
    return wrapper
