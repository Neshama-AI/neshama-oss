"""
Storage Layer - 存储接口抽象
"""

from .file_storage import FileStorage
from .vector_store import VectorStore

__all__ = [
    "FileStorage",
    "VectorStore",
]
