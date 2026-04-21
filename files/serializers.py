# -*- coding: utf-8 -*-
"""
文件管理序列化器
用于API接口的数据序列化
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FileStorage, FileCategory, ChunkedUpload, FileAccessLog

User = get_user_model()


class FileCategorySerializer(serializers.ModelSerializer):
    """文件分类序列化器"""
    
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    children_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FileCategory
        fields = [
            'id', 'name', 'slug', 'description', 'parent', 'full_path',
            'sort_order', 'is_active', 'children_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_children_count(self, obj):
        return obj.children.count()


class FileStorageSerializer(serializers.ModelSerializer):
    """文件存储序列化器"""
    
    file_size_display = serializers.CharField(read_only=True)
    is_image = serializers.BooleanField(read_only=True)
    is_pdf = serializers.BooleanField(read_only=True)
    is_document = serializers.BooleanField(read_only=True)
    is_previewable = serializers.BooleanField(read_only=True)
    download_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    agent_name = serializers.CharField(source='agent.name', read_only=True, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    
    class Meta:
        model = FileStorage
        fields = [
            'id', 'file_type', 'original_name', 'file_extension', 'file_size',
            'file_size_display', 'mime_type', 'storage_type', 'storage_url',
            'user', 'user_name', 'agent', 'agent_name', 'category', 'category_name',
            'access_level', 'is_vectorized', 'vector_status',
            'is_image', 'is_pdf', 'is_document', 'is_previewable',
            'download_url', 'preview_url', 'checksum', 'metadata',
            'created_at', 'updated_at', 'accessed_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'storage_type', 'storage_url', 'checksum',
            'is_vectorized', 'vector_status', 'created_at', 'updated_at', 'accessed_at'
        ]
    
    def get_download_url(self, obj):
        from .services import FileService
        return FileService.get_download_url(obj)
    
    def get_preview_url(self, obj):
        from .services import FileService
        return FileService.get_preview_url(obj)


class FileStorageListSerializer(serializers.ModelSerializer):
    """文件列表序列化器（简化版）"""
    
    file_size_display = serializers.CharField(read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    
    class Meta:
        model = FileStorage
        fields = [
            'id', 'file_type', 'original_name', 'file_extension', 
            'file_size', 'file_size_display', 'mime_type',
            'user_name', 'access_level', 'is_vectorized',
            'created_at', 'accessed_at'
        ]


class FileUploadSerializer(serializers.Serializer):
    """文件上传序列化器"""
    
    file = serializers.FileField(required=True)
    file_type = serializers.ChoiceField(
        choices=[
            ('attachment', '用户附件'),
            ('knowledge', '知识库文件'),
            ('avatar', '用户头像'),
        ],
        default='attachment'
    )
    agent_id = serializers.IntegerField(required=False, allow_null=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    access_level = serializers.ChoiceField(
        choices=[
            ('private', '私有'),
            ('agent', 'Agent可见'),
            ('public', '公开'),
        ],
        default='private'
    )
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_file(self, value):
        """验证文件"""
        from .services import FileService, FileValidationError
        
        max_size = self.context.get('max_size_mb', 50)
        try:
            FileService.validate_file(value, max_size)
        except FileValidationError as e:
            raise serializers.ValidationError(str(e))
        
        return value
    
    def validate_agent_id(self, value):
        """验证Agent"""
        if value:
            from agents.models import Agent
            if not Agent.objects.filter(id=value).exists():
                raise serializers.ValidationError("Agent不存在")
        return value
    
    def validate_category_id(self, value):
        """验证分类"""
        if value:
            if not FileCategory.objects.filter(id=value).exists():
                raise serializers.ValidationError("分类不存在")
        return value


class ChunkedUploadInitiateSerializer(serializers.Serializer):
    """分片上传初始化序列化器"""
    
    file_name = serializers.CharField(max_length=255)
    file_size = serializers.IntegerField(min_value=1)
    file_type = serializers.CharField(max_length=100, required=False, default='')
    
    def validate_file_size(self, value):
        max_size = 100 * 1024 * 1024  # 100MB
        if value > max_size:
            raise serializers.ValidationError(f"文件大小不能超过 {max_size // (1024*1024)}MB")
        return value


class ChunkedUploadSerializer(serializers.ModelSerializer):
    """分片上传序列化器"""
    
    progress = serializers.FloatField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    file_record = FileStorageSerializer(read_only=True)
    
    class Meta:
        model = ChunkedUpload
        fields = [
            'id', 'upload_id', 'file_name', 'file_size', 'file_type',
            'chunk_size', 'total_chunks', 'uploaded_chunks', 'progress',
            'status', 'is_expired', 'file_record', 'error_message',
            'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChunkedUploadChunkSerializer(serializers.Serializer):
    """分片数据序列化器"""
    
    upload_id = serializers.CharField(max_length=64)
    chunk_index = serializers.IntegerField(min_value=0)
    chunk = serializers.FileField(required=True)
    
    def validate(self, attrs):
        from .models import ChunkedUpload
        from django.utils import timezone
        
        upload_id = attrs['upload_id']
        chunk_index = attrs['chunk_index']
        user = self.context['request'].user
        
        try:
            upload_record = ChunkedUpload.objects.get(upload_id=upload_id, user=user)
        except ChunkedUpload.DoesNotExist:
            raise serializers.ValidationError("上传记录不存在")
        
        if upload_record.is_expired:
            raise serializers.ValidationError("上传已过期")
        
        if upload_record.status == 'completed':
            raise serializers.ValidationError("上传已完成")
        
        if chunk_index >= upload_record.total_chunks:
            raise serializers.ValidationError("分片索引超出范围")
        
        attrs['upload_record'] = upload_record
        return attrs


class ChunkedUploadCompleteSerializer(serializers.Serializer):
    """分片上传完成序列化器"""
    
    upload_id = serializers.CharField(max_length=64)
    file_type = serializers.ChoiceField(
        choices=[
            ('attachment', '用户附件'),
            ('knowledge', '知识库文件'),
        ],
        default='attachment'
    )
    agent_id = serializers.IntegerField(required=False, allow_null=True)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_upload_id(self, value):
        user = self.context['request'].user
        try:
            ChunkedUpload.objects.get(upload_id=value, user=user)
        except ChunkedUpload.DoesNotExist:
            raise serializers.ValidationError("上传记录不存在")
        return value


class FileAccessLogSerializer(serializers.ModelSerializer):
    """文件访问日志序列化器"""
    
    file_name = serializers.CharField(source='file.original_name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = FileAccessLog
        fields = [
            'id', 'file', 'file_name', 'user', 'user_name', 
            'action', 'action_display', 'ip_address', 'created_at'
        ]


class FileBatchDeleteSerializer(serializers.Serializer):
    """批量删除序列化器"""
    
    file_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    
    def validate_file_ids(self, value):
        user = self.context['request'].user
        files = FileStorage.objects.filter(id__in=value, user=user, is_deleted=False)
        
        if files.count() != len(value):
            raise serializers.ValidationError("部分文件不存在或无权删除")
        
        return value


class FileMoveSerializer(serializers.Serializer):
    """文件移动序列化器"""
    
    file_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    category_id = serializers.IntegerField(required=False, allow_null=True)
    agent_id = serializers.IntegerField(required=False, allow_null=True)
    access_level = serializers.ChoiceField(
        choices=[
            ('private', '私有'),
            ('agent', 'Agent可见'),
            ('public', '公开'),
        ],
        required=False
    )
    
    def validate(self, attrs):
        user = self.context['request'].user
        file_ids = attrs['file_ids']
        
        files = FileStorage.objects.filter(id__in=file_ids, user=user, is_deleted=False)
        if files.count() != len(file_ids):
            raise serializers.ValidationError("部分文件不存在或无权操作")
        
        return attrs
