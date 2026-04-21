# Soul层 - 人格稳定性检测
"""
人格稳定性检测：防止人格剧烈变化

功能：
- 监控人格特征变化速率
- 检测异常变化模式
- 触发稳定性保护机制
- 发送预警通知
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import numpy as np


class StabilityLevel(Enum):
    """稳定性等级"""
    STABLE = "stable"           # 稳定
    FLUCTUATING = "fluctuating"  # 波动中
    UNSTABLE = "unstable"       # 不稳定
    CRITICAL = "critical"      # 危险


class StabilityAction(Enum):
    """稳定性保护动作"""
    ALLOW = "allow"             # 允许变化
    SMOOTH = "smooth"           # 平滑变化
    BLOCK = "block"             # 阻止变化
    REVERT = "revert"           # 回滚变化
    ALERT = "alert"             # 发送警报


@dataclass
class StabilityThreshold:
    """稳定性阈值配置"""
    # 变化速率阈值（单位时间内的最大变化）
    change_rate_per_minute: float = 0.05
    change_rate_per_hour: float = 0.15
    change_rate_per_day: float = 0.30
    
    # 波动阈值
    max_fluctuation_range: float = 0.20  # 单个特征的最大波动范围
    max_consecutive_changes: int = 5      # 最大连续变化次数
    
    # 稳定性等级阈值
    stable_threshold: float = 0.70
    fluctuating_threshold: float = 0.50
    unstable_threshold: float = 0.30
    
    # 时间窗口
    short_window_minutes: int = 5
    medium_window_hours: int = 1
    long_window_days: int = 1


@dataclass
class TraitStabilityRecord:
    """特征稳定性记录"""
    trait_name: str
    value_history: List[Dict] = field(default_factory=list)
    
    # 统计指标
    mean_value: float = 0.5
    std_deviation: float = 0.0
    change_count: int = 0
    total_change: float = 0.0
    
    # 当前状态
    current_value: float = 0.5
    baseline_value: float = 0.5
    deviation_from_baseline: float = 0.0
    
    # 稳定性指标
    stability_score: float = 1.0  # 0-1，越高越稳定
    volatility_index: float = 0.0  # 波动指数
    
    def update(self, new_value: float, timestamp: datetime):
        """更新记录"""
        old_value = self.current_value
        delta = new_value - old_value
        
        self.value_history.append({
            "timestamp": timestamp.isoformat(),
            "value": new_value,
            "delta": delta
        })
        
        self.current_value = new_value
        self.change_count += 1
        self.total_change += abs(delta)
        self.deviation_from_baseline = abs(new_value - self.baseline_value)
        
        # 计算统计指标（保留最近100条记录）
        if len(self.value_history) > 100:
            self.value_history = self.value_history[-100:]
        
        self._recalculate_statistics()
        self._calculate_stability_score()
    
    def _recalculate_statistics(self):
        """重新计算统计指标"""
        if len(self.value_history) < 2:
            return
        
        values = [h["value"] for h in self.value_history]
        self.mean_value = np.mean(values)
        self.std_deviation = np.std(values)
    
    def _calculate_stability_score(self):
        """计算稳定性分数"""
        # 综合考虑：
        # 1. 与基线的偏离
        # 2. 波动幅度
        # 3. 变化频率
        
        baseline_deviation_penalty = min(self.deviation_from_baseline / 0.3, 1.0) * 0.4
        volatility_penalty = min(self.std_deviation / 0.1, 1.0) * 0.3
        
        # 归一化变化频率
        expected_changes_per_hour = 10  # 预期每小时最多10次
        change_rate = self.change_count / expected_changes_per_hour
        change_rate_penalty = min(change_rate, 1.0) * 0.3
        
        self.stability_score = 1.0 - (baseline_deviation_penalty + volatility_penalty + change_rate_penalty)
        self.stability_score = max(0.0, min(1.0, self.stability_score))
        
        self.volatility_index = self.std_deviation + (self.total_change / max(self.change_count, 1))


class StabilityMonitor:
    """稳定性监控器"""
    
    def __init__(self, thresholds: StabilityThreshold = None):
        self.thresholds = thresholds or StabilityThreshold()
        self.trait_records: Dict[str, TraitStabilityRecord] = {}
        self.global_stability_history: List[Dict] = []
        self.alerts: List[Dict] = []
    
    def register_trait(self, trait_name: str, initial_value: float, baseline: float = None):
        """注册需要监控的特征"""
        if baseline is None:
            baseline = initial_value
        
        self.trait_records[trait_name] = TraitStabilityRecord(
            trait_name=trait_name,
            current_value=initial_value,
            baseline_value=baseline
        )
    
    def update_trait(self, trait_name: str, new_value: float, timestamp: datetime = None):
        """更新特征值"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if trait_name not in self.trait_records:
            self.register_trait(trait_name, new_value)
        else:
            self.trait_records[trait_name].update(new_value, timestamp)
        
        # 记录全局稳定性
        self._update_global_stability(timestamp)
    
    def _update_global_stability(self, timestamp: datetime):
        """更新全局稳定性"""
        if not self.trait_records:
            return
        
        avg_stability = np.mean([r.stability_score for r in self.trait_records.values()])
        
        # 确定稳定性等级
        if avg_stability >= self.thresholds.stable_threshold:
            level = StabilityLevel.STABLE
        elif avg_stability >= self.thresholds.fluctuating_threshold:
            level = StabilityLevel.FLUCTUATING
        elif avg_stability >= self.thresholds.unstable_threshold:
            level = StabilityLevel.UNSTABLE
        else:
            level = StabilityLevel.CRITICAL
        
        self.global_stability_history.append({
            "timestamp": timestamp.isoformat(),
            "stability_score": avg_stability,
            "level": level.value,
            "trait_scores": {name: r.stability_score for name, r in self.trait_records.items()}
        })
        
        # 保留最近历史
        if len(self.global_stability_history) > 1000:
            self.global_stability_history = self.global_stability_history[-1000:]
    
    def check_proposed_change(
        self,
        trait_name: str,
        proposed_value: float,
        timestamp: datetime = None
    ) -> Dict[str, Any]:
        """检查提议的变化是否应该被允许"""
        if timestamp is None:
            timestamp = datetime.now()
        
        if trait_name not in self.trait_records:
            return {
                "allowed": True,
                "action": StabilityAction.ALLOW,
                "reason": "Trait not registered, allowing initial change"
            }
        
        record = self.trait_records[trait_name]
        current_value = record.current_value
        delta = proposed_value - current_value
        
        # 计算各种指标
        change_magnitude = abs(delta)
        deviation_from_baseline = abs(proposed_value - record.baseline_value)
        
        # 检查各个阈值
        concerns = []
        warnings = []
        
        # 1. 检查变化幅度
        if change_magnitude > self.thresholds.max_fluctuation_range:
            concerns.append(f"变化幅度过大: {change_magnitude:.3f} > {self.thresholds.max_fluctuation_range}")
        
        # 2. 检查与基线的偏离
        if deviation_from_baseline > 0.3:
            concerns.append(f"偏离基线过多: {deviation_from_baseline:.3f}")
        elif deviation_from_baseline > 0.2:
            warnings.append(f"开始偏离基线: {deviation_from_baseline:.3f}")
        
        # 3. 检查稳定性分数
        if record.stability_score < self.thresholds.unstable_threshold:
            concerns.append(f"特征稳定性极低: {record.stability_score:.3f}")
        
        # 4. 检查连续变化
        recent_changes = [h for h in record.value_history[-10:] if h["delta"] != 0]
        if len(recent_changes) >= self.thresholds.max_consecutive_changes:
            concerns.append(f"连续变化过多: {len(recent_changes)}")
        
        # 确定动作
        if len(concerns) >= 2:
            action = StabilityAction.BLOCK
            allowed = False
            reason = f"存在 {len(concerns)} 个严重问题，阻止变化"
        elif len(concerns) == 1:
            action = StabilityAction.SMOOTH
            allowed = True
            # 建议平滑后的值
            smoothed_delta = delta * 0.5
            proposed_value = current_value + smoothed_delta
            reason = f"变化过大，采用平滑策略: {smoothed_delta:.4f}"
        elif len(warnings) > 0:
            action = StabilityAction.ALLOW
            allowed = True
            reason = "存在警告但允许变化"
        else:
            action = StabilityAction.ALLOW
            allowed = True
            reason = "通过所有稳定性检查"
        
        return {
            "allowed": allowed,
            "action": action,
            "reason": reason,
            "proposed_value": proposed_value,
            "original_proposed": proposed_value if action != StabilityAction.SMOOTH else current_value + delta,
            "delta": proposed_value - current_value,
            "concerns": concerns,
            "warnings": warnings,
            "current_stability_score": record.stability_score
        }
    
    def get_stability_report(self) -> Dict:
        """获取稳定性报告"""
        if not self.trait_records:
            return {"status": "no_data", "message": "尚无稳定性数据"}
        
        avg_stability = np.mean([r.stability_score for r in self.trait_records.values()])
        
        # 确定当前等级
        if avg_stability >= self.thresholds.stable_threshold:
            level = StabilityLevel.STABLE
        elif avg_stability >= self.thresholds.fluctuating_threshold:
            level = StabilityLevel.FLUCTUATING
        elif avg_stability >= self.thresholds.unstable_threshold:
            level = StabilityLevel.UNSTABLE
        else:
            level = StabilityLevel.CRITICAL
        
        # 找出最不稳定的特征
        unstable_traits = [
            {"name": name, "stability_score": r.stability_score, "volatility": r.volatility_index}
            for name, r in self.trait_records.items()
            if r.stability_score < self.thresholds.fluctuating_threshold
        ]
        unstable_traits.sort(key=lambda x: x["stability_score"])
        
        # 获取最近的趋势
        recent_trend = "stable"
        if len(self.global_stability_history) >= 5:
            recent = [h["stability_score"] for h in self.global_stability_history[-5:]]
            if all(recent[i] > recent[i+1] for i in range(len(recent)-1)):
                recent_trend = "declining"
            elif all(recent[i] < recent[i+1] for i in range(len(recent)-1)):
                recent_trend = "improving"
        
        return {
            "overall_stability": avg_stability,
            "stability_level": level.value,
            "trend": recent_trend,
            "trait_count": len(self.trait_records),
            "unstable_traits": unstable_traits[:5],
            "trait_details": {
                name: {
                    "current_value": r.current_value,
                    "baseline": r.baseline_value,
                    "stability_score": r.stability_score,
                    "volatility_index": r.volatility_index,
                    "change_count": r.change_count
                }
                for name, r in self.trait_records.items()
            },
            "recent_alerts": self.alerts[-10:] if self.alerts else []
        }
    
    def create_checkpoint(self) -> Dict:
        """创建稳定性检查点"""
        return {
            "timestamp": datetime.now().isoformat(),
            "trait_records": {
                name: {
                    "current_value": r.current_value,
                    "baseline_value": r.baseline_value,
                    "stability_score": r.stability_score,
                    "value_history": r.value_history[-50:]  # 只保留最近50条
                }
                for name, r in self.trait_records.items()
            },
            "global_stability": self.global_stability_history[-100:]
        }
    
    def restore_from_checkpoint(self, checkpoint: Dict):
        """从检查点恢复"""
        self.trait_records = {}
        for name, data in checkpoint["trait_records"].items():
            record = TraitStabilityRecord(
                trait_name=name,
                value_history=data.get("value_history", []),
                current_value=data["current_value"],
                baseline_value=data["baseline_value"],
                stability_score=data["stability_score"]
            )
            self.trait_records[name] = record
        
        self.global_stability_history = checkpoint.get("global_stability", [])
    
    def emit_alert(self, alert_type: str, message: str, severity: str = "warning"):
        """发送警报"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message,
            "severity": severity
        }
        self.alerts.append(alert)
        
        # 保留最近100条警报
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        return alert


# 全局稳定性监控器实例
stability_monitor = StabilityMonitor()


# 便捷函数
def check_trait_change(trait_name: str, proposed_value: float) -> Dict:
    """检查特征变化的便捷函数"""
    return stability_monitor.check_proposed_change(trait_name, proposed_value)


def get_current_stability() -> Dict:
    """获取当前稳定性的便捷函数"""
    return stability_monitor.get_stability_report()


def update_trait_value(trait_name: str, value: float):
    """更新特征值的便捷函数"""
    stability_monitor.update_trait(trait_name, value)
