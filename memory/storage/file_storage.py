"""
文件存储模块 - 支持 JSON/YAML 格式

特性：
- 统一的存储接口
- 自动创建目录
- 线程安全
- 支持多种序列化格式
"""

from typing import Any, Dict, Optional, List
from pathlib import Path
import json
import yaml
import threading
import os


class FileStorage:
    """
    文件存储 - 通用文件读写接口
    
    支持格式：
    - JSON: .json
    - YAML: .yaml, .yml
    
    使用示例：
        storage = FileStorage(base_path="./data")
        
        # 保存数据
        storage.save("user_profile", {"name": "张三", "age": 25})
        
        # 读取数据
        profile = storage.load("user_profile")
        
        # 保存记忆
        storage.save_memory("agent_001", memory_data)
    """
    
    def __init__(
        self,
        base_path: str = "./memory_data",
        format: str = "json",
        auto_mkdir: bool = True,
    ):
        """
        初始化文件存储
        
        Args:
            base_path: 基础存储路径
            format: 存储格式 ("json" | "yaml")
            auto_mkdir: 是否自动创建目录
        """
        self._base_path = Path(base_path)
        self._format = format.lower()
        self._lock = threading.RLock()
        
        if auto_mkdir:
            self._base_path.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        key: str,
        data: Any,
        sub_path: Optional[str] = None,
    ) -> bool:
        """
        保存数据到文件
        
        Args:
            key: 文件名（不含扩展名）
            data: 要保存的数据
            sub_path: 子目录路径
            
        Returns:
            是否成功
        """
        with self._lock:
            try:
                file_path = self._get_path(key, sub_path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                serialized = self._serialize(data)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(serialized)
                
                return True
            except Exception as e:
                print(f"[FileStorage] 保存失败 {key}: {e}")
                return False
    
    def load(
        self,
        key: str,
        sub_path: Optional[str] = None,
        default: Any = None,
    ) -> Any:
        """
        从文件加载数据
        
        Args:
            key: 文件名（不含扩展名）
            sub_path: 子目录路径
            default: 默认值（文件不存在时返回）
            
        Returns:
            加载的数据或默认值
        """
        with self._lock:
            try:
                file_path = self._get_path(key, sub_path)
                
                if not file_path.exists():
                    return default
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                return self._deserialize(content)
            except Exception as e:
                print(f"[FileStorage] 加载失败 {key}: {e}")
                return default
    
    def delete(
        self,
        key: str,
        sub_path: Optional[str] = None,
    ) -> bool:
        """
        删除文件
        
        Args:
            key: 文件名
            sub_path: 子目录路径
            
        Returns:
            是否成功
        """
        with self._lock:
            try:
                file_path = self._get_path(key, sub_path)
                if file_path.exists():
                    file_path.unlink()
                return True
            except Exception as e:
                print(f"[FileStorage] 删除失败 {key}: {e}")
                return False
    
    def exists(
        self,
        key: str,
        sub_path: Optional[str] = None,
    ) -> bool:
        """检查文件是否存在"""
        with self._lock:
            file_path = self._get_path(key, sub_path)
            return file_path.exists()
    
    def list_keys(
        self,
        sub_path: Optional[str] = None,
        pattern: Optional[str] = None,
    ) -> List[str]:
        """
        列出文件键
        
        Args:
            sub_path: 子目录路径
            pattern: 文件名匹配模式
            
        Returns:
            文件名列表（不含扩展名）
        """
        with self._lock:
            try:
                dir_path = self._base_path
                if sub_path:
                    dir_path = dir_path / sub_path
                
                if not dir_path.exists():
                    return []
                
                ext = self._get_extension()
                keys = []
                
                for file_path in dir_path.glob(f"*{ext}"):
                    keys.append(file_path.stem)
                
                if pattern:
                    keys = [k for k in keys if pattern in k]
                
                return sorted(keys)
            except Exception as e:
                print(f"[FileStorage] 列出失败: {e}")
                return []
    
    def save_memory(
        self,
        agent_id: str,
        memory_data: Dict[str, Any],
    ) -> bool:
        """保存 Agent 记忆（便捷方法）"""
        return self.save(agent_id, memory_data, sub_path="memories")
    
    def load_memory(
        self,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """加载 Agent 记忆（便捷方法）"""
        return self.load(agent_id, sub_path="memories")
    
    def list_agents(self) -> List[str]:
        """列出所有 Agent ID"""
        return self.list_keys(sub_path="memories")
    
    def _get_path(
        self,
        key: str,
        sub_path: Optional[str] = None,
    ) -> Path:
        """获取完整文件路径"""
        path = self._base_path
        if sub_path:
            path = path / sub_path
        return path / f"{key}{self._get_extension()}"
    
    def _get_extension(self) -> str:
        """获取文件扩展名"""
        return {".json": "", "json": ""}.get(self._format, self._format)
    
    def _serialize(self, data: Any) -> str:
        """序列化数据"""
        if self._format in ("yaml", "yml"):
            return yaml.dump(data, allow_unicode=True, default_flow_style=False)
        else:
            return json.dumps(data, ensure_ascii=False, indent=2)
    
    def _deserialize(self, content: str) -> Any:
        """反序列化数据"""
        if self._format in ("yaml", "yml"):
            return yaml.safe_load(content)
        else:
            return json.loads(content)
    
    @property
    def base_path(self) -> str:
        """获取基础路径"""
        return str(self._base_path)
