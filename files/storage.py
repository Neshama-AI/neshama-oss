# -*- coding: utf-8 -*-
"""
文件存储后端模块
支持本地存储和阿里云OSS
"""

import os
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

logger = logging.getLogger(__name__)


class BaseStorageBackend(ABC):
    """存储后端基类"""
    
    @abstractmethod
    def upload(self, file: UploadedFile, path: str, **kwargs) -> Dict[str, Any]:
        """
        上传文件
        
        Args:
            file: 上传的文件对象
            path: 存储路径
            
        Returns:
            dict: 包含 url, storage_path 等信息
        """
        pass
    
    @abstractmethod
    def download(self, path: str, dest: Optional[str] = None) -> bytes:
        """下载文件"""
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        pass
    
    @abstractmethod
    def get_url(self, path: str, expires: int = 3600) -> str:
        """获取文件访问URL"""
        pass
    
    def get_file_hash(self, file: BinaryIO) -> str:
        """计算文件MD5哈希"""
        md5 = hashlib.md5()
        for chunk in file.chunks():
            md5.update(chunk)
        return md5.hexdigest()


class LocalStorageBackend(BaseStorageBackend):
    """本地存储后端"""
    
    def __init__(self, base_url: str = None, base_path: str = None):
        self.base_url = base_url or getattr(settings, 'MEDIA_URL', '/media/')
        self.base_path = base_path or getattr(settings, 'MEDIA_ROOT', 'media/uploads')
    
    def upload(self, file: UploadedFile, path: str, **kwargs) -> Dict[str, Any]:
        """上传文件到本地存储"""
        full_path = os.path.join(self.base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # 计算文件哈希
        file.seek(0)
        checksum = self.get_file_hash(file)
        file.seek(0)
        
        # 保存文件
        with open(full_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        url = f"{self.base_url.rstrip('/')}/{path}"
        
        return {
            'url': url,
            'storage_path': path,
            'checksum': checksum,
            'storage_type': 'local'
        }
    
    def download(self, path: str, dest: Optional[str] = None) -> bytes:
        """从本地下载文件"""
        full_path = os.path.join(self.base_path, path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {path}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
    def delete(self, path: str) -> bool:
        """删除本地文件"""
        full_path = os.path.join(self.base_path, path)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                # 尝试清理空目录
                dir_path = os.path.dirname(full_path)
                self._cleanup_empty_dirs(dir_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除文件失败: {path}, error: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        """检查本地文件是否存在"""
        full_path = os.path.join(self.base_path, path)
        return os.path.exists(full_path)
    
    def get_url(self, path: str, expires: int = 3600) -> str:
        """获取本地文件URL"""
        return f"{self.base_url.rstrip('/')}/{path}"
    
    def _cleanup_empty_dirs(self, dir_path: str):
        """清理空目录"""
        try:
            if os.path.isdir(dir_path) and not os.listdir(dir_path):
                os.rmdir(dir_path)
                # 递归清理上层空目录
                parent = os.path.dirname(dir_path)
                if parent != self.base_path:
                    self._cleanup_empty_dirs(parent)
        except Exception:
            pass


class OSSStorageBackend(BaseStorageBackend):
    """阿里云OSS存储后端"""
    
    def __init__(self, bucket_name: str = None, endpoint: str = None, 
                 access_key_id: str = None, access_key_secret: str = None,
                 base_url: str = None):
        self.bucket_name = bucket_name or getattr(settings, 'OSS_BUCKET_NAME', '')
        self.endpoint = endpoint or getattr(settings, 'OSS_ENDPOINT', '')
        self.access_key_id = access_key_id or getattr(settings, 'OSS_ACCESS_KEY_ID', '')
        self.access_key_secret = access_key_secret or getattr(settings, 'OSS_ACCESS_KEY_SECRET', '')
        self.base_url = base_url or getattr(settings, 'OSS_BASE_URL', '')
        self._client = None
    
    @property
    def client(self):
        """懒加载OSS客户端"""
        if self._client is None:
            try:
                import oss2
                auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                self._client = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            except ImportError:
                raise ImportError("请安装阿里云OSS SDK: pip install oss2")
            except Exception as e:
                logger.error(f"OSS客户端初始化失败: {e}")
                raise
        return self._client
    
    def upload(self, file: UploadedFile, path: str, **kwargs) -> Dict[str, Any]:
        """上传文件到OSS"""
        file.seek(0)
        content = file.read()
        file.seek(0)
        
        # 计算文件哈希
        checksum = hashlib.md5(content).hexdigest()
        
        # 上传到OSS
        result = self.client.put_object(path, content)
        
        if result.status != 200:
            raise Exception(f"OSS上传失败: status={result.status}")
        
        url = f"{self.base_url}/{path}" if self.base_url else path
        
        return {
            'url': url,
            'storage_path': path,
            'checksum': checksum,
            'storage_type': 'oss',
            'oss_bucket': self.bucket_name,
            'oss_key': path
        }
    
    def download(self, path: str, dest: Optional[str] = None) -> bytes:
        """从OSS下载文件"""
        try:
            result = self.client.get_object(path)
            content = result.read()
            
            if dest:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, 'wb') as f:
                    f.write(content)
            
            return content
        except oss2.exceptions.NoSuchKey:
            raise FileNotFoundError(f"OSS文件不存在: {path}")
        except Exception as e:
            logger.error(f"OSS下载失败: {path}, error: {e}")
            raise
    
    def delete(self, path: str) -> bool:
        """删除OSS文件"""
        try:
            result = self.client.delete_object(path)
            return result.status in [200, 204]
        except Exception as e:
            logger.error(f"OSS删除失败: {path}, error: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        """检查OSS文件是否存在"""
        try:
            return self.client.object_exists(path)
        except Exception:
            return False
    
    def get_url(self, path: str, expires: int = 3600) -> str:
        """获取OSS文件访问URL（带签名）"""
        try:
            from datetime import datetime, timedelta
            expiry = datetime.utcnow() + timedelta(seconds=expires)
            return self.client.sign_url('GET', path, expires)
        except Exception as e:
            logger.error(f"OSS URL签名失败: {path}, error: {e}")
            return f"{self.base_url}/{path}"


class StorageFactory:
    """存储后端工厂"""
    
    _backends = {
        'local': LocalStorageBackend,
        'oss': OSSStorageBackend,
    }
    
    @classmethod
    def get_backend(cls, storage_type: str = 'local') -> BaseStorageBackend:
        """获取存储后端实例"""
        backend_class = cls._backends.get(storage_type)
        if not backend_class:
            raise ValueError(f"不支持的存储类型: {storage_type}")
        return backend_class()
    
    @classmethod
    def register_backend(cls, name: str, backend_class: type):
        """注册新的存储后端"""
        cls._backends[name] = backend_class


class FileStorageManager:
    """文件存储管理器"""
    
    def __init__(self):
        self.default_storage = getattr(settings, 'DEFAULT_FILE_STORAGE', 'local')
    
    def get_storage(self, storage_type: str = None) -> BaseStorageBackend:
        """获取存储后端"""
        return StorageFactory.get_backend(storage_type or self.default_storage)
    
    def upload_file(self, file: UploadedFile, path: str, 
                   storage_type: str = None) -> Dict[str, Any]:
        """上传文件"""
        storage = self.get_storage(storage_type)
        return storage.upload(file, path)
    
    def delete_file(self, path: str, storage_type: str = None) -> bool:
        """删除文件"""
        storage = self.get_storage(storage_type)
        return storage.delete(path)
    
    def get_file_url(self, path: str, storage_type: str = None,
                     expires: int = 3600) -> str:
        """获取文件URL"""
        storage = self.get_storage(storage_type)
        return storage.get_url(path, expires)


# 全局存储管理器实例
storage_manager = FileStorageManager()


def get_storage_backend(storage_type: str = None) -> BaseStorageBackend:
    """获取存储后端的快捷方法"""
    return storage_manager.get_storage(storage_type)
