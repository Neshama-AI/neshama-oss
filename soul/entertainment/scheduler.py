# Soul层 - 娱乐调度模块
"""
娱乐调度：根据状态和时机自动安排娱乐活动

功能：
- 状态监测与触发
- 活动调度决策
- Token预算管理
- 用户开关控制
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import random


class SchedulerState(Enum):
    """调度器状态"""
    IDLE = "idle"                  # 空闲
    MONITORING = "monitoring"      # 监控中
    RECOMMENDING = "recommending"  # 推荐中
    ACTIVE = "active"              # 进行中
    COOLDOWN = "cooldown"          # 冷却中


class TriggerCondition(Enum):
    """触发条件"""
    LOW_MOOD = "low_mood"          # 情绪低落
    BOREDOM = "boredom"           # 感到无聊
    HIGH_STRESS = "high_stress"   # 压力大
    IDLE_TIME = "idle_time"       # 空闲时间
    TOKEN_BONUS = "token_bonus"   # Token充裕
    USER_REQUEST = "user_request" # 用户请求
    PERIODIC = "periodic"         # 周期性


@dataclass
class ScheduleRule:
    """调度规则"""
    id: str
    trigger: TriggerCondition
    condition: Callable[[Dict], bool]  # 触发条件函数
    
    # 行动配置
    recommended_activity_type: str = ""  # 推荐的类型
    priority: int = 1                   # 优先级（越高越先触发）
    max_daily_triggers: int = 5         # 每日最大触发次数
    
    # 冷却
    cooldown_minutes: int = 30         # 冷却时间
    last_triggered: Optional[datetime] = None
    
    # 启用状态
    enabled: bool = True
    
    @classmethod
    def create(
        cls,
        trigger: TriggerCondition,
        condition: Callable[[Dict], bool],
        **kwargs
    ) -> "ScheduleRule":
        import uuid
        return cls(
            id=f"rule_{uuid.uuid4().hex[:8]}",
            trigger=trigger,
            condition=condition,
            **kwargs
        )


@dataclass
class ScheduleContext:
    """调度上下文"""
    # 当前状态
    current_mood: Dict[str, float] = field(default_factory=dict)
    energy_level: float = 0.5
    stress_level: float = 0.3
    boredom_level: float = 0.4
    
    # Token状态
    token_balance: int = 100
    daily_token_budget: int = 50
    token_used_today: int = 0
    
    # 时间状态
    time_of_day: str = ""       # morning, afternoon, evening, night
    is_weekend: bool = False
    idle_minutes: int = 0       # 空闲分钟数
    
    # 统计
    activities_today: int = 0
    last_activity_time: Optional[str] = None
    consecutive_boring_interactions: int = 0
    
    @classmethod
    def create(cls, **kwargs) -> "ScheduleContext":
        ctx = cls(**kwargs)
        ctx.time_of_day = cls._get_time_of_day()
        return ctx
    
    @staticmethod
    def _get_time_of_day() -> str:
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"


@dataclass
class ScheduleDecision:
    """调度决策"""
    decision_type: str  # "recommend", "defer", "block"
    activity: Optional[Any] = None
    reason: str = ""
    trigger: TriggerCondition = None
    confidence: float = 0.5
    
    # 后续建议
    suggestion: str = ""
    alternative_reason: str = ""


class EntertainmentScheduler:
    """娱乐调度器"""
    
    def __init__(self):
        self.state = SchedulerState.IDLE
        self.rules: List[ScheduleRule] = []
        self.daily_stats: Dict[str, int] = {
            "activities_started": 0,
            "activities_completed": 0,
            "tokens_spent": 0,
            "recommendations_made": 0,
            "recommendations_accepted": 0
        }
        self.schedule_log: List[Dict] = []
        
        # 用户控制
        self.user_enabled: bool = True  # 用户总开关
        self.auto_mode: bool = True     # 是否自动推荐
        self.max_daily_activities: int = 5
        
        # 初始化默认规则
        self._init_default_rules()
    
    def _init_default_rules(self):
        """初始化默认调度规则"""
        
        # 低情绪规则
        self.rules.append(ScheduleRule.create(
            trigger=TriggerCondition.LOW_MOOD,
            condition=lambda ctx: any(
                mood in ["sadness", "anger", "fear"] and val > 0.5
                for mood, val in ctx.current_mood.items()
            ),
            priority=3,
            cooldown_minutes=20
        ))
        
        # 无聊规则
        self.rules.append(ScheduleRule.create(
            trigger=TriggerCondition.BOREDOM,
            condition=lambda ctx: ctx.boredom_level > 0.6 or ctx.consecutive_boring_interactions > 3,
            priority=2,
            cooldown_minutes=30
        ))
        
        # 高压力规则
        self.rules.append(ScheduleRule.create(
            trigger=TriggerCondition.HIGH_STRESS,
            condition=lambda ctx: ctx.stress_level > 0.7,
            priority=4,
            cooldown_minutes=45
        ))
        
        # 空闲时间规则
        self.rules.append(ScheduleRule.create(
            trigger=TriggerCondition.IDLE_TIME,
            condition=lambda ctx: ctx.idle_minutes > 10,
            priority=1,
            cooldown_minutes=60
        ))
        
        # Token充裕规则
        self.rules.append(ScheduleRule.create(
            trigger=TriggerCondition.TOKEN_BONUS,
            condition=lambda ctx: (
                ctx.token_balance > ctx.daily_token_budget * 1.5 and
                ctx.token_used_today < ctx.daily_token_budget * 0.5
            ),
            priority=1,
            cooldown_minutes=120
        ))
    
    def set_user_enabled(self, enabled: bool):
        """设置用户开关"""
        self.user_enabled = enabled
    
    def set_auto_mode(self, auto: bool):
        """设置自动模式"""
        self.auto_mode = auto
    
    def evaluate(self, context: ScheduleContext) -> Optional[ScheduleDecision]:
        """评估是否应该推荐活动"""
        # 用户关闭
        if not self.user_enabled:
            return ScheduleDecision(
                decision_type="block",
                reason="User has disabled entertainment features"
            )
        
        # 检查每日限制
        if context.activities_today >= self.max_daily_activities:
            return ScheduleDecision(
                decision_type="defer",
                reason=f"Daily activity limit ({self.max_daily_activities}) reached"
            )
        
        # 检查Token
        if context.token_balance < context.daily_token_budget * 0.2:
            return ScheduleDecision(
                decision_type="defer",
                reason="Insufficient token balance"
            )
        
        # 检查冷却中的规则
        active_triggers = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # 检查冷却
            if rule.last_triggered:
                cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
                if datetime.now() < cooldown_end:
                    continue
            
            # 检查条件
            try:
                if rule.condition(context):
                    active_triggers.append(rule)
            except Exception:
                continue
        
        if not active_triggers:
            return ScheduleDecision(
                decision_type="defer",
                reason="No trigger conditions met"
            )
        
        # 按优先级排序
        active_triggers.sort(key=lambda r: r.priority, reverse=True)
        selected_rule = active_triggers[0]
        
        # 更新规则状态
        selected_rule.last_triggered = datetime.now()
        
        # 导入活动库
        from .activities import activity_library
        
        # 推荐活动
        activity = activity_library.recommend_activity(
            current_mood=context.current_mood,
            token_balance=context.token_balance,
            energy_level=context.energy_level
        )
        
        if activity:
            self.state = SchedulerState.RECOMMENDING
            self.daily_stats["recommendations_made"] += 1
            
            self._log_decision(
                decision_type="recommend",
                activity=activity,
                rule=selected_rule
            )
            
            return ScheduleDecision(
                decision_type="recommend",
                activity=activity,
                trigger=selected_rule.trigger,
                reason=f"Triggered by {selected_rule.trigger.value}",
                suggestion=self._generate_suggestion(activity, context),
                confidence=min(0.9, 0.5 + selected_rule.priority * 0.1)
            )
        else:
            return ScheduleDecision(
                decision_type="defer",
                reason="No suitable activity found"
            )
    
    def _generate_suggestion(self, activity, context: ScheduleContext) -> str:
        """生成建议文本"""
        suggestions = [
            f"想不想试试「{activity.name}」放松一下？只需要 {activity.token_cost} Token~",
            f"感觉你可能需要换个心情，要不要玩个「{activity.name}」？",
            f"我准备了一个有趣的活动「{activity.name}」，有兴趣吗？",
            f"来试试「{activity.name}」吧！可以帮助放松一下~"
        ]
        
        # 根据时间调整
        if context.time_of_day == "morning":
            suggestions = [
                f"早安！来点「{activity.name}」开启美好的一天？",
                f"早上好，要不要用「{activity.name}」提提神？"
            ]
        elif context.time_of_day == "evening":
            suggestions = [
                f"晚上好，来个「{activity.name}」放松一下吧~",
                f"辛苦了一天，要不要玩会儿「{activity.name}」？"
            ]
        
        return random.choice(suggestions)
    
    def record_response(self, accepted: bool, activity=None):
        """记录用户响应"""
        if accepted and activity:
            self.daily_stats["recommendations_accepted"] += 1
            self.daily_stats["activities_started"] += 1
            self.state = SchedulerState.ACTIVE
        else:
            self.state = SchedulerState.IDLE
    
    def record_completion(self, activity, success: bool = True):
        """记录活动完成"""
        if success:
            self.daily_stats["activities_completed"] += 1
            self.daily_stats["tokens_spent"] += activity.token_cost
        
        self.state = SchedulerState.COOLDOWN
    
    def _log_decision(self, decision_type: str, activity=None, rule=None, reason: str = ""):
        """记录决策"""
        self.schedule_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": decision_type,
            "activity": activity.name if activity else None,
            "rule": rule.trigger.value if rule else None,
            "reason": reason
        })
        
        # 限制日志长度
        if len(self.schedule_log) > 100:
            self.schedule_log = self.schedule_log[-100:]
    
    def get_scheduled_activities(self) -> List[Dict]:
        """获取计划中的活动"""
        from .activities import activity_library
        return activity_library.list_all_activities()
    
    def get_stats(self) -> Dict:
        """获取调度统计"""
        acceptance_rate = (
            self.daily_stats["recommendations_accepted"] / max(1, self.daily_stats["recommendations_made"])
        )
        
        return {
            "state": self.state.value,
            "user_enabled": self.user_enabled,
            "auto_mode": self.auto_mode,
            "daily_stats": self.daily_stats.copy(),
            "acceptance_rate": acceptance_rate,
            "active_rules": sum(1 for r in self.rules if r.enabled),
            "recent_decisions": [
                {
                    "timestamp": d["timestamp"],
                    "type": d["type"],
                    "activity": d.get("activity")
                }
                for d in self.schedule_log[-10:]
            ]
        }
    
    def reset_daily_stats(self):
        """重置每日统计"""
        self.daily_stats = {
            "activities_started": 0,
            "activities_completed": 0,
            "tokens_spent": 0,
            "recommendations_made": 0,
            "recommendations_accepted": 0
        }
        
        # 重置规则冷却
        for rule in self.rules:
            rule.last_triggered = None


# 全局调度器实例
entertainment_scheduler = EntertainmentScheduler()


# 便捷函数
def evaluate_entertainment(context: ScheduleContext) -> Optional[ScheduleDecision]:
    """评估娱乐需求的便捷函数"""
    return entertainment_scheduler.evaluate(context)


def set_entertainment_enabled(enabled: bool):
    """设置娱乐功能开关"""
    entertainment_scheduler.set_user_enabled(enabled)


def get_entertainment_stats() -> Dict:
    """获取娱乐统计"""
    return entertainment_scheduler.get_stats()
