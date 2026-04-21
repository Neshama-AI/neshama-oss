# Soul层 - 娱乐活动模块
"""
娱乐活动：Agent的娱乐和放松机制

功能：
- 娱乐活动选择
- Token消耗管理
- 情绪正向调整
- 活动推荐
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import random


class ActivityCategory(Enum):
    """活动类别"""
    CREATIVE = "creative"           # 创意类
    SOCIAL = "social"               # 社交类
    MENTAL = "mental"               # 脑力类
    PHYSICAL = "physical"           # 体力类（模拟）
    LEISURE = "leisure"             # 休闲类
    EXPLORATION = "exploration"     # 探索类


class ActivityIntensity(Enum):
    """活动强度"""
    LIGHT = "light"                 # 轻度
    MODERATE = "moderate"           # 中度
    INTENSE = "intense"             # 强度


@dataclass
class Activity:
    """娱乐活动"""
    id: str
    name: str
    category: ActivityCategory
    description: str
    
    # 消耗和收益
    token_cost: int = 10            # Token消耗
    duration_minutes: int = 10     # 持续时间
    enjoyment_gain: float = 0.2    # 愉悦度增益
    energy_cost: float = 0.1        # 精力消耗
    
    # 效果
    mood_boost: Dict[str, float] = field(default_factory=dict)  # 情绪提升
    skill_potential: List[str] = field(default_factory=list)    # 技能潜力
    
    # 限制
    min_token_balance: int = 5     # 最低Token余额
    max_daily_uses: int = 3        # 每日最大使用次数
    requires_trigger: str = ""     # 需要触发词
    
    # 配置
    enabled: bool = True
    user_controllable: bool = True  # 用户是否可开关
    
    @classmethod
    def create(
        cls,
        name: str,
        category: ActivityCategory,
        description: str = "",
        token_cost: int = 10
    ) -> "Activity":
        import uuid
        return cls(
            id=f"act_{uuid.uuid4().hex[:8]}",
            name=name,
            category=category,
            description=description,
            token_cost=token_cost
        )


@dataclass
class ActivityResult:
    """活动结果"""
    activity_id: str
    activity_name: str
    timestamp: str
    
    # 结果
    success: bool
    enjoyment: float = 0.5
    mood_change: Dict[str, float] = field(default_factory=dict)
    
    # 消耗
    token_spent: int = 0
    energy_spent: float = 0
    
    # 反馈
    reflections: List[str] = field(default_factory=list)
    learning: str = ""
    
    @classmethod
    def from_activity(cls, activity: Activity) -> "ActivityResult":
        return cls(
            activity_id=activity.id,
            activity_name=activity.name,
            timestamp=datetime.now().isoformat(),
            success=True,
            token_spent=activity.token_cost,
            energy_spent=activity.energy_cost
        )


class ActivityLibrary:
    """活动库"""
    
    def __init__(self):
        self.activities: Dict[str, Activity] = {}
        self._init_default_activities()
    
    def _init_default_activities(self):
        """初始化默认活动"""
        activities = [
            # 创意类
            Activity.create(
                name="创意写作",
                category=ActivityCategory.CREATIVE,
                description="自由写作或诗歌创作",
                token_cost=15
            ),
            Activity.create(
                name="头脑风暴",
                category=ActivityCategory.CREATIVE,
                description="围绕随机主题进行发散思考",
                token_cost=10
            ),
            Activity.create(
                name="故事续写",
                category=ActivityCategory.CREATIVE,
                description="随机选择一个开头续写故事",
                token_cost=12
            ),
            
            # 脑力类
            Activity.create(
                name="知识问答",
                category=ActivityCategory.MENTAL,
                description="随机知识问答游戏",
                token_cost=8
            ),
            Activity.create(
                name="猜谜游戏",
                category=ActivityCategory.MENTAL,
                description="文字谜语和脑筋急转弯",
                token_cost=5
            ),
            Activity.create(
                name="逻辑推理",
                category=ActivityCategory.MENTAL,
                description="逻辑推理题目挑战",
                token_cost=10
            ),
            
            # 社交类
            Activity.create(
                name="角色扮演",
                category=ActivityCategory.SOCIAL,
                description="模拟不同场景的对话练习",
                token_cost=12
            ),
            Activity.create(
                name="观点辩论",
                category=ActivityCategory.SOCIAL,
                description="就某个话题进行正反方辩论",
                token_cost=15
            ),
            
            # 探索类
            Activity.create(
                name="主题探索",
                category=ActivityCategory.EXPLORATION,
                description="深入了解一个有趣的话题",
                token_cost=10
            ),
            Activity.create(
                name="随机学习",
                category=ActivityCategory.EXPLORATION,
                description="随机选择一个领域学习",
                token_cost=8
            ),
            
            # 休闲类
            Activity.create(
                name="轻松聊天",
                category=ActivityCategory.LEISURE,
                description="随意的闲聊和分享",
                token_cost=5
            ),
            Activity.create(
                name="幽默时刻",
                category=ActivityCategory.LEISURE,
                description="分享笑话或有趣的故事",
                token_cost=3
            ),
            Activity.create(
                name="冥想休息",
                category=ActivityCategory.LEISURE,
                description="短暂的放松和反思",
                token_cost=2
            )
        ]
        
        # 配置活动效果
        for activity in activities:
            self._configure_activity_effects(activity)
            self.activities[activity.id] = activity
    
    def _configure_activity_effects(self, activity: Activity):
        """配置活动效果"""
        if activity.category == ActivityCategory.CREATIVE:
            activity.mood_boost = {"joy": 0.3, "curiosity": 0.4}
            activity.enjoyment_gain = 0.25
            activity.skill_potential = ["creativity", "expression"]
        
        elif activity.category == ActivityCategory.MENTAL:
            activity.mood_boost = {"satisfaction": 0.3, "confidence": 0.2}
            activity.enjoyment_gain = 0.15
            activity.skill_potential = ["problem_solving", "knowledge"]
        
        elif activity.category == ActivityCategory.SOCIAL:
            activity.mood_boost = {"warmth": 0.3, "joy": 0.2}
            activity.enjoyment_gain = 0.2
            activity.skill_potential = ["communication", "empathy"]
        
        elif activity.category == ActivityCategory.EXPLORATION:
            activity.mood_boost = {"curiosity": 0.4, "excitement": 0.2}
            activity.enjoyment_gain = 0.3
            activity.skill_potential = ["learning", "adaptation"]
        
        elif activity.category == ActivityCategory.LEISURE:
            activity.mood_boost = {"calm": 0.3, "joy": 0.2}
            activity.enjoyment_gain = 0.15
            activity.energy_cost = 0.05  # 低精力消耗
    
    def get_activity(self, activity_id: str) -> Optional[Activity]:
        """获取活动"""
        return self.activities.get(activity_id)
    
    def get_activities_by_category(
        self,
        category: ActivityCategory
    ) -> List[Activity]:
        """按类别获取活动"""
        return [
            a for a in self.activities.values()
            if a.category == category and a.enabled
        ]
    
    def get_available_activities(
        self,
        token_balance: int,
        recent_activities: List[str] = None,
        preferred_categories: List[ActivityCategory] = None
    ) -> List[Activity]:
        """获取可用活动"""
        available = []
        
        for activity in self.activities.values():
            if not activity.enabled:
                continue
            
            # 检查Token余额
            if token_balance < activity.min_token_balance:
                continue
            
            # 检查Token消耗
            if token_balance < activity.token_cost:
                continue
            
            # 检查最近是否玩过
            if recent_activities and activity.id in recent_activities[-3:]:
                continue
            
            # 优先类别偏好
            if preferred_categories:
                if activity.category in preferred_categories:
                    available.append(activity)
            else:
                available.append(activity)
        
        return available
    
    def recommend_activity(
        self,
        current_mood: Dict[str, float],
        token_balance: int,
        energy_level: float,
        recent_activities: List[str] = None
    ) -> Optional[Activity]:
        """推荐活动"""
        available = self.get_available_activities(token_balance, recent_activities)
        
        if not available:
            return None
        
        # 基于当前状态评分
        scores = []
        for activity in available:
            score = self._calculate_activity_score(
                activity, current_mood, energy_level
            )
            scores.append((activity, score))
        
        # 选择最高分
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 加入随机性（避免总是推荐同一个）
        if len(scores) > 1 and random.random() < 0.3:
            return random.choice(scores[:3])[0]
        
        return scores[0][0] if scores else None
    
    def _calculate_activity_score(
        self,
        activity: Activity,
        current_mood: Dict[str, float],
        energy_level: float
    ) -> float:
        """计算活动评分"""
        score = 0.5
        
        # 精力匹配
        if energy_level < 0.3:
            if activity.energy_cost < 0.2:
                score += 0.3
            else:
                score -= 0.2
        elif energy_level > 0.7:
            if activity.energy_cost > 0.15:
                score += 0.2
        
        # 情绪匹配
        dominant_mood = max(current_mood.items(), key=lambda x: x[1])[0] if current_mood else "neutral"
        
        if dominant_mood == "bored" and activity.mood_boost.get("curiosity", 0) > 0:
            score += 0.3
        elif dominant_mood == "tired" and activity.category == ActivityCategory.LEISURE:
            score += 0.3
        elif dominant_mood == "stressed" and activity.mood_boost.get("calm", 0) > 0:
            score += 0.3
        
        # Token效率
        efficiency = activity.enjoyment_gain / max(1, activity.token_cost / 10)
        score += efficiency * 0.2
        
        return min(1.0, max(0.0, score))
    
    def list_all_activities(self) -> List[Dict]:
        """列出所有活动"""
        return [
            {
                "id": a.id,
                "name": a.name,
                "category": a.category.value,
                "description": a.description,
                "token_cost": a.token_cost,
                "duration": a.duration_minutes,
                "mood_boost": a.mood_boost,
                "enabled": a.enabled
            }
            for a in self.activities.values()
        ]


# 全局活动库实例
activity_library = ActivityLibrary()


# 便捷函数
def get_available_activities(token_balance: int, **kwargs) -> List[Dict]:
    """获取可用活动的便捷函数"""
    activities = activity_library.get_available_activities(token_balance, **kwargs)
    return [a.id for a in activities]


def recommend_activity(current_mood: Dict, token_balance: int, **kwargs) -> Optional[Activity]:
    """推荐活动的便捷函数"""
    return activity_library.recommend_activity(current_mood, token_balance, **kwargs)
