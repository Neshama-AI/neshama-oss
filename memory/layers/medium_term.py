"""
中期记忆模块 - 用户画像、偏好与习惯

特性：
- 用户画像结构化存储
- 偏好实时更新
- 习惯模式学习
- 支持增量更新与合并
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import json
import threading


@dataclass
class UserProfile:
    """用户画像基础结构"""
    name: Optional[str] = None
    language: str = "zh-CN"
    timezone: str = "Asia/Shanghai"
    interests: List[str] = field(default_factory=list)
    profession: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "language": self.language,
            "timezone": self.timezone,
            "interests": self.interests,
            "profession": self.profession,
            "custom_fields": self.custom_fields,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        return cls(
            name=data.get("name"),
            language=data.get("language", "zh-CN"),
            timezone=data.get("timezone", "Asia/Shanghai"),
            interests=data.get("interests", []),
            profession=data.get("profession"),
            custom_fields=data.get("custom_fields", {}),
        )


@dataclass
class Preference:
    """用户偏好记录"""
    key: str  # 偏好维度: "communication_style", "response_length", etc.
    value: Any
    confidence: float = 1.0  # 置信度 0-1
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = "explicit"  # "explicit" | "implicit"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "updated_at": self.updated_at,
            "source": self.source,
        }


@dataclass
class Habit:
    """用户习惯模式"""
    pattern: str  # 习惯描述
    frequency: float  # 出现频率 0-1
    last_observed: str = field(default_factory=lambda: datetime.now().isoformat())
    context: str = "general"  # 触发上下文
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern,
            "frequency": self.frequency,
            "last_observed": self.last_observed,
            "context": self.context,
        }


class MediumTermMemory:
    """
    中期记忆 - 用户画像、偏好与习惯
    
    使用示例：
        memory = MediumTermMemory(agent_id="agent_001")
        
        # 设置用户画像
        memory.set_profile(UserProfile(name="张三", language="zh-CN"))
        
        # 更新偏好
        memory.update_preference("response_style", "简洁", confidence=0.8)
        
        # 记录习惯
        memory.record_habit("通常在工作日早上提问", context="time")
        
        # 获取偏好
        style = memory.get_preference("response_style")
    """
    
    def __init__(
        self,
        agent_id: str,
        storage_path: Optional[str] = None,
        auto_save: bool = True,
    ):
        """
        初始化中期记忆
        
        Args:
            agent_id: Agent 唯一标识
            storage_path: 存储路径
            auto_save: 是否自动保存
        """
        self._agent_id = agent_id
        self._storage_path = storage_path
        self._auto_save = auto_save
        self._lock = threading.RLock()
        
        # 数据结构
        self._profile: Optional[UserProfile] = None
        self._preferences: Dict[str, Preference] = {}
        self._habits: List[Habit] = []
        self._interaction_count: int = 0
        self._created_at: str = datetime.now().isoformat()
        self._updated_at: str = datetime.now().isoformat()
        
        # 加载已有数据
        if storage_path:
            self._load()
    
    # ========== 用户画像操作 ==========
    
    def set_profile(self, profile: UserProfile) -> None:
        """设置用户画像"""
        with self._lock:
            self._profile = profile
            self._mark_updated()
            self._save()
    
    def get_profile(self) -> Optional[UserProfile]:
        """获取用户画像"""
        with self._lock:
            return self._profile
    
    def update_profile_field(self, field: str, value: Any) -> None:
        """更新画像中的单个字段"""
        with self._lock:
            if self._profile is None:
                self._profile = UserProfile()
            
            if hasattr(self._profile, field):
                setattr(self._profile, field, value)
                self._mark_updated()
                self._save()
    
    # ========== 偏好操作 ==========
    
    def update_preference(
        self,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: str = "explicit",
    ) -> None:
        """
        更新用户偏好
        
        Args:
            key: 偏好维度
            value: 偏好值
            confidence: 置信度
            source: 来源 ("explicit" | "implicit")
        """
        with self._lock:
            existing = self._preferences.get(key)
            
            # 增量更新：合并置信度
            if existing and source == "implicit":
                new_confidence = min(1.0, (existing.confidence + confidence) / 2)
            else:
                new_confidence = confidence
            
            self._preferences[key] = Preference(
                key=key,
                value=value,
                confidence=new_confidence,
                source=source,
            )
            self._mark_updated()
            self._save()
    
    def get_preference(self, key: str) -> Optional[Preference]:
        """获取指定偏好"""
        with self._lock:
            return self._preferences.get(key)
    
    def get_all_preferences(
        self, 
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """
        获取所有偏好
        
        Args:
            min_confidence: 最低置信度阈值
            
        Returns:
            偏好字典 {key: value}
        """
        with self._lock:
            return {
                k: v.value 
                for k, v in self._preferences.items()
                if v.confidence >= min_confidence
            }
    
    def learn_preference_implicit(
        self,
        key: str,
        value: Any,
        weight: float = 0.2,
    ) -> None:
        """
        隐式学习偏好（从行为中推断）
        
        Args:
            key: 偏好维度
            value: 观察到的值
            weight: 权重，影响置信度
        """
        with self._lock:
            existing = self._preferences.get(key)
            
            if existing and existing.value == value:
                # 一致行为，提高置信度
                new_confidence = min(1.0, existing.confidence + weight)
                self._preferences[key] = Preference(
                    key=key,
                    value=value,
                    confidence=new_confidence,
                    source="implicit",
                )
            else:
                # 新观察，降低置信度
                new_confidence = weight if not existing else weight * 0.5
                self._preferences[key] = Preference(
                    key=key,
                    value=value,
                    confidence=new_confidence,
                    source="implicit",
                )
            
            self._mark_updated()
            self._save()
    
    # ========== 习惯操作 ==========
    
    def record_habit(
        self,
        pattern: str,
        frequency: float = 1.0,
        context: str = "general",
    ) -> None:
        """
        记录用户习惯
        
        Args:
            pattern: 习惯描述
            frequency: 出现频率
            context: 触发上下文
        """
        with self._lock:
            # 尝试更新已有习惯
            for habit in self._habits:
                if habit.pattern == pattern:
                    habit.frequency = (habit.frequency + frequency) / 2
                    habit.last_observed = datetime.now().isoformat()
                    break
            else:
                # 新习惯
                self._habits.append(Habit(
                    pattern=pattern,
                    frequency=frequency,
                    context=context,
                ))
            
            self._mark_updated()
            self._save()
    
    def get_habits(
        self,
        min_frequency: float = 0.3,
        context: Optional[str] = None,
    ) -> List[Habit]:
        """
        获取用户习惯
        
        Args:
            min_frequency: 最低频率阈值
            context: 按上下文筛选
            
        Returns:
            习惯列表
        """
        with self._lock:
            habits = [
                h for h in self._habits
                if h.frequency >= min_frequency
            ]
            if context:
                habits = [h for h in habits if h.context == context]
            return habits
    
    # ========== 统计与交互 ==========
    
    def increment_interaction(self) -> None:
        """增加交互计数"""
        with self._lock:
            self._interaction_count += 1
            self._mark_updated()
    
    def get_interaction_count(self) -> int:
        """获取交互次数"""
        with self._lock:
            return self._interaction_count
    
    # ========== 内部方法 ==========
    
    def _mark_updated(self) -> None:
        """标记更新时间"""
        self._updated_at = datetime.now().isoformat()
    
    def _save(self) -> None:
        """保存到文件"""
        if not self._auto_save or not self._storage_path:
            return
        
        try:
            data = self.to_dict()
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[MediumTermMemory] 保存失败: {e}")
    
    def _load(self) -> None:
        """从文件加载"""
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._profile = (
                    UserProfile.from_dict(data["profile"])
                    if data.get("profile")
                    else None
                )
                self._preferences = {
                    k: Preference(**v) for k, v in data.get("preferences", {}).items()
                }
                self._habits = [Habit(**h) for h in data.get("habits", [])]
                self._interaction_count = data.get("interaction_count", 0)
                self._created_at = data.get("created_at", datetime.now().isoformat())
                self._updated_at = data.get("updated_at", datetime.now().isoformat())
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[MediumTermMemory] 加载失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        with self._lock:
            return {
                "agent_id": self._agent_id,
                "profile": self._profile.to_dict() if self._profile else None,
                "preferences": {k: v.to_dict() for k, v in self._preferences.items()},
                "habits": [h.to_dict() for h in self._habits],
                "interaction_count": self._interaction_count,
                "created_at": self._created_at,
                "updated_at": self._updated_at,
            }
    
    def get_context_summary(self) -> str:
        """获取上下文摘要（用于注入 Agent prompt）"""
        with self._lock:
            parts = []
            
            if self._profile:
                parts.append(f"用户: {self._profile.name or '未知'}")
                parts.append(f"语言: {self._profile.language}")
                if self._profile.interests:
                    parts.append(f"兴趣: {', '.join(self._profile.interests[:5])}")
            
            prefs = self.get_all_preferences(min_confidence=0.5)
            if prefs:
                pref_str = ", ".join(f"{k}={v}" for k, v in prefs.items())
                parts.append(f"偏好: {pref_str}")
            
            habits = self.get_habits(min_frequency=0.5)
            if habits:
                habit_str = ", ".join(h.pattern for h in habits[:3])
                parts.append(f"习惯: {habit_str}")
            
            parts.append(f"交互次数: {self._interaction_count}")
            
            return "\n".join(parts)
