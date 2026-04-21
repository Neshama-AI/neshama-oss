# -*- coding: utf-8 -*-
"""
Neshama Agent 文件管理模块
=================

本模块提供完整的文件管理功能，包括用户文件和Agent知识库管理。

## 主要功能

### 1. 文件存储
- 本地存储
- 阿里云OSS存储
- 支持扩展其他存储后端

### 2. 文件类型
- 用户附件（图片、文档、音频、视频等）
- Agent知识库文件
- 用户头像

### 3. 访问权限
- private: 仅本人可见
- agent: Agent可见
- public: 公开

### 4. 分片上传
- 支持大文件分片上传
- 断点续传
- 上传进度跟踪

### 5. 知识库向量化
- 文件自动向量化（预留接口）
- 支持多种文档格式

## 安装与配置

### 1. 添加到Django INSTALLED_APPS

```python
INSTALLED_APPS = [
    ...
    'Neshama.files',
]
```

### 2. 配置存储后端

```python
# 本地存储（默认）
DEFAULT_FILE_STORAGE = 'local'
MEDIA_URL = '/media/'
MEDIA_ROOT = 'media/uploads'

# 阿里云OSS
DEFAULT_FILE_STORAGE = 'oss'
OSS_BUCKET_NAME = 'your-bucket'
OSS_ENDPOINT = 'oss-cn-hangzhou.aliyuncs.com'
OSS_ACCESS_KEY_ID = 'your-access-key'
OSS_ACCESS_KEY_SECRET = 'your-secret-key'
OSS_BASE_URL = 'https://your-bucket.oss-cn-hangzhou.aliyuncs.com'
```

### 3. 配置上传限制

```python
MAX_FILE_SIZE_MB = 50  # 最大文件大小（MB）
FILE_RETENTION_DAYS = 30  # 软删除文件保留天数
```

### 4. 添加URL路由

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('files/', include('Neshama.files.urls')),
]
```

## API 接口

### 文件上传

```
POST /files/upload/
Content-Type: multipart/form-data

{
    "file": <file>,
    "file_type": "attachment",  # attachment/knowledge/avatar
    "agent_id": 1,  # 可选
    "category_id": 1,  # 可选
    "access_level": "private"  # private/agent/public
}
```

### 文件下载

```
GET /files/{file_id}/download/
```

### 文件预览

```
GET /files/{file_id}/preview/
```

### 文件列表

```
GET /files/files/
GET /files/files/?file_type=attachment
GET /files/files/?file_type=knowledge
```

### 分片上传

```
# 1. 初始化上传
POST /files/chunked/initiate/
{
    "file_name": "large_file.zip",
    "file_size": 104857600,
    "file_type": "attachment"
}

# 2. 上传分片
POST /files/chunked/upload/
{
    "upload_id": "xxx",
    "chunk_index": 0,
    "chunk": <binary>
}

# 3. 完成上传
POST /files/chunked/complete/
{
    "upload_id": "xxx",
    "file_type": "attachment"
}
```

### 存储统计

```
GET /files/stats/
```

## 数据模型

### FileStorage
文件存储主表

| 字段 | 类型 | 说明 |
|------|------|------|
| file_type | CharField | 文件类型 |
| original_name | CharField | 原始文件名 |
| file_size | BigIntegerField | 文件大小 |
| storage_type | CharField | 存储类型 |
| storage_path | CharField | 存储路径 |
| user | ForeignKey | 所属用户 |
| agent | ForeignKey | 关联Agent |
| access_level | CharField | 访问权限 |
| is_vectorized | BooleanField | 是否已向量化 |

### FileCategory
文件分类

### ChunkedUpload
分片上传记录

### FileAccessLog
访问日志

## Celery 任务

```python
# 向量化文件
from Neshama.files.tasks import vectorize_file_task
vectorize_file_task.delay(file_id)

# 清理过期上传
from Neshama.files.tasks import cleanup_expired_uploads
cleanup_expired_uploads.delay()

# 清理软删除文件
from Neshama.files.tasks import cleanup_soft_deleted_files
cleanup_soft_deleted_files.delay()
```

## 扩展存储后端

```python
from Neshama.files.storage import BaseStorageBackend, StorageFactory

class S3StorageBackend(BaseStorageBackend):
    # 实现存储后端接口
    pass

# 注册新的存储后端
StorageFactory.register_backend('s3', S3StorageBackend)
```

## 许可证

Neshama Agent Project
"""

__version__ = '1.0.0'
__author__ = 'Neshama Team'
