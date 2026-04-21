# Soul层 - Soul执行引擎
"""
Soul执行引擎：协调所有Soul子系统

功能：
- Soul配置加载
- 各系统协调
- 状态持久化
- 生命周期管理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import yaml
import json


class SoulState(Enum):
    """Soul状态"""
    UNINITIALIZED = "uninitialized"
    LOADING = "loading"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class SoulConfig:
    """Soul配置"""
    name: str = "Neshama Soul"
    version: str = "2.0.0"
    
    # 模块启用状态
    modules: Dict[str, bool] = field(default_factory=lambda: {
        "emotions": True,
        "creativity": True,
        "learning": True,
        "evolution": True,
        "entertainment": True,
        "boundaries": True,
        "drives": True
    })
    
    # 全局设置
    persistence_enabled: bool = True
    snapshot_enabled: bool = True
    snapshot_interval_minutes: int = 60
    
    # 限制设置
    max_memory_items: int = 1000
    max_knowledge_nodes: int = 500
    max_snapshot_count: int = 100
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SoulConfig":
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "modules": self.modules,
            "persistence_enabled": self.persistence_enabled,
            "snapshot_enabled": self.snapshot_enabled,
            "snapshot_interval_minutes": self.snapshot_interval_minutes,
            "max_memory_items": self.max_memory_items,
            "max_knowledge_nodes": self.max_knowledge_nodes,
            "max_snapshot_count": self.max_snapshot_count
        }


class SoulExecutor:
    """Soul执行引擎"""
    
    def __init__(self, config: SoulConfig = None):
        self.config = config or SoulConfig()
        self.state = SoulState.UNINITIALIZED
        
        # 子系统引用
        self.emotion_system = None
        self.creativity_system = None
        self.learning_system = None
        self.evolution_system = None
        self.entertainment_system = None
        self.boundaries_system = None
        self.drives_system = None
        
        # 状态存储
        self.current_state: Dict[str, Any] = {}
        self.runtime_stats: Dict[str, Any] = {}
        
        # 回调函数
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # 初始化时间戳
        self.started_at: Optional[datetime] = None
        self.last_active_at: Optional[datetime] = None
    
    def initialize(self, config_path: str = None, config_data: Dict = None):
        """初始化Soul"""
        self.state = SoulState.LOADING
        
        try:
            # 加载配置
            if config_path:
                config_data = self._load_config_from_file(config_path)
            
            if config_data:
                self.config = SoulConfig.from_dict(config_data)
            
            # 初始化各子系统
            self._initialize_systems()
            
            self.state = SoulState.READY
            self.started_at = datetime.now()
            
            self._emit_event("soul_initialized", {"config": self.config.to_dict()})
            
        except Exception as e:
            self.state = SoulState.ERROR
            raise RuntimeError(f"Failed to initialize Soul: {e}")
    
    def _load_config_from_file(self, path: str) -> Dict:
        """从文件加载配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return {}
    
    def _initialize_systems(self):
        """初始化各子系统"""
        # 情绪系统
        if self.config.modules.get("emotions"):
            from .emotion.recognizer import EmotionRecognizer
            from .emotion.responder import EmotionResponder
            from .emotion.memory import EmotionMemory
            
            self.emotion_system = {
                "recognizer": EmotionRecognizer(),
                "responder": EmotionResponder(),
                "memory": EmotionMemory()
            }
        
        # 创造力系统
        if self.config.modules.get("creativity"):
            from .creativity.inspiration import InspirationEngine
            from .creativity.style import StyleLearner
            
            self.creativity_system = {
                "inspiration": InspirationEngine(),
                "style": StyleLearner()
            }
        
        # 学习系统
        if self.config.modules.get("learning"):
            from .learning.knowledge import KnowledgeGraph
            from .learning.forgetting import ForgettingMechanism
            
            self.learning_system = {
                "knowledge": KnowledgeGraph(),
                "forgetting": ForgettingMechanism()
            }
        
        # 演化系统
        if self.config.modules.get("evolution"):
            from .evolution.engine import EvolutionEngine
            from .evolution.snapshot import SnapshotManager
            from .evolution.stability import StabilityMonitor
            
            self.evolution_system = {
                "engine": EvolutionEngine(),
                "snapshot": SnapshotManager(
                    max_snapshots=self.config.max_snapshot_count
                ),
                "stability": StabilityMonitor()
            }
        
        # 娱乐系统
        if self.config.modules.get("entertainment"):
            from .entertainment.activities import ActivityLibrary
            from .entertainment.scheduler import EntertainmentScheduler
            
            self.entertainment_system = {
                "activities": ActivityLibrary(),
                "scheduler": EntertainmentScheduler()
            }
        
        # 边界系统
        if self.config.modules.get("boundaries"):
            self.boundaries_system = self._load_boundaries_system()
        
        # 驱动力系统
        if self.config.modules.get("drives"):
            self.drives_system = self._load_drives_system()
    
    def _load_boundaries_system(self) -> Dict:
        """加载边界系统"""
        # 简化实现
        return {
            "identity": {"core_values": [], "non_negotiable": []},
            "limits": {"content": [], "actions": []}
        }
    
    def _load_drives_system(self) -> Dict:
        """加载驱动力系统"""
        # 简化实现
        return {
            "curiosity": {"level": 0.7, "active": True},
            "achievement": {"level": 0.6, "active": True},
            "connection": {"level": 0.8, "active": True}
        }
    
    # ==================== 情绪处理 ====================
    
    def recognize_emotions(self, text: str, context: Dict = None) -> List[Dict]:
        """识别情绪"""
        if not self.emotion_system:
            return []
        
        recognizer = self.emotion_system["recognizer"]
        return recognizer.recognize(text, context)
    
    def generate_emotion_response(
        self,
        emotions: List[Dict],
        user_message: str,
        user_profile: Dict = None,
        relationship_level: float = 0.5
    ) -> Dict:
        """生成情绪响应"""
        if not self.emotion_system:
            return {"response": "", "strategy": "none"}
        
        responder = self.emotion_system["responder"]
        return responder.generate_response(
            emotions, user_message, user_profile, relationship_level
        )
    
    def record_emotion_event(
        self,
        user_id: str,
        emotions: List[Dict],
        context: Dict = None
    ) -> Any:
        """记录情绪事件"""
        if not self.emotion_system:
            return None
        
        memory = self.emotion_system["memory"]
        if hasattr(memory, 'record_event'):
            return memory.record_event(emotions, **(context or {}))
        return None
    
    # ==================== 创造力处理 ====================
    
    def trigger_inspiration(
        self,
        trigger_word: str,
        context: Dict = None
    ) -> Any:
        """触发灵感"""
        if not self.creativity_system:
            return None
        
        inspiration = self.creativity_system["inspiration"]
        return inspiration.create_inspiration(
            trigger_word=trigger_word,
            association_type=None,  # 使用默认
            context=context.get("text", "") if context else ""
        )
    
    def learn_style(self, content: str, context: Dict = None):
        """学习风格"""
        if not self.creativity_system:
            return
        
        style = self.creativity_system["style"]
        style.learn_from_generation(content, context)
    
    # ==================== 学习处理 ====================
    
    def add_knowledge(
        self,
        content: str,
        knowledge_type: str = "experience",
        domain: str = "",
        tags: List[str] = None
    ) -> Any:
        """添加知识"""
        if not self.learning_system:
            return None
        
        knowledge = self.learning_system["knowledge"]
        return knowledge.add_knowledge(
            content=content,
            knowledge_type=None,  # KnowledgeType
            domain=domain,
            tags=tags
        )
    
    def retrieve_knowledge(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Any]:
        """检索知识"""
        if not self.learning_system:
            return []
        
        knowledge = self.learning_system["knowledge"]
        return knowledge.retrieve_knowledge(query, top_k=top_k)
    
    # ==================== 演化处理 ====================
    
    def evaluate_evolution(self, context: Dict) -> List[Dict]:
        """评估人格演化"""
        if not self.evolution_system:
            return []
        
        engine = self.evolution_system["engine"]
        return engine.evaluate_context(context)
    
    def create_snapshot(
        self,
        snapshot_type: str = "auto",
        label: str = ""
    ) -> Any:
        """创建人格快照"""
        if not self.evolution_system or not self.config.snapshot_enabled:
            return None
        
        snapshot_manager = self.evolution_system["snapshot"]
        
        # 收集当前状态
        traits = self.get_personality_traits()
        emotion_state = self.get_emotion_state()
        drives = self.get_drive_levels()
        
        from .evolution.snapshot import SnapshotType
        snap_type = SnapshotType(snapshot_type)
        
        return snapshot_manager.create_snapshot(
            traits=traits,
            emotion_state=emotion_state,
            drive_levels=drives,
            snapshot_type=snap_type,
            label=label
        )
    
    def rollback_to_snapshot(self, snapshot_id: str) -> Dict:
        """回滚到指定快照"""
        if not self.evolution_system:
            return {"success": False}
        
        snapshot_manager = self.evolution_system["snapshot"]
        return snapshot_manager.rollback_to(snapshot_id)
    
    def check_stability(self, trait_name: str, proposed_value: float) -> Dict:
        """检查人格稳定性"""
        if not self.evolution_system:
            return {"allowed": True}
        
        stability = self.evolution_system["stability"]
        return stability.check_proposed_change(trait_name, proposed_value)
    
    # ==================== 娱乐处理 ====================
    
    def evaluate_entertainment(self, context: Dict) -> Optional[Any]:
        """评估娱乐需求"""
        if not self.entertainment_system:
            return None
        
        from .entertainment.scheduler import ScheduleContext
        
        ctx = ScheduleContext(
            current_mood=context.get("mood", {}),
            energy_level=context.get("energy", 0.5),
            stress_level=context.get("stress", 0.3),
            boredom_level=context.get("boredom", 0.4),
            token_balance=context.get("token_balance", 100)
        )
        
        scheduler = self.entertainment_system["scheduler"]
        return scheduler.evaluate(ctx)
    
    def set_entertainment_enabled(self, enabled: bool):
        """设置娱乐开关"""
        if not self.entertainment_system:
            return
        
        scheduler = self.entertainment_system["scheduler"]
        scheduler.set_user_enabled(enabled)
    
    # ==================== 状态获取 ====================
    
    def get_personality_traits(self) -> Dict[str, float]:
        """获取人格特征"""
        if not self.evolution_system:
            return {}
        
        return self.evolution_system["engine"].get_trait_values()
    
    def get_emotion_state(self) -> Dict:
        """获取情绪状态"""
        if not self.emotion_system:
            return {}
        
        # 返回简化的情绪状态
        return {
            "current": "neutral",
            "intensity": 0.3
        }
    
    def get_drive_levels(self) -> Dict[str, float]:
        """获取驱动力水平"""
        if not self.drives_system:
            return {}
        
        return {
            name: data["level"]
            for name, data in self.drives_system.items()
        }
    
    def get_full_state(self) -> Dict:
        """获取完整状态"""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_active": self.last_active_at.isoformat() if self.last_active_at else None,
            "personality_traits": self.get_personality_traits(),
            "emotion_state": self.get_emotion_state(),
            "drive_levels": self.get_drive_levels(),
            "stats": self.runtime_stats
        }
    
    # ==================== 事件处理 ====================
    
    def on_event(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def _emit_event(self, event_name: str, data: Dict):
        """触发事件"""
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception:
                pass
    
    # ==================== 生命周期 ====================
    
    def activate(self):
        """激活Soul"""
        self.state = SoulState.ACTIVE
        self.last_active_at = datetime.now()
        self._emit_event("soul_activated", {})
    
    def pause(self):
        """暂停Soul"""
        if self.state == SoulState.ACTIVE:
            self.state = SoulState.PAUSED
            self._emit_event("soul_paused", {})
    
    def resume(self):
        """恢复Soul"""
        if self.state == SoulState.PAUSED:
            self.state = SoulState.ACTIVE
            self.last_active_at = datetime.now()
            self._emit_event("soul_resumed", {})
    
    def shutdown(self):
        """关闭Soul"""
        # 保存状态
        if self.config.persistence_enabled:
            self._persist_state()
        
        self.state = SoulState.READY
        self._emit_event("soul_shutdown", {})
    
    def _persist_state(self):
        """持久化状态"""
        # 简化实现
        self.runtime_stats["last_persisted"] = datetime.now().isoformat()
    
    # ==================== 状态持久化 ====================
    
    def export_state(self) -> Dict:
        """导出完整状态"""
        state = {
            "config": self.config.to_dict(),
            "timestamp": datetime.now().isoformat(),
            "soul_state": self.get_full_state()
        }
        
        # 导出子系统状态
        if self.evolution_system:
            state["evolution"] = {
                "traits": self.evolution_system["engine"].export_state(),
                "snapshots": self.evolution_system["snapshot"].export_snapshots()
            }
        
        if self.learning_system:
            state["learning"] = {
                "knowledge": self.learning_system["knowledge"].export_knowledge()
            }
        
        return state
    
    def import_state(self, state_data: Dict):
        """导入状态"""
        # 恢复配置
        if "config" in state_data:
            self.config = SoulConfig.from_dict(state_data["config"])
        
        # 恢复子系统状态
        if "evolution" in state_data and self.evolution_system:
            if "traits" in state_data["evolution"]:
                engine = self.evolution_system["engine"]
                for trait_name, trait_data in state_data["evolution"]["traits"].get("traits", {}).items():
                    engine.traits[trait_name].value = trait_data["value"]
            
            if "snapshots" in state_data["evolution"]:
                self.evolution_system["snapshot"].import_snapshots(
                    state_data["evolution"]["snapshots"]
                )
        
        if "learning" in state_data and self.learning_system:
            if "knowledge" in state_data["learning"]:
                self.learning_system["knowledge"].import_knowledge(
                    state_data["learning"]["knowledge"]
                )
        
        self._emit_event("soul_state_restored", state_data)


# 全局Soul执行器实例
soul_executor = SoulExecutor()


# 便捷函数
def get_soul_executor() -> SoulExecutor:
    """获取Soul执行器"""
    return soul_executor


def initialize_soul(config_path: str = None, config_data: Dict = None):
    """初始化Soul的便捷函数"""
    soul_executor.initialize(config_path, config_data)
    return soul_executor
