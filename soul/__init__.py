# Soul层 - Neshama Agent灵魂系统
"""
Soul层：Agent的人格、行为模式、情绪反应等核心特质

核心模块：
- loader - 配置加载器

主要类：
- SoulLoader - Soul配置加载器
- SoulLoaderConfig - 加载器配置
"""

# 只导出 loader 模块，避免其他子模块的语法错误
from .loader import (
    SoulLoader,
    SoulLoaderConfig,
    SoulConfigBuilder,
    soul_loader,
    load_soul_config,
    create_soul_config,
    save_soul_config
)

# 注意：executor 模块存在导入问题，暂不导出
# 如需使用 Executor，请直接导入并修复语法错误
# from .executor import SoulExecutor, SoulConfig

__version__ = "2.0.0"

__all__ = [
    # Loader
    "SoulLoader",
    "SoulLoaderConfig",
    "SoulConfigBuilder",
    "soul_loader",
    "load_soul_config",
    "create_soul_config",
    "save_soul_config",
]
