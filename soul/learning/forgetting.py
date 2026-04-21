# Soul层 - 遗忘机制模块
"""
遗忘机制：模拟人类记忆的遗忘特性

功能：
- 基于重要性的遗忘
- 基于时间的遗忘
- 基于使用频率的遗忘
- 主动遗忘与保护
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import math


class ForgettingCurve(Enum):
    """遗忘曲线类型"""
    Ebbinghaus = "ebbinghaus"         # 经典艾宾浩斯
    Adaptive = "adaptive"            # 自适应遗忘
    UserInfluence = "user_influence" # 用户影响遗忘


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: str
    memory_type: str  # "experience", "knowledge", "preference", "fact"
    
    # 强度和重要性
    strength: float = 1.0           # 记忆强度 0-1
    importance: float = 0.5          # 重要性 0-1
    emotional_significance: float = 0.5  # 情感重要性
    
    # 访问信息
    last_accessed: str = ""          # ISO时间戳
    access_count: int = 0
    first_created: str = ""
    
    # 遗忘相关
    decay_rate: float = 0.1         # 衰减率
    last_reviewed: str = ""         # 上次复习时间
    
    # 保护状态
    protected: bool = False         # 是否被保护
    protection_reason: str = ""
    
    # 元数据
    domain: str = ""
    tags: List[str] = field(default_factory=list)
    context: str = ""
    
    @classmethod
    def create(
        cls,
        content: str,
        memory_type: str,
        importance: float = 0.5,
        domain: str = "",
        tags: List[str] = None,
        emotional_significance: float = 0.5
    ) -> "MemoryItem":
        import uuid
        now = datetime.now().isoformat()
        
        return cls(
            id=f"mem_{uuid.uuid4().hex[:10]}",
            content=content,
            memory_type=memory_type,
            importance=importance,
            domain=domain,
            tags=tags or [],
            emotional_significance=emotional_significance,
            first_created=now,
            last_accessed=now,
            last_reviewed=now
        )
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "strength": self.strength,
            "importance": self.importance,
            "emotional_significance": self.emotional_significance,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "first_created": self.first_created,
            "decay_rate": self.decay_rate,
            "protected": self.protected,
            "domain": self.domain,
            "tags": self.tags,
            "time_alive": self._calculate_time_alive()
        }
    
    def _calculate_time_alive(self) -> float:
        """计算存活时间（小时）"""
        if not self.first_created:
            return 0
        created = datetime.fromisoformat(self.first_created)
        now = datetime.now()
        return (now - created).total_seconds() / 3600


@dataclass
class ForgettingConfig:
    """遗忘配置"""
    curve_type: ForgettingCurve = ForgettingCurve.Ebbinghaus
    
    # 基础衰减参数
    base_decay_rate: float = 0.1     # 基础衰减率
    time_weight: float = 0.3        # 时间权重
    
    # 强化因子
    importance_multiplier: float = 2.0  # 重要性对强度的乘法因子
    emotional_multiplier: float = 1.5   # 情感强度乘法因子
    usage_boost: float = 0.1        # 每次使用增加的强度
    
    # 遗忘阈值
    forgetting_threshold: float = 0.1  # 低于此值会被遗忘
    review_threshold: float = 0.3    # 需要复习的阈值
    
    # 保护规则
    protect_emotional: bool = True   # 保护高情感重要性的记忆
    protect_recent: bool = True       # 保护近期重要记忆
    protect_user_marked: bool = True # 保护用户标记的记忆
    
    # 执行设置
    check_interval_hours: int = 24   # 检查间隔
    max_items_per_check: int = 100   # 每次检查处理的最大项数


class ForgettingMechanism:
    """遗忘机制"""
    
    def __init__(self, config: ForgettingConfig = None):
        self.config = config or ForgettingConfig()
        self.memory_store: Dict[str, MemoryItem] = {}
        self.forgetting_log: List[Dict] = []
        self.last_check = datetime.now().isoformat()
        
        # 统计数据
        self.stats = {
            "total_items": 0,
            "forgotten_items": 0,
            "strengthened_items": 0,
            "protected_items": 0
        }
    
    def add_memory(
        self,
        content: str,
        memory_type: str,
        importance: float = 0.5,
        emotional_significance: float = 0.5,
        domain: str = "",
        tags: List[str] = None,
        protected: bool = False,
        protection_reason: str = ""
    ) -> MemoryItem:
        """添加记忆"""
        item = MemoryItem.create(
            content=content,
            memory_type=memory_type,
            importance=importance,
            domain=domain,
            tags=tags,
            emotional_significance=emotional_significance
        )
        
        # 根据配置调整初始强度
        initial_strength = min(1.0, 0.5 + importance * 0.3 + emotional_significance * 0.2)
        item.strength = initial_strength
        
        # 设置衰减率
        item.decay_rate = self._calculate_decay_rate(
            importance, 
            emotional_significance,
            memory_type
        )
        
        # 处理保护
        if protected:
            item.protected = True
            item.protection_reason = protection_reason
            self.stats["protected_items"] += 1
        elif self._should_auto_protect(item):
            item.protected = True
            item.protection_reason = "Auto-protected by system"
            self.stats["protected_items"] += 1
        
        self.memory_store[item.id] = item
        self.stats["total_items"] += 1
        
        return item
    
    def _calculate_decay_rate(
        self,
        importance: float,
        emotional: float,
        memory_type: str
    ) -> float:
        """计算衰减率"""
        base = self.config.base_decay_rate
        
        # 类型调整
        type_multipliers = {
            "fact": 0.8,
            "knowledge": 0.7,
            "experience": 1.0,
            "preference": 1.2,
            "context": 1.5
        }
        
        type_mult = type_multipliers.get(memory_type, 1.0)
        
        # 重要性调整（重要性越高衰减越慢）
        importance_mult = 1.0 - importance * 0.5
        
        # 情感调整
        emotional_mult = 1.0 - emotional * 0.3
        
        return base * type_mult * importance_mult * emotional_mult
    
    def _should_auto_protect(self, item: MemoryItem) -> bool:
        """判断是否应该自动保护"""
        # 高情感重要性
        if self.config.protect_emotional and item.emotional_significance > 0.8:
            return True
        
        # 近期高重要性
        if self.config.protect_recent and item.importance > 0.8:
            time_alive = item._calculate_time_alive()
            if time_alive < 24:  # 24小时内
                return True
        
        return False
    
    def access_memory(self, item_id: str) -> Optional[MemoryItem]:
        """访问记忆（强化记忆）"""
        if item_id not in self.memory_store:
            return None
        
        item = self.memory_store[item_id]
        item.access_count += 1
        item.last_accessed = datetime.now().isoformat()
        
        # 根据艾宾浩斯曲线强化
        time_since_review = self._hours_since(item.last_reviewed)
        
        # 强化量取决于距上次复习的时间
        if time_since_review > 0:
            boost = self.config.usage_boost * (1 + math.log1p(time_since_review) * 0.1)
            item.strength = min(1.0, item.strength + boost)
            self.stats["strengthened_items"] += 1
        
        item.last_reviewed = datetime.now().isoformat()
        
        return item
    
    def _hours_since(self, timestamp: str) -> float:
        """计算距离某时间的小时数"""
        if not timestamp:
            return float('inf')
        dt = datetime.fromisoformat(timestamp)
        return (datetime.now() - dt).total_seconds() / 3600
    
    def calculate_strength(self, item: MemoryItem, current_time: datetime = None) -> float:
        """计算当前强度（基于遗忘曲线）"""
        if current_time is None:
            current_time = datetime.now()
        
        hours_since_creation = item._calculate_time_alive()
        
        if self.config.curve_type == ForgettingCurve.Ebbinghaus:
            # 艾宾浩斯遗忘曲线
            # S = e^(-t/S)
            stability = 10  # 稳定性参数
            strength = math.exp(-hours_since_creation / stability) * item.strength
            
        elif self.config.curve_type == ForgettingCurve.Adaptive:
            # 自适应遗忘曲线
            # 考虑重要性和使用频率
            usage_factor = 1 + math.log1p(item.access_count) * 0.2
            importance_factor = 1 + item.importance * self.config.importance_multiplier
            emotional_factor = 1 + item.emotional_significance * self.config.emotional_multiplier
            
            decay = hours_since_creation * item.decay_rate
            strength = max(0, 1 - decay / (usage_factor * importance_factor * emotional_factor))
            
        else:
            # 简化遗忘
            decay = hours_since_creation * item.decay_rate
            strength = max(0, item.strength - decay)
        
        # 应用重要性和情感修正
        strength = strength * (1 + item.importance * 0.2) * (1 + item.emotional_significance * 0.1)
        
        return min(1.0, max(0.0, strength))
    
    def process_forgetting(self) -> Dict[str, Any]:
        """处理遗忘"""
        results = {
            "checked": 0,
            "weakened": 0,
            "forgotten": 0,
            "strengthened": 0
        }
        
        current_time = datetime.now()
        items_to_remove = []
        
        for item_id, item in self.memory_store.items():
            if item.protected:
                continue
            
            results["checked"] += 1
            
            # 计算当前强度
            current_strength = self.calculate_strength(item, current_time)
            item.strength = current_strength
            
            # 检查遗忘阈值
            if current_strength < self.config.forgetting_threshold:
                items_to_remove.append(item_id)
                results["forgotten"] += 1
                self.stats["forgotten_items"] += 1
                
                self.forgetting_log.append({
                    "timestamp": current_time.isoformat(),
                    "item_id": item_id,
                    "reason": "strength_below_threshold",
                    "final_strength": current_strength
                })
            
            # 检查是否需要复习
            elif current_strength < self.config.review_threshold:
                results["weakened"] += 1
        
        # 执行遗忘
        for item_id in items_to_remove:
            del self.memory_store[item_id]
        
        self.last_check = current_time.isoformat()
        
        return results
    
    def protect_memory(self, item_id: str, reason: str = "") -> bool:
        """保护记忆"""
        if item_id in self.memory_store:
            self.memory_store[item_id].protected = True
            self.memory_store[item_id].protection_reason = reason
            self.stats["protected_items"] += 1
            return True
        return False
    
    def unprotect_memory(self, item_id: str) -> bool:
        """取消保护"""
        if item_id in self.memory_store:
            self.memory_store[item_id].protected = False
            self.memory_store[item_id].protection_reason = ""
            self.stats["protected_items"] -= 1
            return True
        return False
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计"""
        total = len(self.memory_store)
        if total == 0:
            return {"total": 0, "avg_strength": 0, "protected": 0}
        
        avg_strength = sum(m.strength for m in self.memory_store.values()) / total
        protected = sum(1 for m in self.memory_store.values() if m.protected)
        
        strength_distribution = {
            "high": sum(1 for m in self.memory_store.values() if m.strength > 0.7),
            "medium": sum(1 for m in self.memory_store.values() if 0.3 < m.strength <= 0.7),
            "low": sum(1 for m in self.memory_store.values() if m.strength <= 0.3)
        }
        
        return {
            "total_items": total,
            "avg_strength": avg_strength,
            "protected_count": protected,
            "protected_pct": protected / total if total > 0 else 0,
            "strength_distribution": strength_distribution,
            "stats": self.stats.copy()
        }
    
    def get_memories_needing_review(self, limit: int = 20) -> List[MemoryItem]:
        """获取需要复习的记忆"""
        memories = []
        
        for item in self.memory_store.values():
            if item.protected:
                continue
            
            current_strength = self.calculate_strength(item)
            if current_strength < self.config.review_threshold:
                memories.append((item, current_strength))
        
        # 按强度排序
        memories.sort(key=lambda x: x[1])
        return [m for m, _ in memories[:limit]]
    
    def suggest_forgetting(self, reason: str = "") -> List[str]:
        """建议可以遗忘的内容"""
        suggestions = []
        
        for item in self.memory_store.values():
            if item.protected:
                continue
            
            current_strength = self.calculate_strength(item)
            
            # 可以遗忘的条件
            can_forget = (
                current_strength < self.config.forgetting_threshold * 2 and
                item.access_count == 0 and
                item.importance < 0.3 and
                item.emotional_significance < 0.3
            )
            
            if can_forget:
                suggestions.append({
                    "id": item.id,
                    "content": item.content[:50],
                    "strength": current_strength,
                    "reason": reason or "Low importance, never accessed"
                })
        
        return suggestions[:20]
    
    def export_state(self) -> Dict:
        """导出状态"""
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats.copy(),
            "config": {
                "curve_type": self.config.curve_type.value,
                "forgetting_threshold": self.config.forgetting_threshold,
                "base_decay_rate": self.config.base_decay_rate
            },
            "memory_count": len(self.memory_store),
            "forgetting_log_count": len(self.forgetting_log)
        }


# 全局遗忘机制实例
forgetting_mechanism = ForgettingMechanism()


# 便捷函数
def add_memory(content: str, memory_type: str = "experience", **kwargs) -> MemoryItem:
    """添加记忆的便捷函数"""
    return forgetting_mechanism.add_memory(content, memory_type, **kwargs)


def access_memory(item_id: str) -> Optional[MemoryItem]:
    """访问记忆的便捷函数"""
    return forgetting_mechanism.access_memory(item_id)


def process_forgetting() -> Dict:
    """处理遗忘的便捷函数"""
    return forgetting_mechanism.process_forgetting()


def get_memory_stats() -> Dict:
    """获取记忆统计的便捷函数"""
    return forgetting_mechanism.get_memory_stats()
