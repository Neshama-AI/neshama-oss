# Soul层 - 人格快照管理
"""
人格快照：版本历史与回滚能力

功能：
- 定期保存人格快照
- 记录关键变化节点
- 支持回滚到指定版本
- 快照对比与分析
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json


class SnapshotType(Enum):
    """快照类型"""
    AUTO = "auto"              # 自动定期快照
    MANUAL = "manual"          # 手动快照
    MILESTONE = "milestone"    # 里程碑快照（重大变化后）
    BEFORE_CHANGE = "before_change"  # 变化前快照
    BACKUP = "backup"          # 备份快照


@dataclass
class PersonalitySnapshot:
    """人格快照"""
    id: str
    timestamp: str
    snapshot_type: SnapshotType
    
    # 快照内容
    traits: Dict[str, float]           # 人格特征值
    emotion_state: Dict[str, Any]      # 情绪状态
    drive_levels: Dict[str, float]     # 驱动力水平
    
    # 元数据
    label: str = ""                     # 快照标签
    description: str = ""               # 快照描述
    parent_id: Optional[str] = None     # 父快照ID
    user_visible: bool = True          # 是否对用户可见
    
    # 变化信息
    changes_from_parent: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        traits: Dict[str, float],
        emotion_state: Dict[str, Any],
        drive_levels: Dict[str, float],
        snapshot_type: SnapshotType,
        parent_id: Optional[str] = None,
        label: str = "",
        description: str = ""
    ) -> "PersonalitySnapshot":
        """创建新快照"""
        snapshot_id = f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{snapshot_type.value}"
        
        # 计算与父快照的变化
        changes = {}
        if parent_id and parent_id in SNAPSHOT_STORE:
            parent = SNAPSHOT_STORE[parent_id]
            for trait_name, trait_value in traits.items():
                if trait_name in parent.traits:
                    delta = trait_value - parent.traits[trait_name]
                    if abs(delta) > 0.001:
                        changes[trait_name] = delta
        
        return cls(
            id=snapshot_id,
            timestamp=datetime.now().isoformat(),
            snapshot_type=snapshot_type,
            traits=traits,
            emotion_state=emotion_state,
            drive_levels=drive_levels,
            label=label,
            description=description,
            parent_id=parent_id,
            changes_from_parent=changes
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "snapshot_type": self.snapshot_type.value,
            "traits": self.traits,
            "emotion_state": self.emotion_state,
            "drive_levels": self.drive_levels,
            "label": self.label,
            "description": self.description,
            "parent_id": self.parent_id,
            "changes_from_parent": self.changes_from_parent,
            "user_visible": self.user_visible
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PersonalitySnapshot":
        """从字典创建"""
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            snapshot_type=SnapshotType(data["snapshot_type"]),
            traits=data["traits"],
            emotion_state=data["emotion_state"],
            drive_levels=data["drive_levels"],
            label=data.get("label", ""),
            description=data.get("description", ""),
            parent_id=data.get("parent_id"),
            changes_from_parent=data.get("changes_from_parent", {}),
            user_visible=data.get("user_visible", True)
        )


# 快照存储（内存中，实际应用中应持久化到数据库）
SNAPSHOT_STORE: Dict[str, PersonalitySnapshot] = {}
SNAPSHOT_INDEX: List[str] = []  # 按时间顺序的快照ID列表


class SnapshotManager:
    """快照管理器"""
    
    def __init__(self, max_snapshots: int = 100):
        self.max_snapshots = max_snapshots
        self.snapshots: Dict[str, PersonalitySnapshot] = {}
        self.index: List[str] = []  # 按时间顺序的快照ID
        self.latest_id: Optional[str] = None
    
    def create_snapshot(
        self,
        traits: Dict[str, float],
        emotion_state: Dict[str, Any],
        drive_levels: Dict[str, float],
        snapshot_type: SnapshotType,
        label: str = "",
        description: str = "",
        user_visible: bool = True
    ) -> PersonalitySnapshot:
        """创建新快照"""
        # 获取父快照
        parent_id = self.latest_id
        
        snapshot = PersonalitySnapshot.create(
            traits=traits,
            emotion_state=emotion_state,
            drive_levels=drive_levels,
            snapshot_type=snapshot_type,
            parent_id=parent_id,
            label=label,
            description=description
        )
        snapshot.user_visible = user_visible
        
        # 存储
        self.snapshots[snapshot.id] = snapshot
        self.index.append(snapshot.id)
        self.latest_id = snapshot.id
        
        # 清理旧快照
        self._cleanup_old_snapshots()
        
        return snapshot
    
    def _cleanup_old_snapshots(self):
        """清理旧快照，保留最近的"""
        while len(self.snapshots) > self.max_snapshots:
            # 保留里程碑快照和手动快照
            auto_snapshots = [
                sid for sid in self.index
                if self.snapshots[sid].snapshot_type in [SnapshotType.AUTO, SnapshotType.BEFORE_CHANGE]
            ]
            if auto_snapshots:
                old_id = auto_snapshots[0]
                del self.snapshots[old_id]
                self.index.remove(old_id)
    
    def get_snapshot(self, snapshot_id: str) -> Optional[PersonalitySnapshot]:
        """获取指定快照"""
        return self.snapshots.get(snapshot_id)
    
    def get_latest_snapshot(self) -> Optional[PersonalitySnapshot]:
        """获取最新快照"""
        if self.latest_id:
            return self.snapshots.get(self.latest_id)
        return None
    
    def get_snapshots_by_type(self, snapshot_type: SnapshotType) -> List[PersonalitySnapshot]:
        """按类型获取快照"""
        return [s for s in self.snapshots.values() if s.snapshot_type == snapshot_type]
    
    def get_snapshots_in_range(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[PersonalitySnapshot]:
        """获取时间范围内的快照"""
        result = []
        for snapshot in self.snapshots.values():
            ts = datetime.fromisoformat(snapshot.timestamp)
            if start_time and ts < start_time:
                continue
            if end_time and ts > end_time:
                continue
            result.append(snapshot)
        return sorted(result, key=lambda s: s.timestamp)
    
    def list_snapshots(self, limit: int = 20, include_hidden: bool = False) -> List[Dict]:
        """列出快照（摘要）"""
        snapshots = list(self.snapshots.values())
        if not include_hidden:
            snapshots = [s for s in snapshots if s.user_visible]
        
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        
        return [
            {
                "id": s.id,
                "timestamp": s.timestamp,
                "type": s.snapshot_type.value,
                "label": s.label,
                "description": s.description,
                "trait_changes": len(s.changes_from_parent)
            }
            for s in snapshots[:limit]
        ]
    
    def compare_snapshots(
        self,
        snapshot_id1: str,
        snapshot_id2: str
    ) -> Optional[Dict]:
        """对比两个快照"""
        snap1 = self.snapshots.get(snapshot_id1)
        snap2 = self.snapshots.get(snapshot_id2)
        
        if not snap1 or not snap2:
            return None
        
        # 特征对比
        trait_diff = {}
        for trait_name in set(snap1.traits.keys()) | set(snap2.traits.keys()):
            val1 = snap1.traits.get(trait_name, 0)
            val2 = snap2.traits.get(trait_name, 0)
            delta = val2 - val1
            if abs(delta) > 0.001:
                trait_diff[trait_name] = {
                    "before": val1,
                    "after": val2,
                    "delta": delta,
                    "change_pct": (delta / val1 * 100) if val1 != 0 else 0
                }
        
        return {
            "snapshot1": {
                "id": snap1.id,
                "timestamp": snap1.timestamp,
                "type": snap1.snapshot_type.value
            },
            "snapshot2": {
                "id": snap2.id,
                "timestamp": snap2.timestamp,
                "type": snap2.snapshot_type.value
            },
            "trait_differences": trait_diff,
            "duration": self._calculate_duration(snap1.timestamp, snap2.timestamp)
        }
    
    def _calculate_duration(self, time1: str, time2: str) -> str:
        """计算时间差"""
        dt1 = datetime.fromisoformat(time1)
        dt2 = datetime.fromisoformat(time2)
        delta = dt2 - dt1
        
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    def rollback_to(self, snapshot_id: str) -> Optional[Dict]:
        """回滚到指定快照"""
        target = self.snapshots.get(snapshot_id)
        if not target:
            return None
        
        # 创建回滚前快照
        current = self.get_latest_snapshot()
        rollback_snapshot = None
        if current:
            rollback_snapshot = self.create_snapshot(
                traits=current.traits.copy(),
                emotion_state=current.emotion_state.copy(),
                drive_levels=current.drive_levels.copy(),
                snapshot_type=SnapshotType.BACKUP,
                label="Pre-rollback backup",
                description=f"快照回滚前的备份"
            )
        
        # 创建回滚后快照
        restored = self.create_snapshot(
            traits=target.traits.copy(),
            emotion_state=target.emotion_state.copy(),
            drive_levels=target.drive_levels.copy(),
            snapshot_type=SnapshotType.MANUAL,
            label=f"Rollback to {snapshot_id}",
            description=f"从 {snapshot_id} 恢复"
        )
        
        return {
            "restored_snapshot": restored.to_dict(),
            "rollback_backup": rollback_snapshot.to_dict() if rollback_snapshot else None,
            "changes": target.changes_from_parent
        }
    
    def export_snapshots(self) -> List[Dict]:
        """导出所有快照"""
        return [s.to_dict() for s in self.snapshots.values()]
    
    def import_snapshots(self, data: List[Dict]):
        """导入快照"""
        for snapshot_data in data:
            snapshot = PersonalitySnapshot.from_dict(snapshot_data)
            self.snapshots[snapshot.id] = snapshot
            if snapshot.id not in self.index:
                self.index.append(snapshot.id)
        
        # 更新最新ID
        if self.index:
            self.index.sort()
            self.latest_id = self.index[-1]
    
    def get_timeline(self, limit: int = 30) -> List[Dict]:
        """获取人格演化时间线"""
        snapshots = self.list_snapshots(limit=limit, include_hidden=False)
        
        timeline = []
        for i, snap_summary in enumerate(snapshots):
            snap = self.snapshots.get(snap_summary["id"])
            if not snap:
                continue
            
            entry = {
                "timestamp": snap.timestamp,
                "type": snap.snapshot_type.value,
                "label": snap.label or snap.snapshot_type.value,
                "description": snap.description,
                "significant_changes": []
            }
            
            # 标记显著变化
            for trait_name, delta in snap.changes_from_parent.items():
                if abs(delta) > 0.02:  # 2%以上变化
                    direction = "↑" if delta > 0 else "↓"
                    entry["significant_changes"].append(f"{trait_name} {direction}{abs(delta)*100:.1f}%")
            
            timeline.append(entry)
        
        return timeline


# 全局快照管理器实例
snapshot_manager = SnapshotManager()
