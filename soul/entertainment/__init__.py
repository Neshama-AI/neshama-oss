# Soul层 - Entertainment子模块
"""
娱乐系统模块

包含：
- activities.py - 娱乐活动
- scheduler.py - 娱乐调度
"""

from .activities import (
    ActivityLibrary,
    Activity,
    ActivityCategory,
    ActivityIntensity,
    ActivityResult,
    activity_library,
    get_available_activities,
    recommend_activity
)

from .scheduler import (
    EntertainmentScheduler,
    ScheduleContext,
    ScheduleDecision,
    ScheduleRule,
    SchedulerState,
    TriggerCondition,
    entertainment_scheduler,
    evaluate_entertainment,
    set_entertainment_enabled,
    get_entertainment_stats
)

__all__ = [
    # Activities
    "ActivityLibrary",
    "Activity",
    "ActivityCategory",
    "ActivityIntensity",
    "ActivityResult",
    "activity_library",
    "get_available_activities",
    "recommend_activity",
    
    # Scheduler
    "EntertainmentScheduler",
    "ScheduleContext",
    "ScheduleDecision",
    "ScheduleRule",
    "SchedulerState",
    "TriggerCondition",
    "entertainment_scheduler",
    "evaluate_entertainment",
    "set_entertainment_enabled",
    "get_entertainment_stats"
]
