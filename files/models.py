# -*- coding: utf-8 -*-
"""
文件管理模块 - 数据模型
支持用户文件和Agent知识库文件管理
"""

import os
import uuid
from datetime import datetime
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.deconstruct import deconstructible


def upload_to(instance, filename):
    """生成上传文件路径"""
    ext = os.path.splitext(filename)[1].lower()
    date_str = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:12]
    
    if instance.file_type == 'knowledge':
        return f'knowledge/{date_str}/{unique_id}{ext}'
    elif instance.file_type == 'attachment':
        return f'attachments/{date_str}/{unique_id}{ext}'
    elif instance.file_type == 'avatar':
        return f'avatars/{unique_id}{ext}'
    else:
        return f'files/{date_str}/{unique_id}{ext}'


@deconstructible
class FileSizeValidator:
    """文件大小验证器"""
    
    def __init__(self, max_size_mb=50):
        self.max_size = max_size_mb * 1024 * 1024  # 转换为字节
    
    def __call__(self, file):
        if file.size > self.max_size:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f'文件大小不能超过 {self.max_size // (1024*1024)}MB'
            )


class FileCategory(models.Model):
    """文件分类"""
    
    name = models.CharField('分类名称', max_length=50, unique=True)
    slug = models.SlugField('分类标识', unique=True)
    description = models.TextField('分类描述', blank=True)
    parent = models.ForeignKey(
        'self',
        verbose_name='父分类',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'files_category'
        verbose_name = '文件分类'
        verbose_name_plural = '文件分类'
        ordering = ['sort_order', '-created_at']
    
    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """获取完整分类路径"""
        if self.parent:
            return f"{self.parent.get_full_path()} / {self.name}"
        return self.name


class FileStorage(models.Model):
    """文件存储记录"""
    
    FILE_TYPE_CHOICES = [
        ('attachment', '用户附件'),
        ('knowledge', '知识库文件'),
        ('avatar', '用户头像'),
        ('other', '其他文件'),
    ]
    
    STORAGE_TYPE_CHOICES = [
        ('local', '本地存储'),
        ('oss', '阿里云OSS'),
        ('s3', 'AWS S3'),
    ]
    
    ACCESS_LEVEL_CHOICES = [
        ('private', '私有(仅本人)'),
        ('agent', 'Agent可见'),
        ('public', '公开'),
    ]
    
    # 基本信息
    file_type = models.CharField(
        '文件类型',
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default='attachment'
    )
    original_name = models.CharField('原始文件名', max_length=255)
    file_extension = models.CharField('文件扩展名', max_length=20)
    file_size = models.BigIntegerField('文件大小(字节)')
    mime_type = models.CharField('MIME类型', max_length=100)
    
    # 存储信息
    storage_type = models.CharField(
        '存储类型',
        max_length=20,
        choices=STORAGE_TYPE_CHOICES,
        default='local'
    )
    storage_path = models.CharField('存储路径', max_length=500)
    storage_url = models.URLField('访问URL', max_length=500, blank=True)
    oss_bucket = models.CharField('OSS Bucket', max_length=100, blank=True)
    oss_key = models.CharField('OSS Key', max_length=500, blank=True)
    
    # 关联信息
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='所属用户',
        on_delete=models.CASCADE,
        related_name='files',
        null=True,
        blank=True
    )
    agent = models.ForeignKey(
        'agents.Agent',
        verbose_name='关联Agent',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='knowledge_files'
    )
    category = models.ForeignKey(
        FileCategory,
        verbose_name='文件分类',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='files'
    )
    
    # 权限控制
    access_level = models.CharField(
        '访问权限',
        max_length=20,
        choices=ACCESS_LEVEL_CHOICES,
        default='private'
    )
    
    # 状态信息
    is_vectorized = models.BooleanField('已向量化', default=False)
    vector_id = models.CharField('向量ID', max_length=100, blank=True)
    vector_status = models.CharField('向量化状态', max_length=20, default='pending')
    vector_error = models.TextField('向量化错误', blank=True)
    
    is_active = models.BooleanField('是否启用', default=True)
    is_deleted = models.BooleanField('已删除', default=False)
    deleted_at = models.DateTimeField('删除时间', null=True, blank=True)
    
    # 元数据
    checksum = models.CharField('文件校验码', max_length=64, blank=True)
    metadata = models.JSONField('元数据', default=dict, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    accessed_at = models.DateTimeField('最后访问时间', null=True, blank=True)
    
    class Meta:
        db_table = 'files_storage'
        verbose_name = '文件存储'
        verbose_name_plural = '文件存储'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'file_type']),
            models.Index(fields=['agent', 'file_type']),
            models.Index(fields=['storage_type', 'is_active']),
            models.Index(fields=['is_vectorized', 'vector_status']),
        ]
    
    def __str__(self):
        return f"{self.original_name} ({self.file_size_display})"
    
    @property
    def file_size_display(self):
        """人类可读的文件大小"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    
    @property
    def is_image(self):
        """是否为图片"""
        return self.mime_type and self.mime_type.startswith('image/')
    
    @property
    def is_pdf(self):
        """是否为PDF"""
        return self.file_extension.lower() == '.pdf'
    
    @property
    def is_document(self):
        """是否为文档"""
        doc_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md']
        return self.file_extension.lower() in doc_extensions
    
    @property
    def is_previewable(self):
        """是否可预览"""
        return self.is_image or self.is_pdf or self.is_document
    
    def get_download_url(self):
        """获取下载URL"""
        from .services import FileService
        return FileService.get_download_url(self)
    
    def get_preview_url(self):
        """获取预览URL"""
        from .services import FileService
        return FileService.get_preview_url(self)
    
    def soft_delete(self):
        """软删除"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    def restore(self):
        """恢复删除"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class ChunkedUpload(models.Model):
    """分片上传记录"""
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('uploading', '上传中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    upload_id = models.CharField('上传ID', max_length=64, unique=True, db_index=True)
    file_name = models.CharField('文件名', max_length=255)
    file_size = models.BigIntegerField('文件大小')
    file_type = models.CharField('文件类型', max_length=100)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='上传用户',
        on_delete=models.CASCADE,
        related_name='chunked_uploads'
    )
    
    chunk_size = models.IntegerField('分片大小', default=5 * 1024 * 1024)  # 5MB
    total_chunks = models.IntegerField('总分片数')
    uploaded_chunks = models.IntegerField('已上传分片数', default=0)
    
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    storage_path = models.CharField('临时存储路径', max_length=500, blank=True)
    
    # 完成后关联的文件
    file_record = models.ForeignKey(
        FileStorage,
        verbose_name='关联文件',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='upload_sessions'
    )
    
    error_message = models.TextField('错误信息', blank=True)
    expires_at = models.DateTimeField('过期时间')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'files_chunked_upload'
        verbose_name = '分片上传'
        verbose_name_plural = '分片上传'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} ({self.upload_id[:8]}...)"
    
    @property
    def progress(self):
        """上传进度百分比"""
        if self.total_chunks == 0:
            return 0
        return round(self.uploaded_chunks / self.total_chunks * 100, 2)
    
    @property
    def is_expired(self):
        """是否已过期"""
        return timezone.now() > self.expires_at


class FileAccessLog(models.Model):
    """文件访问日志"""
    
    ACTION_CHOICES = [
        ('upload', '上传'),
        ('download', '下载'),
        ('preview', '预览'),
        ('delete', '删除'),
        ('share', '分享'),
    ]
    
    file = models.ForeignKey(
        FileStorage,
        verbose_name='文件',
        on_delete=models.CASCADE,
        related_name='access_logs'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='操作用户',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action = models.CharField('操作类型', max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)
    
    created_at = models.DateTimeField('访问时间', auto_now_add=True)
    
    class Meta:
        db_table = 'files_access_log'
        verbose_name = '文件访问日志'
        verbose_name_plural = '文件访问日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['file', 'action']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.file.original_name} - {self.get_action_display()}"
