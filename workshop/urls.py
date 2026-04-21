# -*- coding: utf-8 -*-
"""
Workshop URL 路由配置
Neshama Agent 项目
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SkillViewSet, SkillCategoryViewSet, CreatorViewSet,
    RatingViewSet, InstallRecordViewSet, ReviewQueueViewSet
)

# 创建路由注册器
router = DefaultRouter()
router.register(r'skills', SkillViewSet, basename='skill')
router.register(r'categories', SkillCategoryViewSet, basename='category')
router.register(r'creators', CreatorViewSet, basename='creator')
router.register(r'ratings', RatingViewSet, basename='rating')
router.register(r'installs', InstallRecordViewSet, basename='install')
router.register(r'reviews', ReviewQueueViewSet, basename='review')

# URL 命名空间
app_name = 'workshop'

urlpatterns = [
    # API 路由
    path('api/', include(router.urls)),
    
    # Web 页面路由（可选）
    # path('', views.index, name='index'),
    # path('skill/<slug:slug>/', views.skill_detail, name='skill_detail'),
    # path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    # path('creator/<int:pk>/', views.creator_profile, name='creator_profile'),
    # path('publish/', views.publish_skill, name='publish'),
    # path('manage/', views.manage_skills, name='manage'),
]
