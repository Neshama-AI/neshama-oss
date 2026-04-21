# -*- coding: utf-8 -*-
"""
文件管理视图
处理文件上传、下载、预览等API请求
"""

import os
import logging
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.static import serve
from django.conf import settings
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from .models import FileStorage, FileCategory, ChunkedUpload, FileAccessLog
from .serializers import (
    FileStorageSerializer, FileStorageListSerializer, FileUploadSerializer,
    FileCategorySerializer, ChunkedUploadSerializer, ChunkedUploadInitiateSerializer,
    ChunkedUploadChunkSerializer, ChunkedUploadCompleteSerializer,
    FileAccessLogSerializer, FileBatchDeleteSerializer, FileMoveSerializer
)
from .services import FileService, ChunkedUploadService, FileValidationError

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class FileUploadView(APIView):
    """文件上传视图"""
    
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """上传文件"""
        serializer = FileUploadSerializer(
            data=request.data,
            context={'request': request, 'max_size_mb': getattr(settings, 'MAX_FILE_SIZE_MB', 50)}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            file = serializer.validated_data['file']
            
            # 获取关联对象
            agent = None
            if serializer.validated_data.get('agent_id'):
                from agents.models import Agent
                agent = Agent.objects.get(id=serializer.validated_data['agent_id'])
            
            category = None
            if serializer.validated_data.get('category_id'):
                category = FileCategory.objects.get(id=serializer.validated_data['category_id'])
            
            # 上传文件
            file_record = FileService.upload_file(
                file=file,
                user=request.user,
                file_type=serializer.validated_data['file_type'],
                agent=agent,
                category=category,
                access_level=serializer.validated_data['access_level'],
                metadata=serializer.validated_data.get('metadata', {})
            )
            
            # 记录访问日志
            FileService.log_access(
                file_record, request.user, 'upload',
                get_client_ip(request), request.META.get('HTTP_USER_AGENT', '')
            )
            
            output_serializer = FileStorageSerializer(file_record)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
            
        except FileValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return Response(
                {'error': '文件上传失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileDownloadView(APIView):
    """文件下载视图"""
    
    permission_classes = [AllowAny]
    
    def get(self, request, file_id):
        """下载文件"""
        file_record = get_object_or_404(FileStorage, id=file_id, is_deleted=False)
        
        # 检查权限
        if not FileService.check_file_permission(file_record, request.user):
            return Response(
                {'error': '无权访问该文件'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # 获取文件内容
            content = FileService.download_file(
                file_record,
                user=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # 创建响应
            response = HttpResponse(content, content_type=file_record.mime_type)
            response['Content-Disposition'] = f'attachment; filename="{file_record.original_name}"'
            response['Content-Length'] = file_record.file_size
            
            return response
            
        except FileNotFoundError:
            return Response(
                {'error': '文件不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return Response(
                {'error': '文件下载失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FilePreviewView(APIView):
    """文件预览视图"""
    
    permission_classes = [AllowAny]
    
    def get(self, request, file_id):
        """预览文件"""
        file_record = get_object_or_404(FileStorage, id=file_id, is_deleted=False)
        
        # 检查权限
        if not FileService.check_file_permission(file_record, request.user):
            return Response(
                {'error': '无权访问该文件'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 检查是否可预览
        if not file_record.is_previewable:
            return Response(
                {'error': '该文件类型不支持预览'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            content = FileService.download_file(
                file_record,
                user=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # 记录访问日志
            FileService.log_access(
                file_record, request.user, 'preview',
                get_client_ip(request), request.META.get('HTTP_USER_AGENT', '')
            )
            
            return HttpResponse(content, content_type=file_record.mime_type)
            
        except FileNotFoundError:
            return Response(
                {'error': '文件不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"文件预览失败: {e}")
            return Response(
                {'error': '文件预览失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FileStreamView(APIView):
    """文件流式访问视图（用于CDN/OSS直连）"""
    
    permission_classes = [AllowAny]
    
    def get(self, request, file_id):
        """获取文件访问URL"""
        file_record = get_object_or_404(FileStorage, id=file_id, is_deleted=False)
        
        if not FileService.check_file_permission(file_record, request.user):
            return Response(
                {'error': '无权访问该文件'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 获取访问URL
        url = FileService.get_download_url(file_record)
        
        return Response({'url': url})


class FileViewSet(viewsets.ModelViewSet):
    """文件管理视图集"""
    
    serializer_class = FileStorageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'put', 'patch']
    
    def get_queryset(self):
        """获取当前用户的文件"""
        return FileStorage.objects.filter(
            user=self.request.user,
            is_deleted=False
        ).select_related('user', 'agent', 'category')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FileStorageListSerializer
        return FileStorageSerializer
    
    def perform_destroy(self, instance):
        """软删除文件"""
        FileService.delete_file(
            instance,
            user=self.request.user,
            ip_address=get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    @action(detail=True, methods=['get'])
    def download_url(self, request, pk=None):
        """获取下载URL"""
        file_record = self.get_object()
        url = FileService.get_download_url(file_record)
        return Response({'url': url})
    
    @action(detail=True, methods=['get'])
    def preview_url(self, request, pk=None):
        """获取预览URL"""
        file_record = self.get_object()
        url = FileService.get_preview_url(file_record)
        if not url:
            return Response({'error': '不支持预览'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'url': url})
    
    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除文件"""
        serializer = FileBatchDeleteSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        file_ids = serializer.validated_data['file_ids']
        deleted_count = 0
        
        for file_id in file_ids:
            try:
                file_record = FileStorage.objects.get(id=file_id, user=request.user)
                if FileService.delete_file(
                    file_record,
                    user=request.user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                ):
                    deleted_count += 1
            except Exception as e:
                logger.error(f"批量删除失败: {file_id}, {e}")
        
        return Response({
            'deleted': deleted_count,
            'total': len(file_ids)
        })
    
    @action(detail=False, methods=['post'])
    def move(self, request):
        """移动文件"""
        serializer = FileMoveSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        file_ids = serializer.validated_data['file_ids']
        updated_count = 0
        
        files = FileStorage.objects.filter(id__in=file_ids, user=request.user)
        
        for file_record in files:
            if serializer.validated_data.get('category_id'):
                file_record.category_id = serializer.validated_data['category_id']
            if serializer.validated_data.get('agent_id'):
                file_record.agent_id = serializer.validated_data['agent_id']
            if serializer.validated_data.get('access_level'):
                file_record.access_level = serializer.validated_data['access_level']
            file_record.save()
            updated_count += 1
        
        return Response({
            'updated': updated_count,
            'total': len(file_ids)
        })
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """获取文件分类列表"""
        categories = FileCategory.objects.filter(is_active=True)
        serializer = FileCategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def access_logs(self, request, pk=None):
        """获取文件访问日志"""
        file_record = self.get_object()
        logs = FileAccessLog.objects.filter(file=file_record).order_by('-created_at')[:50]
        serializer = FileAccessLogSerializer(logs, many=True)
        return Response(serializer.data)


class ChunkedUploadInitiateView(APIView):
    """分片上传初始化"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """初始化分片上传"""
        serializer = ChunkedUploadInitiateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            upload_record = ChunkedUploadService.initiate_upload(
                file_name=serializer.validated_data['file_name'],
                file_size=serializer.validated_data['file_size'],
                file_type=serializer.validated_data.get('file_type', ''),
                user=request.user
            )
            
            output_serializer = ChunkedUploadSerializer(upload_record)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"分片上传初始化失败: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChunkedUploadChunkView(APIView):
    """分片上传"""
    
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """上传分片"""
        serializer = ChunkedUploadChunkSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = ChunkedUploadService.upload_chunk(
                upload_id=serializer.validated_data['upload_id'],
                chunk_index=serializer.validated_data['chunk_index'],
                chunk_data=serializer.validated_data['chunk'].read(),
                user=request.user
            )
            
            return Response(result)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"分片上传失败: {e}")
            return Response(
                {'error': '分片上传失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChunkedUploadCompleteView(APIView):
    """分片上传完成"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """完成分片上传"""
        serializer = ChunkedUploadCompleteSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 获取关联对象
            agent = None
            if serializer.validated_data.get('agent_id'):
                from agents.models import Agent
                agent = Agent.objects.get(id=serializer.validated_data['agent_id'])
            
            category = None
            if serializer.validated_data.get('category_id'):
                category = FileCategory.objects.get(id=serializer.validated_data['category_id'])
            
            file_record = ChunkedUploadService.complete_upload(
                upload_id=serializer.validated_data['upload_id'],
                user=request.user,
                file_type=serializer.validated_data['file_type'],
                agent=agent,
                category=category
            )
            
            output_serializer = FileStorageSerializer(file_record)
            return Response(output_serializer.data)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"分片上传完成失败: {e}")
            return Response(
                {'error': '分片上传完成失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChunkedUploadCancelView(APIView):
    """取消分片上传"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """取消分片上传"""
        upload_id = request.data.get('upload_id')
        
        if not upload_id:
            return Response({'error': '缺少upload_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        success = ChunkedUploadService.cancel_upload(upload_id, request.user)
        
        if success:
            return Response({'message': '上传已取消'})
        else:
            return Response({'error': '取消失败'}, status=status.HTTP_400_BAD_REQUEST)


class ChunkedUploadStatusView(APIView):
    """查询分片上传状态"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, upload_id):
        """获取上传状态"""
        try:
            upload_record = ChunkedUpload.objects.get(upload_id=upload_id, user=request.user)
            serializer = ChunkedUploadSerializer(upload_record)
            return Response(serializer.data)
        except ChunkedUpload.DoesNotExist:
            return Response({'error': '上传记录不存在'}, status=status.HTTP_404_NOT_FOUND)


class FileCategoryViewSet(viewsets.ModelViewSet):
    """文件分类视图集"""
    
    queryset = FileCategory.objects.filter(is_active=True)
    serializer_class = FileCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 支持树形结构查询
        parent_id = self.request.query_params.get('parent_id')
        if parent_id == 'null' or parent_id == '0':
            queryset = queryset.filter(parent__isnull=True)
        elif parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        
        return queryset.order_by('sort_order', 'name')


class UserStorageStatsView(APIView):
    """用户存储统计"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """获取存储统计"""
        user = request.user
        
        # 基础统计
        total_files = FileStorage.objects.filter(
            user=user, is_deleted=False
        ).count()
        
        total_size = FileStorage.objects.filter(
            user=user, is_deleted=False
        ).aggregate(total=models.Sum('file_size'))['total'] or 0
        
        # 按类型统计
        by_type = {}
        for file_type, name in FileStorage.FILE_TYPE_CHOICES:
            count = FileStorage.objects.filter(
                user=user, is_deleted=False, file_type=file_type
            ).count()
            size = FileStorage.objects.filter(
                user=user, is_deleted=False, file_type=file_type
            ).aggregate(total=models.Sum('file_size'))['total'] or 0
            by_type[file_type] = {
                'name': name,
                'count': count,
                'size': size
            }
        
        # 最近上传
        recent_files = FileStorage.objects.filter(
            user=user, is_deleted=False
        ).order_by('-created_at')[:10]
        
        return Response({
            'total_files': total_files,
            'total_size': total_size,
            'total_size_display': self._format_size(total_size),
            'by_type': by_type,
            'recent_files': FileStorageListSerializer(recent_files, many=True).data
        })
    
    def _format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"


# 导入models用于统计查询
from django.db import models
