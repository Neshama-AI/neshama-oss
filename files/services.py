# -*- coding: utf-8 -*-
"""
文件管理服务层
处理文件上传、下载、预览等业务逻辑
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any, List
from django.conf import settings
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from .models import FileStorage, FileCategory, ChunkedUpload, FileAccessLog
from .storage import storage_manager, get_storage_backend

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """文件验证错误"""
    pass


class FileService:
    """文件服务类"""
    
    # 允许的文件类型白名单
    ALLOWED_EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
        'document': ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.txt', '.md'],
        'audio': ['.mp3', '.wav', '.ogg', '.m4a', '.flac'],
        'video': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
    }
    
    # MIME类型映射
    MIME_TYPE_MAP = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.zip': 'application/zip',
        '.rar': 'application/vnd.rar',
    }
    
    @classmethod
    def get_mime_type(cls, filename: str) -> str:
        """根据文件扩展名获取MIME类型"""
        ext = os.path.splitext(filename)[1].lower()
        return cls.MIME_TYPE_MAP.get(ext, 'application/octet-stream')
    
    @classmethod
    def validate_file(cls, file: UploadedFile, max_size_mb: int = 50) -> None:
        """
        验证文件
        
        Args:
            file: 上传的文件对象
            max_size_mb: 最大文件大小(MB)
            
        Raises:
            FileValidationError: 验证失败时抛出
        """
        # 检查文件大小
        max_size_bytes = max_size_mb * 1024 * 1024
        if file.size > max_size_bytes:
            raise FileValidationError(f"文件大小不能超过 {max_size_mb}MB")
        
        # 检查文件扩展名
        ext = os.path.splitext(file.name)[1].lower()
        all_extensions = []
        for extensions in cls.ALLOWED_EXTENSIONS.values():
            all_extensions.extend(extensions)
        
        if ext not in all_extensions:
            raise FileValidationError(
                f"不支持的文件类型: {ext}，支持的类型: {', '.join(all_extensions)}"
            )
        
        # 检查MIME类型
        if file.content_type:
            allowed_types = [
                'image/', 'application/pdf', 'application/msword',
                'application/vnd.', 'text/', 'audio/', 'video/',
                'application/zip', 'application/x-rar'
            ]
            if not any(file.content_type.startswith(t) for t in allowed_types):
                raise FileValidationError(f"不支持的文件类型: {file.content_type}")
    
    @classmethod
    def generate_storage_path(cls, original_name: str, file_type: str = 'attachment') -> str:
        """生成存储路径"""
        ext = os.path.splitext(original_name)[1].lower()
        date_str = timezone.now().strftime('%Y%m%d')
        unique_id = uuid.uuid4().hex[:12]
        
        path_map = {
            'attachment': f'attachments/{date_str}/{unique_id}{ext}',
            'knowledge': f'knowledge/{date_str}/{unique_id}{ext}',
            'avatar': f'avatars/{unique_id}{ext}',
        }
        
        return path_map.get(file_type, f'files/{date_str}/{unique_id}{ext}')
    
    @classmethod
    @transaction.atomic
    def upload_file(cls, file: UploadedFile, user, file_type: str = 'attachment',
                   agent=None, category=None, access_level: str = 'private',
                   metadata: Dict = None) -> FileStorage:
        """
        上传文件
        
        Args:
            file: 上传的文件对象
            user: 上传用户
            file_type: 文件类型
            agent: 关联的Agent
            category: 文件分类
            access_level: 访问权限
            metadata: 额外元数据
            
        Returns:
            FileStorage: 文件记录对象
        """
        # 验证文件
        max_size = getattr(settings, 'MAX_FILE_SIZE_MB', 50)
        cls.validate_file(file, max_size)
        
        # 生成存储路径
        storage_path = cls.generate_storage_path(file.name, file_type)
        
        # 获取存储后端并上传
        storage_type = getattr(settings, 'DEFAULT_FILE_STORAGE', 'local')
        storage = get_storage_backend(storage_type)
        
        # 上传到存储
        upload_result = storage.upload(file, storage_path)
        
        # 获取文件扩展名和MIME类型
        ext = os.path.splitext(file.name)[1].lower()
        
        # 创建文件记录
        file_record = FileStorage.objects.create(
            file_type=file_type,
            original_name=file.name,
            file_extension=ext,
            file_size=file.size,
            mime_type=upload_result.get('mime_type', file.content_type or cls.get_mime_type(file.name)),
            storage_type=storage_type,
            storage_path=storage_path,
            storage_url=upload_result.get('url', ''),
            oss_bucket=upload_result.get('oss_bucket', ''),
            oss_key=upload_result.get('oss_key', ''),
            user=user,
            agent=agent,
            category=category,
            access_level=access_level,
            checksum=upload_result.get('checksum', ''),
            metadata=metadata or {},
        )
        
        logger.info(f"文件上传成功: {file_record.id}, {file.name}, 用户: {user.id if user else 'N/A'}")
        
        return file_record
    
    @classmethod
    def get_download_url(cls, file_record: FileStorage, expires: int = 3600) -> str:
        """获取文件下载URL"""
        if file_record.storage_type == 'oss':
            storage = get_storage_backend('oss')
            return storage.get_url(file_record.oss_key, expires)
        else:
            storage = get_storage_backend('local')
            return storage.get_url(file_record.storage_path)
    
    @classmethod
    def get_preview_url(cls, file_record: FileStorage) -> Optional[str]:
        """获取文件预览URL"""
        if file_record.is_image:
            return file_record.storage_url
        elif file_record.is_pdf:
            # PDF预览使用iframe或专门的预览组件
            return f"/files/preview/{file_record.id}/"
        elif file_record.is_document:
            # 文档预览可能需要转换或使用在线预览服务
            return f"/files/preview/{file_record.id}/"
        return None
    
    @classmethod
    def download_file(cls, file_record: FileStorage, user=None, 
                     ip_address: str = None, user_agent: str = None) -> bytes:
        """下载文件内容"""
        storage = get_storage_backend(file_record.storage_type)
        
        try:
            if file_record.storage_type == 'oss':
                content = storage.download(file_record.oss_key)
            else:
                content = storage.download(file_record.storage_path)
            
            # 记录访问日志
            cls.log_access(file_record, user, 'download', ip_address, user_agent)
            
            return content
        except FileNotFoundError:
            logger.error(f"文件不存在: {file_record.storage_path}")
            raise
        except Exception as e:
            logger.error(f"文件下载失败: {file_record.id}, error: {e}")
            raise
    
    @classmethod
    @transaction.atomic
    def delete_file(cls, file_record: FileStorage, user=None,
                   ip_address: str = None, user_agent: str = None) -> bool:
        """删除文件"""
        try:
            # 从存储删除
            storage = get_storage_backend(file_record.storage_type)
            if file_record.storage_type == 'oss':
                storage.delete(file_record.oss_key)
            else:
                storage.delete(file_record.storage_path)
            
            # 记录访问日志
            cls.log_access(file_record, user, 'delete', ip_address, user_agent)
            
            # 软删除数据库记录
            file_record.soft_delete()
            
            logger.info(f"文件删除成功: {file_record.id}")
            return True
        except Exception as e:
            logger.error(f"文件删除失败: {file_record.id}, error: {e}")
            return False
    
    @classmethod
    def log_access(cls, file_record: FileStorage, user, action: str,
                   ip_address: str = None, user_agent: str = None):
        """记录文件访问日志"""
        FileAccessLog.objects.create(
            file=file_record,
            user=user,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent or ''
        )
        
        # 更新最后访问时间
        file_record.accessed_at = timezone.now()
        file_record.save(update_fields=['accessed_at'])
    
    @classmethod
    def check_file_permission(cls, file_record: FileStorage, user) -> bool:
        """检查用户是否有权访问文件"""
        if not file_record:
            return False
        
        # 管理员可以访问所有文件
        if user.is_staff:
            return True
        
        # 公开文件
        if file_record.access_level == 'public':
            return True
        
        # 文件所有者
        if file_record.user == user:
            return True
        
        # Agent可见的文件，检查用户是否有该Agent的访问权限
        if file_record.access_level == 'agent' and file_record.agent:
            # TODO: 实现Agent权限检查
            return True
        
        return False
    
    @classmethod
    def get_user_files(cls, user, file_type: str = None, 
                       include_deleted: bool = False) -> List[FileStorage]:
        """获取用户的文件列表"""
        queryset = FileStorage.objects.filter(user=user)
        
        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)
        
        if file_type:
            queryset = queryset.filter(file_type=file_type)
        
        return list(queryset.order_by('-created_at'))
    
    @classmethod
    def get_agent_knowledge_files(cls, agent, include_deleted: bool = False) -> List[FileStorage]:
        """获取Agent的知识库文件"""
        queryset = FileStorage.objects.filter(agent=agent, file_type='knowledge')
        
        if not include_deleted:
            queryset = queryset.filter(is_deleted=False)
        
        return list(queryset.order_by('-created_at'))


class ChunkedUploadService:
    """分片上传服务"""
    
    CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
    EXPIRES_HOURS = 24
    
    @classmethod
    def initiate_upload(cls, file_name: str, file_size: int, file_type: str,
                        user) -> ChunkedUpload:
        """初始化分片上传"""
        import math
        
        chunk_size = cls.CHUNK_SIZE
        total_chunks = math.ceil(file_size / chunk_size)
        upload_id = uuid.uuid4().hex
        
        # 生成临时存储路径
        date_str = timezone.now().strftime('%Y%m%d')
        storage_path = f'temp/chunks/{upload_id}'
        
        # 计算过期时间
        expires_at = timezone.now() + timezone.timedelta(hours=cls.EXPIRES_HOURS)
        
        upload_record = ChunkedUpload.objects.create(
            upload_id=upload_id,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            user=user,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            status='pending',
            storage_path=storage_path,
            expires_at=expires_at,
        )
        
        return upload_record
    
    @classmethod
    def upload_chunk(cls, upload_id: str, chunk_index: int, chunk_data: bytes,
                     user) -> Dict[str, Any]:
        """上传分片"""
        try:
            upload_record = ChunkedUpload.objects.get(upload_id=upload_id, user=user)
        except ChunkedUpload.DoesNotExist:
            raise ValueError("上传记录不存在")
        
        if upload_record.is_expired:
            raise ValueError("上传已过期")
        
        if upload_record.status == 'completed':
            raise ValueError("上传已完成")
        
        # 保存分片
        chunk_dir = os.path.join(settings.MEDIA_ROOT, upload_record.storage_path)
        chunk_path = os.path.join(chunk_dir, f'chunk_{chunk_index}')
        os.makedirs(chunk_dir, exist_ok=True)
        
        with open(chunk_path, 'wb') as f:
            f.write(chunk_data)
        
        # 更新上传进度
        upload_record.uploaded_chunks = max(upload_record.uploaded_chunks, chunk_index + 1)
        upload_record.status = 'uploading'
        upload_record.save(update_fields=['uploaded_chunks', 'status', 'updated_at'])
        
        return {
            'upload_id': upload_id,
            'chunk_index': chunk_index,
            'uploaded_chunks': upload_record.uploaded_chunks,
            'total_chunks': upload_record.total_chunks,
            'progress': upload_record.progress
        }
    
    @classmethod
    @transaction.atomic
    def complete_upload(cls, upload_id: str, user, file_type: str = 'attachment',
                        agent=None, category=None) -> FileStorage:
        """完成分片上传"""
        try:
            upload_record = ChunkedUpload.objects.select_for_update().get(
                upload_id=upload_id, user=user
            )
        except ChunkedUpload.DoesNotExist:
            raise ValueError("上传记录不存在")
        
        if upload_record.is_expired:
            raise ValueError("上传已过期")
        
        if upload_record.uploaded_chunks != upload_record.total_chunks:
            raise ValueError(f"还有 {upload_record.total_chunks - upload_record.uploaded_chunks} 个分片未上传")
        
        try:
            # 合并分片
            upload_record.status = 'processing'
            upload_record.save(update_fields=['status'])
            
            # 创建最终文件
            ext = os.path.splitext(upload_record.file_name)[1].lower()
            final_path = FileService.generate_storage_path(upload_record.file_name, file_type)
            
            # 读取所有分片并合并
            chunk_dir = os.path.join(settings.MEDIA_ROOT, upload_record.storage_path)
            storage_type = getattr(settings, 'DEFAULT_FILE_STORAGE', 'local')
            storage = get_storage_backend(storage_type)
            
            # 先保存到本地临时文件
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', f'{upload_id}_merged{ext}')
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, 'wb') as dest:
                for i in range(upload_record.total_chunks):
                    chunk_path = os.path.join(chunk_dir, f'chunk_{i}')
                    with open(chunk_path, 'rb') as src:
                        dest.write(src.read())
            
            # 上传到存储
            with open(temp_path, 'rb') as f:
                upload_result = storage.upload(f, final_path)
            
            # 清理临时文件
            os.remove(temp_path)
            
            # 创建文件记录
            file_record = FileStorage.objects.create(
                file_type=file_type,
                original_name=upload_record.file_name,
                file_extension=ext,
                file_size=upload_record.file_size,
                mime_type=upload_result.get('mime_type', FileService.get_mime_type(upload_record.file_name)),
                storage_type=storage_type,
                storage_path=final_path,
                storage_url=upload_result.get('url', ''),
                oss_bucket=upload_result.get('oss_bucket', ''),
                oss_key=upload_result.get('oss_key', ''),
                user=user,
                agent=agent,
                category=category,
                access_level='private',
                checksum=upload_result.get('checksum', ''),
            )
            
            # 更新上传记录
            upload_record.status = 'completed'
            upload_record.file_record = file_record
            upload_record.save(update_fields=['status', 'file_record', 'updated_at'])
            
            # 清理分片文件
            cls._cleanup_chunks(chunk_dir)
            
            logger.info(f"分片上传完成: {file_record.id}")
            return file_record
            
        except Exception as e:
            upload_record.status = 'failed'
            upload_record.error_message = str(e)
            upload_record.save(update_fields=['status', 'error_message'])
            raise
    
    @classmethod
    def cancel_upload(cls, upload_id: str, user) -> bool:
        """取消分片上传"""
        try:
            upload_record = ChunkedUpload.objects.get(upload_id=upload_id, user=user)
            upload_record.status = 'cancelled'
            upload_record.save(update_fields=['status', 'updated_at'])
            
            # 清理分片文件
            chunk_dir = os.path.join(settings.MEDIA_ROOT, upload_record.storage_path)
            cls._cleanup_chunks(chunk_dir)
            
            return True
        except ChunkedUpload.DoesNotExist:
            return False
    
    @classmethod
    def _cleanup_chunks(cls, chunk_dir: str):
        """清理分片文件"""
        try:
            if os.path.exists(chunk_dir):
                import shutil
                shutil.rmtree(chunk_dir)
        except Exception as e:
            logger.warning(f"清理分片失败: {chunk_dir}, error: {e}")


class KnowledgeBaseService:
    """知识库服务"""
    
    @classmethod
    @transaction.atomic
    def add_knowledge_file(cls, file: UploadedFile, agent, user,
                           category: FileCategory = None,
                           metadata: Dict = None) -> FileStorage:
        """添加知识库文件"""
        # 上传文件
        file_record = FileService.upload_file(
            file=file,
            user=user,
            file_type='knowledge',
            agent=agent,
            category=category,
            access_level='agent',
            metadata=metadata or {}
        )
        
        # 触发向量化任务
        from .tasks import vectorize_file_task
        vectorize_file_task.delay(file_record.id)
        
        return file_record
    
    @classmethod
    def get_vectorization_status(cls, file_record: FileStorage) -> Dict[str, Any]:
        """获取向量化状态"""
        return {
            'is_vectorized': file_record.is_vectorized,
            'status': file_record.vector_status,
            'vector_id': file_record.vector_id,
            'error': file_record.vector_error,
        }
    
    @classmethod
    def update_vectorization_result(cls, file_record: FileStorage, 
                                    vector_id: str = None,
                                    status: str = 'completed',
                                    error: str = None):
        """更新向量化结果"""
        file_record.is_vectorized = (status == 'completed')
        file_record.vector_status = status
        if vector_id:
            file_record.vector_id = vector_id
        if error:
            file_record.vector_error = error
        file_record.save(update_fields=['is_vectorized', 'vector_status', 'vector_id', 'vector_error'])
