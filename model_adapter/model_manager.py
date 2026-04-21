"""
Neshama Model Adapter Layer - Model Manager
模型管理：分组、成本统计、调用量监控、降级策略

功能：
- 模型分组/分类
- 成本统计与分析
- 调用量监控
- 降级策略管理
- 预算控制
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """模型层级"""
    TIER_1_CHEAP = "tier_1_cheap"       # 第一梯队：低价先试
    TIER_2_FIXED = "tier_2_fixed"       # 第二梯队：月费固定
    TIER_3_CODING = "tier_3_coding"     # 第三梯队：编程类
    TIER_4_PREMIUM = "tier_4_premium"   # 第四梯队：高端旗舰


class CostUnit(Enum):
    """计费单位"""
    PER_1K_TOKENS = "per_1k_tokens"     # 每千token
    PER_CALL = "per_call"               # 每次调用
    MONTHLY = "monthly"                 # 月费


@dataclass
class ModelPricing:
    """模型定价信息"""
    model_id: str
    provider: str
    
    # 输入定价 (每1K token)
    input_price: float = 0.0
    
    # 输出定价 (每1K token)
    output_price: float = 0.0
    
    # 固定费用
    fixed_price: float = 0.0
    
    # 计费单位
    cost_unit: CostUnit = CostUnit.PER_1K_TOKENS
    
    # 货币单位
    currency: str = "CNY"
    
    @property
    def input_price_per_token(self) -> float:
        """输入单价 (每token)"""
        return self.input_price / 1000
    
    @property
    def output_price_per_token(self) -> float:
        """输出单价 (每token)"""
        return self.output_price / 1000
    
    def calculate_cost(
        self, 
        input_tokens: int = 0, 
        output_tokens: int = 0,
        calls: int = 1
    ) -> float:
        """计算成本"""
        if self.cost_unit == CostUnit.MONTHLY:
            return self.fixed_price
        elif self.cost_unit == CostUnit.PER_CALL:
            return self.fixed_price * calls
        else:
            return (input_tokens * self.input_price_per_token + 
                    output_tokens * self.output_price_per_token)


@dataclass
class CallRecord:
    """调用记录"""
    timestamp: datetime
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    success: bool
    error: Optional[str] = None
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelGroup:
    """模型分组"""
    name: str
    tier: ModelTier
    models: List[str] = field(default_factory=list)
    description: str = ""
    
    # 降级策略
    fallback_models: List[str] = field(default_factory=list)
    
    # 启用状态
    enabled: bool = True
    
    # 预算限制
    daily_budget: float = 0.0
    monthly_budget: float = 0.0
    
    @property
    def primary_model(self) -> Optional[str]:
        """主模型"""
        return self.models[0] if self.models else None


class CostTracker:
    """成本追踪器"""
    
    def __init__(self):
        self._records: List[CallRecord] = []
        self._daily_cost: Dict[str, float] = defaultdict(float)
        self._monthly_cost: Dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()
    
    async def record(self, record: CallRecord):
        """记录调用"""
        async with self._lock:
            self._records.append(record)
            
            # 更新每日/每月成本
            provider = record.provider
            self._daily_cost[provider] += record.cost
            self._monthly_cost[provider] += record.cost
    
    def get_daily_cost(self, provider: Optional[str] = None) -> float:
        """获取当日成本"""
        if provider:
            return self._daily_cost.get(provider, 0.0)
        return sum(self._daily_cost.values())
    
    def get_monthly_cost(self, provider: Optional[str] = None) -> float:
        """获取当月成本"""
        if provider:
            return self._monthly_cost.get(provider, 0.0)
        return sum(self._monthly_cost.values())
    
    def get_cost_by_model(self, model: str) -> float:
        """获取指定模型的总成本"""
        return sum(r.cost for r in self._records if r.model == model)
    
    def get_total_cost(self) -> float:
        """获取总成本"""
        return sum(r.cost for r in self._records)
    
    def get_records(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None
    ) -> List[CallRecord]:
        """获取调用记录"""
        records = self._records
        
        if start_time:
            records = [r for r in records if r.timestamp >= start_time]
        if end_time:
            records = [r for r in records if r.timestamp <= end_time]
        if model:
            records = [r for r in records if r.model == model]
        if provider:
            records = [r for r in records if r.provider == provider]
        
        return records


class UsageMonitor:
    """使用量监控"""
    
    def __init__(self):
        self._call_counts: Dict[str, int] = defaultdict(int)
        self._input_tokens: Dict[str, int] = defaultdict(int)
        self._output_tokens: Dict[str, int] = defaultdict(int)
        self._success_counts: Dict[str, int] = defaultdict(int)
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def record(self, record: CallRecord):
        """记录使用"""
        async with self._lock:
            model = record.model
            
            self._call_counts[model] += 1
            self._input_tokens[model] += record.input_tokens
            self._output_tokens[model] += record.output_tokens
            
            if record.success:
                self._success_counts[model] += 1
            else:
                self._failure_counts[model] += 1
            
            # 记录延迟 (保留最近100条)
            if record.latency_ms > 0:
                self._latencies[model].append(record.latency_ms)
                if len(self._latencies[model]) > 100:
                    self._latencies[model] = self._latencies[model][-100:]
    
    def get_stats(self, model: str) -> Dict[str, Any]:
        """获取模型统计"""
        latencies = self._latencies.get(model, [])
        
        return {
            "model": model,
            "total_calls": self._call_counts.get(model, 0),
            "success_calls": self._success_counts.get(model, 0),
            "failure_calls": self._failure_counts.get(model, 0),
            "total_input_tokens": self._input_tokens.get(model, 0),
            "total_output_tokens": self._output_tokens.get(model, 0),
            "total_tokens": self._input_tokens.get(model, 0) + self._output_tokens.get(model, 0),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "p50_latency_ms": self._percentile(latencies, 50),
            "p95_latency_ms": self._percentile(latencies, 95),
            "p99_latency_ms": self._percentile(latencies, 99),
        }
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


class FallbackManager:
    """降级管理器"""
    
    def __init__(self):
        self._fallback_chains: Dict[str, List[str]] = {}
        self._current_index: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    def register_fallback_chain(self, model: str, chain: List[str]):
        """注册降级链"""
        self._fallback_chains[model] = chain
        self._current_index[model] = 0
    
    def get_fallback(self, model: str) -> Optional[str]:
        """获取降级模型"""
        if model not in self._fallback_chains:
            return None
        
        chain = self._fallback_chains[model]
        current = self._current_index[model]
        
        if current < len(chain) - 1:
            fallback = chain[current + 1]
            return fallback
        return None
    
    async def record_failure(self, model: str):
        """记录失败，触发降级"""
        async with self._lock:
            if model in self._current_index:
                self._current_index[model] += 1
                logger.warning(f"[FallbackManager] Fallback triggered for {model}, "
                             f"now using index {self._current_index[model]}")
    
    async def reset(self, model: str):
        """重置降级索引"""
        async with self._lock:
            if model in self._fallback_chains:
                self._current_index[model] = 0


class BudgetController:
    """预算控制器"""
    
    def __init__(self, daily_budget: float = 0, monthly_budget: float = 0):
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        
        self._daily_spent: Dict[str, float] = defaultdict(float)
        self._monthly_spent: Dict[str, float] = defaultdict(float)
        self._lock = asyncio.Lock()
    
    async def check_budget(
        self, 
        provider: str, 
        estimated_cost: float
    ) -> bool:
        """检查预算是否足够"""
        async with self._lock:
            # 检查每日预算
            if self.daily_budget > 0:
                if self._daily_spent[provider] + estimated_cost > self.daily_budget:
                    logger.warning(f"Daily budget exceeded for {provider}")
                    return False
            
            # 检查每月预算
            if self.monthly_budget > 0:
                if self._monthly_spent[provider] + estimated_cost > self.monthly_budget:
                    logger.warning(f"Monthly budget exceeded for {provider}")
                    return False
            
            return True
    
    async def record_spending(
        self, 
        provider: str, 
        cost: float,
        date: Optional[datetime] = None
    ):
        """记录支出"""
        async with self._lock:
            self._daily_spent[provider] += cost
            self._monthly_spent[provider] += cost
    
    def get_remaining_budget(self, provider: str) -> Dict[str, float]:
        """获取剩余预算"""
        return {
            "daily_remaining": max(0, self.daily_budget - self._daily_spent.get(provider, 0)),
            "monthly_remaining": max(0, self.monthly_budget - self._monthly_spent.get(provider, 0))
        }


class ModelManager:
    """
    模型管理器
    
    统一管理所有模型，提供：
    - 模型分组
    - 成本统计
    - 使用监控
    - 降级策略
    - 预算控制
    """
    
    def __init__(
        self,
        daily_budget: float = 0,
        monthly_budget: float = 0
    ):
        self._groups: Dict[str, ModelGroup] = {}
        self._pricing: Dict[str, ModelPricing] = {}
        self._provider_mapping: Dict[str, str] = {}  # model -> provider
        
        self.cost_tracker = CostTracker()
        self.usage_monitor = UsageMonitor()
        self.fallback_manager = FallbackManager()
        self.budget_controller = BudgetController(daily_budget, monthly_budget)
        
        self._lock = asyncio.Lock()
        
        # 初始化默认分组
        self._init_default_groups()
    
    def _init_default_groups(self):
        """初始化默认分组"""
        # 第一梯队：低价先试
        self.register_group(ModelGroup(
            name="tier1_cheap",
            tier=ModelTier.TIER_1_CHEAP,
            models=["qwen-turbo", "doubao-lite-32k", "ernie-speed-128k"],
            fallback_models=["qwen-plus", "doubao-pro-32k", "ernie-lite-8k"],
            description="第一梯队：低价优先，适合日常使用"
        ))
        
        # 第二梯队：月费固定
        self.register_group(ModelGroup(
            name="tier2_fixed",
            tier=ModelTier.TIER_2_FIXED,
            models=["glm-4-flash", "abab6.5s-chat"],
            fallback_models=["glm-4", "abab6.5-chat"],
            description="第二梯队：月费固定，适合高频使用"
        ))
        
        # 第三梯队：编程类
        self.register_group(ModelGroup(
            name="tier3_coding",
            tier=ModelTier.TIER_3_CODING,
            models=["qwen-coder-plus", "qwen-coder"],
            fallback_models=["qwen-plus"],
            description="第三梯队：编程专用模型"
        ))
        
        # 第四梯队：高端旗舰
        self.register_group(ModelGroup(
            name="tier4_premium",
            tier=ModelTier.TIER_4_PREMIUM,
            models=["qwen-max", "qwen-max-longcontext", "ernie-4.0-8k-latest"],
            fallback_models=["qwen-plus", "ernie-speed-128k"],
            description="第四梯队：高端旗舰，适合复杂任务"
        ))
    
    def register_group(self, group: ModelGroup):
        """注册模型分组"""
        self._groups[group.name] = group
        
        # 注册降级链
        if group.fallback_models and group.models:
            primary = group.models[0]
            chain = [primary] + group.fallback_models
            self.fallback_manager.register_fallback_chain(primary, chain)
    
    def register_pricing(self, pricing: ModelPricing):
        """注册模型定价"""
        self._pricing[pricing.model_id] = pricing
    
    def register_model_provider(self, model: str, provider: str):
        """注册模型与Provider的映射"""
        self._provider_mapping[model] = provider
    
    def get_group(self, name: str) -> Optional[ModelGroup]:
        """获取模型分组"""
        return self._groups.get(name)
    
    def get_model_by_tier(self, tier: ModelTier) -> List[str]:
        """根据层级获取模型列表"""
        for group in self._groups.values():
            if group.tier == tier:
                return group.models.copy()
        return []
    
    def get_provider(self, model: str) -> Optional[str]:
        """获取模型对应的Provider"""
        return self._provider_mapping.get(model)
    
    def get_pricing(self, model: str) -> Optional[ModelPricing]:
        """获取模型定价"""
        return self._pricing.get(model)
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> float:
        """计算单次调用成本"""
        pricing = self.get_pricing(model)
        if not pricing:
            return 0.0
        return pricing.calculate_cost(input_tokens, output_tokens)
    
    async def record_call(
        self,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录一次调用"""
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        record = CallRecord(
            timestamp=datetime.now(),
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            success=success,
            error=error,
            cost=cost,
            metadata=metadata or {}
        )
        
        # 记录到各组件
        await self.cost_tracker.record(record)
        await self.usage_monitor.record(record)
        
        if not success:
            await self.fallback_manager.record_failure(model)
        
        # 记录支出
        await self.budget_controller.record_spending(provider, cost)
    
    async def select_model(
        self,
        tier: Optional[ModelTier] = None,
        preferred_model: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> Optional[str]:
        """智能选择模型"""
        # 如果指定了模型，直接返回
        if preferred_model:
            return preferred_model
        
        # 根据任务类型选择
        if task_type == "coding":
            tier = ModelTier.TIER_3_CODING
        elif task_type == "fast":
            tier = ModelTier.TIER_1_CHEAP
        
        # 根据层级选择
        if tier:
            models = self.get_model_by_tier(tier)
            if models:
                return models[0]  # 返回主模型
        
        return None
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本汇总"""
        return {
            "total_cost": self.cost_tracker.get_total_cost(),
            "daily_cost": self.cost_tracker.get_daily_cost(),
            "monthly_cost": self.cost_tracker.get_monthly_cost(),
            "budget_remaining": self.budget_controller.get_remaining_budget("all")
        }
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """获取使用量汇总"""
        summary = {}
        for model in set(self._provider_mapping.keys()):
            stats = self.usage_monitor.get_stats(model)
            if stats["total_calls"] > 0:
                summary[model] = stats
        return summary
    
    def get_full_report(self) -> Dict[str, Any]:
        """获取完整报告"""
        return {
            "cost_summary": self.get_cost_summary(),
            "usage_summary": self.get_usage_summary(),
            "model_groups": {
                name: {
                    "models": group.models,
                    "tier": group.tier.value,
                    "enabled": group.enabled,
                    "primary_model": group.primary_model
                }
                for name, group in self._groups.items()
            },
            "pricing": {
                model_id: {
                    "input_price": p.input_price,
                    "output_price": p.output_price,
                    "cost_unit": p.cost_unit.value,
                    "currency": p.currency
                }
                for model_id, p in self._pricing.items()
            }
        }


# 全局实例
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """获取全局模型管理器"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def init_model_manager(
    daily_budget: float = 0,
    monthly_budget: float = 0
) -> ModelManager:
    """初始化模型管理器"""
    global _model_manager
    _model_manager = ModelManager(daily_budget, monthly_budget)
    return _model_manager
