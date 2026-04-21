"""
Neshama Model Adapter Layer
模型接入层

支持多种模型提供商的统一接入
"""

from .config import Config, get_config, init_config, ModelConfig
from .model_adapter import ModelAdapter
from .router import ModelRouter, RouterStrategy, get_router
from .model_manager import (
    ModelManager,
    ModelGroup,
    ModelTier,
    CostTracker,
    UsageMonitor,
    FallbackManager,
    BudgetController,
    get_model_manager,
    init_model_manager
)
from .benchmark import (
    BenchmarkSuite,
    BenchmarkRunner,
    BenchmarkTask,
    BenchmarkResult,
    ModelBenchmarkReport,
    QualityEvaluator,
    ComparisonReport,
    TaskCategory,
    create_standard_benchmark
)

__version__ = "2.0.0"

__all__ = [
    # Config
    "Config",
    "get_config",
    "init_config",
    "ModelConfig",
    
    # Adapter
    "ModelAdapter",
    
    # Router
    "ModelRouter",
    "RouterStrategy",
    "get_router",
    
    # Manager
    "ModelManager",
    "ModelGroup",
    "ModelTier",
    "CostTracker",
    "UsageMonitor",
    "FallbackManager",
    "BudgetController",
    "get_model_manager",
    "init_model_manager",
    
    # Benchmark
    "BenchmarkSuite",
    "BenchmarkRunner",
    "BenchmarkTask",
    "BenchmarkResult",
    "ModelBenchmarkReport",
    "QualityEvaluator",
    "ComparisonReport",
    "TaskCategory",
    "create_standard_benchmark",
]
