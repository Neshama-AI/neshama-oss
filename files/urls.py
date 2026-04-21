# -*- coding: utf-8 -*-
"""
文件管理URL路由
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 创建路由注册器
router = DefaultRouter()
router.register(r'files', views.FileViewSet, basename='files')
router.register(r'categories', views.FileCategoryViewSet, basename='file-categories')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # 文件操作
    path('upload/', views.FileUploadView.as_view(), name='file-upload'),
    path('<int:file_id>/download/', views.FileDownloadView.as_view(), name='file-download'),
    path('<int:file_id>/preview/', views.FilePreviewView.as_view(), name='file-preview'),
    path('<int:file_id>/stream/', views.FileStreamView.as_view(), name='file-stream'),
    
    # 分片上传
    path('chunked/initiate/', views.ChunkedUploadInitiateView.as_view(), name='chunked-initiate'),
    path('chunked/upload/', views.ChunkedUploadChunkView.as_view(), name='chunked-upload'),
    path('chunked/complete/', views.ChunkedUploadCompleteView.as_view(), name='chunked-complete'),
    path('chunked/cancel/', views.ChunkedUploadCancelView.as_view(), name='chunked-cancel'),
    path('chunked/status/<str:upload_id>/', views.ChunkedUploadStatusView.as_view(), name='chunked-status'),
    
    # 存储统计
    path('stats/', views.UserStorageStatsView.as_view(), name='storage-stats'),
]
