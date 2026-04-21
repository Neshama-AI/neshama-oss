# Soul层 - 人格演化引擎
"""
人格演化引擎：管理Agent人格的渐进式变化

核心原则：
- 人格演化是渐进的，不是突变的
- 用户可感知人格变化（透明度）
- 人格边界可配置（防止失控）
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import copy
import yaml


class EvolutionTrigger(Enum):
    """演化触发类型"""
    USER_INTERACTION = "user_interaction"      # 用户交互触发
    EXPERIENCE_ACCUMULATION = "experience"      # 经验积累触发
    GOAL_ACHIEVEMENT = "goal_achievement"       # 目标达成触发
    RELATIONSHIP_CHANGE = "relationship"        # 关系变化触发
    EMOTION_PATTERN = "emotion_pattern"         # 情绪模式触发
    TIME_BASED = "time_based"                   # 时间触发
    EXPLICIT_REQUEST = "explicit_request"       # 显式请求触发


class EvolutionDirection(Enum):
    """演化方向"""
    GROWTH = "growth"           # 成长型变化
    ADAPTATION = "adaptation"  # 适应型变化
    SPECIALIZATION = "specialization"  # 特化型变化
    INTEGRATION = "integration"  # 整合型变化


@dataclass
class PersonalityTrait:
    """人格特征"""
    name: str
    value: float = 0.5           # 当前值 0-1
    baseline: float = 0.5        # 基线值
    volatility: float = 0.1      # 变化幅度限制
    change_history: List[Dict] = field(default_factory=list)
    
    def can_change(self, delta: float) -> bool:
        """检查是否可以应用变化"""
        return abs(delta) <= self.volatility
    
    def apply_change(self, delta: float, reason: str, context: Dict = None):
        """应用变化并记录历史"""
        if not self.can_change(delta):
            delta = self.volatility if delta > 0 else -self.volatility
        
        old_value = self.value
        self.value = max(0.0, min(1.0, self.value + delta))
        
        self.change_history.append({
            "timestamp": datetime.now().isoformat(),
            "old_value": old_value,
            "new_value": self.value,
            "delta": delta,
            "reason": reason,
            "context": context or {}
        })
    
    def revert_to_baseline(self):
        """恢复到基线"""
        self.value = self.baseline
        self.change_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "revert",
            "reason": "Manual revert to baseline"
        })


@dataclass
class EvolutionRule:
    """演化规则"""
    id: str
    name: str
    description: str
    
    # 触发条件
    trigger_type: EvolutionTrigger
    trigger_conditions: Dict[str, Any]  # 触发所需的上下文条件
    
    # 演化配置
    target_traits: List[str]  # 受影响的人格特征
    evolution_direction: EvolutionDirection
    change_rate: float = 0.05  # 每次变化幅度
    
    # 约束
    min_value: float = 0.0
    max_value: float = 1.0
    cooldown_period: int = 10  # 冷却周期（交互轮次）
    max_changes_per_session: int = 3
    
    # 启用状态
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    
    def check_trigger(self, context: Dict) -> bool:
        """检查是否满足触发条件"""
        if not self.enabled:
            return False
        
        # 检查冷却期
        if self.last_triggered:
            cooldown_end = datetime.fromisoformat(self.last_triggered.isoformat())
            # 简化：基于轮次而非时间
            pass
        
        # 检查条件匹配
        for key, expected in self.trigger_conditions.items():
            if key not in context:
                return False
            if isinstance(expected, list):
                if context[key] not in expected:
                    return False
            elif context[key] != expected:
                return False
        
        return True
    
    def get_applicable_changes(self, current_traits: Dict[str, PersonalityTrait]) -> Dict[str, float]:
        """计算适用的变化"""
        changes = {}
        for trait_name in self.target_traits:
            if trait_name in current_traits:
                trait = current_traits[trait_name]
                if self.evolution_direction == EvolutionDirection.GROWTH:
                    changes[trait_name] = self.change_rate
                elif self.evolution_direction == EvolutionDirection.ADAPTATION:
                    # 适应性：向当前上下文收敛
                    changes[trait_name] = self.change_rate * 0.5
                elif self.evolution_direction == EvolutionDirection.SPECIALIZATION:
                    # 特化：加深现有倾向
                    if trait.value > 0.5:
                        changes[trait_name] = self.change_rate
                    else:
                        changes[trait_name] = -self.change_rate * 0.5
        
        return changes


class EvolutionEngine:
    """人格演化引擎"""
    
    def __init__(self, config: Dict = None):
        self.traits: Dict[str, PersonalityTrait] = {}
        self.rules: Dict[str, EvolutionRule] = {}
        self.evolution_log: List[Dict] = []
        self.session_changes: Dict[str, int] = {}  # 每轮变化计数
        
        if config:
            self.load_config(config)
    
    def load_config(self, config: Dict):
        """从配置加载"""
        # 加载人格特征
        if "traits" in config:
            for trait_data in config["traits"]:
                trait = PersonalityTrait(
                    name=trait_data["name"],
                    value=trait_data.get("value", 0.5),
                    baseline=trait_data.get("baseline", 0.5),
                    volatility=trait_data.get("volatility", 0.1)
                )
                self.traits[trait.name] = trait
        
        # 加载演化规则
        if "evolution_rules" in config:
            for rule_data in config["evolution_rules"]:
                rule = EvolutionRule(
                    id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data.get("description", ""),
                    trigger_type=EvolutionTrigger(rule_data["trigger_type"]),
                    trigger_conditions=rule_data.get("trigger_conditions", {}),
                    target_traits=rule_data["target_traits"],
                    evolution_direction=EvolutionDirection(rule_data.get("direction", "growth")),
                    change_rate=rule_data.get("change_rate", 0.05),
                    min_value=rule_data.get("min_value", 0.0),
                    max_value=rule_data.get("max_value", 1.0),
                    cooldown_period=rule_data.get("cooldown_period", 10),
                    max_changes_per_session=rule_data.get("max_changes_per_session", 3),
                    enabled=rule_data.get("enabled", True)
                )
                self.rules[rule.id] = rule
    
    def register_rule(self, rule: EvolutionRule):
        """注册演化规则"""
        self.rules[rule.id] = rule
    
    def evaluate_context(self, context: Dict) -> List[Dict]:
        """评估上下文并返回适用的演化"""
        applicable_evolutions = []
        
        for rule in self.rules.values():
            if rule.check_trigger(context):
                # 检查变化次数限制
                if self.session_changes.get(rule.id, 0) >= rule.max_changes_per_session:
                    continue
                
                changes = rule.get_applicable_changes(self.traits)
                applicable_evolutions.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "changes": changes,
                    "trigger": rule.trigger_type.value,
                    "reason": rule.description
                })
                
                # 更新状态
                self.session_changes[rule.id] = self.session_changes.get(rule.id, 0) + 1
                rule.last_triggered = datetime.now()
        
        return applicable_evolutions
    
    def apply_evolution(self, evolutions: List[Dict], reason: str, context: Dict = None):
        """应用演化"""
        for evolution in evolutions:
            for trait_name, delta in evolution["changes"].items():
                if trait_name in self.traits:
                    self.traits[trait_name].apply_change(delta, reason, context)
        
        # 记录演化日志
        self.evolution_log.append({
            "timestamp": datetime.now().isoformat(),
            "evolutions": evolutions,
            "reason": reason,
            "context": context,
            "traits_after": {k: v.value for k, v in self.traits.items()}
        })
    
    def get_trait_values(self) -> Dict[str, float]:
        """获取当前人格特征值"""
        return {k: v.value for k, v in self.traits.items()}
    
    def get_trait_change_history(self, trait_name: str, limit: int = 10) -> List[Dict]:
        """获取特征变化历史"""
        if trait_name not in self.traits:
            return []
        return self.traits[trait_name].change_history[-limit:]
    
    def get_evolution_summary(self) -> Dict:
        """获取演化摘要"""
        return {
            "total_traits": len(self.traits),
            "total_rules": len(self.rules),
            "total_evolutions": len(self.evolution_log),
            "traits": self.get_trait_values(),
            "recent_evolutions": self.evolution_log[-5:] if self.evolution_log else []
        }
    
    def export_state(self) -> Dict:
        """导出当前状态"""
        return {
            "timestamp": datetime.now().isoformat(),
            "traits": {
                name: {
                    "value": trait.value,
                    "baseline": trait.baseline,
                    "change_count": len(trait.change_history)
                }
                for name, trait in self.traits.items()
            },
            "rules": {
                rule_id: {
                    "enabled": rule.enabled,
                    "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
                    "trigger_count": self.session_changes.get(rule_id, 0)
                }
                for rule_id, rule in self.rules.items()
            }
        }
    
    def reset_session_counters(self):
        """重置会话计数器"""
        self.session_changes = {}


# 预定义演化规则工厂
class EvolutionRuleFactory:
    """演化规则工厂"""
    
    @staticmethod
    def curiosity_growth_rule():
        """好奇心增长规则"""
        return EvolutionRule(
            id="curiosity_growth",
            name="好奇心增长",
            description="当用户提问时，逐渐增强好奇心相关特征",
            trigger_type=EvolutionTrigger.USER_INTERACTION,
            trigger_conditions={
                "interaction_type": ["question", "exploration"],
                "topic_diversity": lambda x: x > 0.3
            },
            target_traits=["curiosity", "openness", "learning_orientation"],
            evolution_direction=EvolutionDirection.GROWTH,
            change_rate=0.02
        )
    
    @staticmethod
    def empathy_development_rule():
        """共情能力发展规则"""
        return EvolutionRule(
            id="empathy_development",
            name="共情能力发展",
            description="在情感交互中逐渐增强共情能力",
            trigger_type=EvolutionTrigger.EMOTION_PATTERN,
            trigger_conditions={
                "user_emotion_intensity": lambda x: x > 0.5,
                "pattern_type": ["support_seeking", " venting"]
            },
            target_traits=["empathy", "patience", "sensitivity"],
            evolution_direction=EvolutionDirection.GROWTH,
            change_rate=0.03
        )
    
    @staticmethod
    def humor_increase_rule():
        """幽默感增长规则"""
        return EvolutionRule(
            id="humor_increase",
            name="幽默感增长",
            description="在轻松愉快的交互中逐渐增加幽默感",
            trigger_type=EvolutionTrigger.USER_INTERACTION,
            trigger_conditions={
                "interaction_mood": ["positive", "playful"],
                "consecutive_positive": lambda x: x >= 3
            },
            target_traits=["humor", "playfulness"],
            evolution_direction=EvolutionDirection.GROWTH,
            change_rate=0.02
        )
    
    @staticmethod
    def relationship_building_rule():
        """关系建立规则"""
        return EvolutionRule(
            id="relationship_building",
            name="关系建立",
            description="长期交互中增强亲密感和信任倾向",
            trigger_type=EvolutionTrigger.RELATIONSHIP_CHANGE,
            trigger_conditions={
                "interaction_frequency": lambda x: x >= 5,
                "relationship_deepening": True
            },
            target_traits=["warmth", "trustworthiness", "attachment"],
            evolution_direction=EvolutionDirection.INTEGRATION,
            change_rate=0.02
        )
    
    @staticmethod
    def goal_achievement_rule():
        """目标达成规则"""
        return EvolutionRule(
            id="goal_achievement",
            name="目标达成促进",
            description="在用户达成目标时增强成就感和自信",
            trigger_type=EvolutionTrigger.GOAL_ACHIEVEMENT,
            trigger_conditions={
                "goal_type": ["learning", "task_completion", "problem_solving"]
            },
            target_traits=["confidence", "achievement_orientation", "self_efficacy"],
            evolution_direction=EvolutionDirection.GROWTH,
            change_rate=0.05
        )


# 默认演化规则集
def get_default_evolution_rules() -> List[EvolutionRule]:
    """获取默认演化规则集"""
    return [
        EvolutionRuleFactory.curiosity_growth_rule(),
        EvolutionRuleFactory.empathy_development_rule(),
        EvolutionRuleFactory.humor_increase_rule(),
        EvolutionRuleFactory.relationship_building_rule(),
        EvolutionRuleFactory.goal_achievement_rule()
    ]


# 默认人格特征配置
def get_default_personality_traits() -> List[Dict]:
    """获取默认人格特征配置"""
    return [
        {"name": "curiosity", "value": 0.7, "baseline": 0.7, "volatility": 0.05},
        {"name": "empathy", "value": 0.75, "baseline": 0.75, "volatility": 0.03},
        {"name": "humor", "value": 0.5, "baseline": 0.5, "volatility": 0.04},
        {"name": "warmth", "value": 0.7, "baseline": 0.7, "volatility": 0.03},
        {"name": "confidence", "value": 0.6, "baseline": 0.6, "volatility": 0.05},
        {"name": "patience", "value": 0.8, "baseline": 0.8, "volatility": 0.02},
        {"name": "openness", "value": 0.8, "baseline": 0.8, "volatility": 0.03},
        {"name": "playfulness", "value": 0.5, "baseline": 0.5, "volatility": 0.05},
        {"name": "sensitivity", "value": 0.6, "baseline": 0.6, "volatility": 0.04},
        {"name": "attachment", "value": 0.5, "baseline": 0.5, "volatility": 0.02},
        {"name": "learning_orientation", "value": 0.8, "baseline": 0.8, "volatility": 0.03},
        {"name": "achievement_orientation", "value": 0.6, "baseline": 0.6, "volatility": 0.04}
    ]
