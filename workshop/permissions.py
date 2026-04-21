# -*- coding: utf-8 -*-
"""
Workshop 权限控制模块
Neshama Agent 项目 - 自定义权限类
"""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    对象所有者权限
    
    - 允许只读操作（GET, HEAD, OPTIONS）
    - 仅允许对象所有者进行写操作
    """

    def has_object_permission(self, request, view, obj):
        # 只读操作允许所有人
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 检查是否为技能的创作者
        if hasattr(obj, 'creator'):
            return obj.creator.user == request.user
        
        # 检查是否为创作者本人
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsVerifiedCreator(permissions.BasePermission):
    """
    已认证创作者权限
    
    - 要求用户已登录
    - 要求用户已完成创作者认证
    """

    message = '需要先完成创作者认证才能发布技能'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # 检查是否有创作者资料
        if not hasattr(request.user, 'craftsman_profile'):
            return False
        
        return True


class IsSkillOwner(permissions.BasePermission):
    """
    技能所有者权限
    
    - 仅技能创作者可以进行修改操作
    """

    message = '只有技能创作者可以进行此操作'

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        return obj.creator.user == request.user


class IsActiveSkill(permissions.BasePermission):
    """
    活跃技能权限
    
    - 只允许对已通过审核的技能进行安装等操作
    """

    message = '只能对已通过的技能进行操作'

    def has_object_permission(self, request, view, obj):
        return obj.status == 'approved'


class CanReviewSkill(permissions.BasePermission):
    """
    技能审核权限
    
    - 仅管理员可以审核技能
    """

    message = '只有管理员可以进行技能审核'

    def has_permission(self, request, view):
        return request.user.is_staff


class RateLimitPermission(permissions.BasePermission):
    """
    评分频率限制权限
    
    - 限制用户评分频率
    """

    message = '评分过于频繁，请稍后再试'

    def has_permission(self, request, view):
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return True
        
        if not request.user.is_authenticated:
            return False
        
        # TODO: 实现频率限制逻辑
        # 可以使用缓存记录用户评分时间
        
        return True
