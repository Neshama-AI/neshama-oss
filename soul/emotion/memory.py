# Soul层 - 情绪记忆模块
"""
情绪记忆：存储和管理长期情绪模式

功能：
- 情绪事件存储
- 情绪模式识别
- 情绪趋势分析
- 周期性情绪报告
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json


class EmotionPatternType(Enum):
    """情绪模式类型"""
    RECURRING = "recurring"           # 周期性模式
    TRIGGERED = "triggered"           # 触发性模式
    SEASONAL = "seasonal"             # 季节性模式
    REACTION = "reaction"             # 反应性模式
    GROWTH = "growth"                 # 成长性模式


@dataclass
class EmotionEvent:
    """情绪事件"""
    id: str
    timestamp: str
    user_id: str
    
    # 情绪数据
    emotions: List[Dict]  # 识别的情绪
    dominant_emotion: str
    intensity: float
    
    # 上下文
    trigger: str = ""           # 触发因素
    context: str = ""           # 场景描述
    user_message: str = ""      # 用户消息摘要
    response: str = ""          # Agent响应摘要
    
    # 元数据
    interaction_id: str = ""
    session_id: str = ""
    resolved: bool = False      # 是否已解决
    notes: str = ""
    
    @classmethod
    def create(
        cls,
        user_id: str,
        emotions: List[Dict],
        user_message: str = "",
        trigger: str = "",
        context: str = ""
    ) -> "EmotionEvent":
        """创建情绪事件"""
        import uuid
        event_id = f"emo_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        dominant = emotions[0] if emotions else {}
        
        return cls(
            id=event_id,
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            emotions=emotions,
            dominant_emotion=dominant.get("category", "unknown"),
            intensity=dominant.get("intensity", 0.5),
            trigger=trigger,
            context=context,
            user_message=user_message[:200] if user_message else ""
        )
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "emotions": self.emotions,
            "dominant_emotion": self.dominant_emotion,
            "intensity": self.intensity,
            "trigger": self.trigger,
            "context": self.context,
            "user_message": self.user_message,
            "response": self.response,
            "interaction_id": self.interaction_id,
            "session_id": self.session_id,
            "resolved": self.resolved,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EmotionEvent":
        return cls(**data)


@dataclass
class EmotionPattern:
    """情绪模式"""
    id: str
    pattern_type: EmotionPatternType
    
    # 模式特征
    trigger_keywords: List[str] = field(default_factory=list)
    emotion_sequence: List[str] = field(default_factory=list)
    typical_intensity: float = 0.5
    
    # 统计
    occurrence_count: int = 0
    first_occurrence: str = ""
    last_occurrence: str = ""
    success_rate: float = 0.0  # 解决成功率
    
    # 建议
    effective_strategies: List[str] = field(default_factory=list)
    notes: str = ""
    
    @classmethod
    def create(
        cls,
        pattern_type: EmotionPatternType,
        trigger_keywords: List[str] = None
    ) -> "EmotionPattern":
        """创建情绪模式"""
        import uuid
        pattern_id = f"pattern_{pattern_type.value}_{uuid.uuid4().hex[:6]}"
        
        return cls(
            id=pattern_id,
            pattern_type=pattern_type,
            trigger_keywords=trigger_keywords or []
        )


class EmotionMemory:
    """情绪记忆管理器"""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id
        self.events: Dict[str, EmotionEvent] = {}  # event_id -> event
        self.patterns: Dict[str, EmotionPattern] = {}  # pattern_id -> pattern
        self.event_index: List[str] = []  # 按时间顺序的事件ID
        
        # 统计数据
        self.emotion_stats: Dict[str, Dict] = {}
        self._init_stats()
    
    def _init_stats(self):
        """初始化统计数据"""
        emotion_categories = [
            "joy", "sadness", "anger", "fear",
            "surprise", "disgust", "trust", "anticipation"
        ]
        for emotion in emotion_categories:
            self.emotion_stats[emotion] = {
                "count": 0,
                "total_intensity": 0.0,
                "avg_intensity": 0.0,
                "max_intensity": 0.0,
                "min_intensity": 1.0
            }
    
    def record_event(
        self,
        emotions: List[Dict],
        user_message: str = "",
        trigger: str = "",
        context: str = "",
        interaction_id: str = "",
        session_id: str = ""
    ) -> EmotionEvent:
        """记录情绪事件"""
        event = EmotionEvent.create(
            user_id=self.user_id or "default",
            emotions=emotions,
            user_message=user_message,
            trigger=trigger,
            context=context
        )
        event.interaction_id = interaction_id
        event.session_id = session_id
        
        # 存储
        self.events[event.id] = event
        self.event_index.append(event.id)
        
        # 更新统计
        self._update_stats(emotions)
        
        # 检测和更新模式
        self._detect_patterns(event)
        
        return event
    
    def update_event(
        self,
        event_id: str,
        resolved: bool = None,
        response: str = None,
        notes: str = None
    ):
        """更新事件"""
        if event_id not in self.events:
            return
        
        event = self.events[event_id]
        if resolved is not None:
            event.resolved = resolved
        if response is not None:
            event.response = response
        if notes is not None:
            event.notes = notes
    
    def _update_stats(self, emotions: List[Dict]):
        """更新情绪统计"""
        for emotion_data in emotions:
            category = emotion_data.get("category", "unknown")
            intensity = emotion_data.get("intensity", 0.5)
            
            if category in self.emotion_stats:
                stats = self.emotion_stats[category]
                stats["count"] += 1
                stats["total_intensity"] += intensity
                stats["avg_intensity"] = stats["total_intensity"] / stats["count"]
                stats["max_intensity"] = max(stats["max_intensity"], intensity)
                stats["min_intensity"] = min(stats["min_intensity"], intensity)
    
    def _detect_patterns(self, event: EmotionEvent):
        """检测情绪模式"""
        # 检测触发词模式
        for keyword in event.trigger.split():
            if len(keyword) < 2:
                continue
            
            # 查找是否有匹配的模式
            existing_pattern = None
            for pattern in self.patterns.values():
                if pattern.pattern_type == EmotionPatternType.TRIGGERED:
                    if keyword in pattern.trigger_keywords:
                        existing_pattern = pattern
                        break
            
            if existing_pattern:
                # 更新现有模式
                existing_pattern.occurrence_count += 1
                existing_pattern.last_occurrence = event.timestamp
                if event.resolved:
                    existing_pattern.success_rate = (
                        existing_pattern.success_rate * 0.9 + 0.1
                    )
            else:
                # 创建新模式
                new_pattern = EmotionPattern.create(
                    pattern_type=EmotionPatternType.TRIGGERED,
                    trigger_keywords=[keyword]
                )
                new_pattern.occurrence_count = 1
                new_pattern.first_occurrence = event.timestamp
                new_pattern.last_occurrence = event.timestamp
                self.patterns[new_pattern.id] = new_pattern
    
    def get_recent_events(
        self,
        limit: int = 10,
        emotion_filter: str = None
    ) -> List[EmotionEvent]:
        """获取最近的事件"""
        events = []
        for event_id in reversed(self.event_index):
            event = self.events.get(event_id)
            if event:
                if emotion_filter is None or event.dominant_emotion == emotion_filter:
                    events.append(event)
                    if len(events) >= limit:
                        break
        return events
    
    def get_emotion_trend(
        self,
        days: int = 7,
        granularity: str = "day"
    ) -> List[Dict]:
        """获取情绪趋势"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 按时间分组
        trend = {}
        
        for event_id in self.event_index:
            event = self.events.get(event_id)
            if not event:
                continue
            
            event_time = datetime.fromisoformat(event.timestamp)
            if event_time < start_date or event_time > end_date:
                continue
            
            # 确定时间桶
            if granularity == "day":
                key = event_time.strftime("%Y-%m-%d")
            elif granularity == "hour":
                key = event_time.strftime("%Y-%m-%d %H:00")
            else:
                key = event_time.strftime("%Y-%m-%d")
            
            if key not in trend:
                trend[key] = {
                    "timestamp": key,
                    "emotions": {},
                    "avg_intensity": 0,
                    "count": 0
                }
            
            # 记录情绪
            for emotion_data in event.emotions:
                cat = emotion_data["category"]
                if cat not in trend[key]["emotions"]:
                    trend[key]["emotions"][cat] = []
                trend[key]["emotions"][cat].append(emotion_data["intensity"])
            
            trend[key]["count"] += 1
        
        # 计算平均值
        result = []
        for key in sorted(trend.keys()):
            data = trend[key]
            total_intensity = 0
            total_count = 0
            for intensities in data["emotions"].values():
                total_intensity += sum(intensities)
                total_count += len(intensities)
            
            data["avg_intensity"] = total_intensity / total_count if total_count > 0 else 0
            result.append(data)
        
        return result
    
    def get_pattern_insights(self) -> List[Dict]:
        """获取模式洞察"""
        insights = []
        
        for pattern in self.patterns.values():
            if pattern.occurrence_count < 2:
                continue
            
            insight = {
                "pattern_id": pattern.id,
                "type": pattern.pattern_type.value,
                "triggers": pattern.trigger_keywords,
                "occurrences": pattern.occurrence_count,
                "last_seen": pattern.last_occurrence,
                "resolution_rate": pattern.success_rate,
                "effective_approaches": pattern.effective_strategies
            }
            insights.append(insight)
        
        # 按出现次数排序
        insights.sort(key=lambda x: x["occurrences"], reverse=True)
        return insights
    
    def get_summary(self) -> Dict:
        """获取情绪摘要"""
        total_events = len(self.events)
        resolved_events = sum(1 for e in self.events.values() if e.resolved)
        
        return {
            "total_events": total_events,
            "resolved_events": resolved_events,
            "resolution_rate": resolved_events / total_events if total_events > 0 else 0,
            "emotion_distribution": {
                cat: stats["count"]
                for cat, stats in self.emotion_stats.items()
                if stats["count"] > 0
            },
            "most_common_emotion": max(
                self.emotion_stats.items(),
                key=lambda x: x[1]["count"]
            )[0] if self.emotion_stats else None,
            "avg_intensity": sum(
                stats["avg_intensity"] * stats["count"]
                for stats in self.emotion_stats.values()
            ) / max(total_events, 1),
            "pattern_count": len([p for p in self.patterns.values() if p.occurrence_count >= 2])
        }
    
    def export_data(self) -> Dict:
        """导出数据"""
        return {
            "user_id": self.user_id,
            "export_time": datetime.now().isoformat(),
            "events": [e.to_dict() for e in self.events.values()],
            "patterns": [
                {
                    "id": p.id,
                    "type": p.pattern_type.value,
                    "triggers": p.trigger_keywords,
                    "occurrences": p.occurrence_count,
                    "success_rate": p.success_rate
                }
                for p in self.patterns.values()
            ],
            "stats": self.emotion_stats
        }
    
    def import_data(self, data: Dict):
        """导入数据"""
        self.user_id = data.get("user_id", self.user_id)
        
        # 导入事件
        for event_data in data.get("events", []):
            event = EmotionEvent.from_dict(event_data)
            self.events[event.id] = event
            if event.id not in self.event_index:
                self.event_index.append(event.id)
        
        # 导入统计
        if "stats" in data:
            self.emotion_stats = data["stats"]


# 用户情绪记忆存储（实际应用中应使用数据库）
USER_EMOTION_MEMORIES: Dict[str, EmotionMemory] = {}


def get_emotion_memory(user_id: str) -> EmotionMemory:
    """获取用户的情绪记忆"""
    if user_id not in USER_EMOTION_MEMORIES:
        USER_EMOTION_MEMORIES[user_id] = EmotionMemory(user_id)
    return USER_EMOTION_MEMORIES[user_id]


def record_emotion(user_id: str, emotions: List[Dict], **kwargs) -> EmotionEvent:
    """记录的便捷函数"""
    memory = get_emotion_memory(user_id)
    return memory.record_event(emotions, **kwargs)
