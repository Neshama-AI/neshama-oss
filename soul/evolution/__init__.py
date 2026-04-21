# Soul层 - Evolution子模块
"""
人格演化模块

包含：
- engine.py - 人格演化引擎
- snapshot.py - 快照管理
- stability.py - 稳定性检测
"""

from .engine import (
    EvolutionEngine,
    EvolutionRule,
    PersonalityTrait,
    EvolutionTrigger,
    EvolutionDirection,
    get_default_evolution_rules,
    get_default_personality_traits
)

from .snapshot import (
    SnapshotManager,
    PersonalitySnapshot,
    SnapshotType
)

from .stability import (
    StabilityMonitor,
    StabilityThreshold,
    StabilityLevel,
    StabilityAction,
    TraitStabilityRecord
)

__all__ = [
    # Engine
    "EvolutionEngine",
    "EvolutionRule",
    "PersonalityTrait",
    "EvolutionTrigger",
    "EvolutionDirection",
    "get_default_evolution_rules",
    "get_default_personality_traits",
    
    # Snapshot
    "SnapshotManager",
    "PersonalitySnapshot",
    "SnapshotType",
    
    # Stability
    "StabilityMonitor",
    "StabilityThreshold",
    "StabilityLevel",
    "StabilityAction",
    "TraitStabilityRecord"
]
