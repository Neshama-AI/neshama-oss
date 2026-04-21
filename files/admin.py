# -*- coding: utf-8 -*-
"""
文件管理后台管理
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import FileStorage, FileCategory, ChunkedUpload, FileAccessLog


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    """文件分类管理"""
    
    list_display = ['name', 'slug', 'parent', 'sort_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug', 'description']
    ordering = ['sort_order', '-created_at']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = [
        ('基本信息', {'fields': ['name', 'slug', 'description']}),
        ('分类结构', {'fields': ['parent', 'sort_order']}),
        ('状态', {'fields': ['is_active']}),
    ]


@admin.register(FileStorage)
class FileStorageAdmin(admin.ModelAdmin):
    """文件存储管理"""
    
    list_display = [
        'id', 'original_name', 'file_type', 'file_size_display',
        'user', 'storage_type', 'access_level', 'is_vectorized',
        'is_active', 'created_at'
    ]
    list_filter = [
        'file_type', 'storage_type', 'access_level',
        'is_vectorized', 'is_active', 'is_deleted',
        'created_at'
    ]
    search_fields = ['original_name', 'storage_path', 'user__username']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    readonly_fields = [
        'storage_path', 'storage_url', 'checksum',
        'created_at', 'updated_at', 'accessed_at'
    ]
    
    fieldsets = [
        ('文件信息', {
            'fields': [
                'file_type', 'original_name', 'file_extension',
                'file_size', 'mime_type', 'checksum'
            ]
        }),
        ('存储信息', {
            'fields': ['storage_type', 'storage_path', 'storage_url', 'oss_bucket', 'oss_key']
        }),
        ('关联信息', {
            'fields': ['user', 'agent', 'category', 'access_level']
        }),
        ('向量化状态', {
            'fields': ['is_vectorized', 'vector_id', 'vector_status', 'vector_error']
        }),
        ('状态', {
            'fields': ['is_active', 'is_deleted', 'deleted_at']
        }),
        ('元数据', {
            'fields': ['metadata']
        }),
        ('时间戳', {
            'fields': ['created_at', 'updated_at', 'accessed_at'],
            'classes': ['collapse']
        }),
    ]
    
    def file_size_display(self, obj):
        return obj.file_size_display
    file_size_display.short_description = '文件大小'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'agent', 'category')


@admin.register(ChunkedUpload)
class ChunkedUploadAdmin(admin.ModelAdmin):
    """分片上传管理"""
    
    list_display = [
        'upload_id', 'file_name', 'file_size', 'user',
        'progress', 'status', 'expires_at', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['upload_id', 'file_name', 'user__username']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    readonly_fields = ['upload_id', 'created_at', 'updated_at', 'progress', 'is_expired']
    
    fieldsets = [
        ('文件信息', {'fields': ['upload_id', 'file_name', 'file_size', 'file_type']}),
        ('上传信息', {
            'fields': [
                'user', 'chunk_size', 'total_chunks', 'uploaded_chunks',
                'progress', 'status', 'storage_path'
            ]
        }),
        ('关联文件', {'fields': ['file_record']}),
        ('状态信息', {'fields': ['error_message', 'expires_at', 'is_expired']}),
        ('时间戳', {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'file_record')


@admin.register(FileAccessLog)
class FileAccessLogAdmin(admin.ModelAdmin):
    """文件访问日志管理"""
    
    list_display = ['id', 'file', 'user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['file__original_name', 'user__username', 'ip_address']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    readonly_fields = ['file', 'user', 'action', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('file', 'user')
