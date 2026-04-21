"""
Neshama Model Adapter Layer Configuration - 完善版
模型接入层配置文件

支持多种模型提供商的统一配置管理
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import yaml


@dataclass
class ModelConfig:
    """单个模型配置"""
    name: str
    provider: str
    model_id: str
    api_key: str = ""
    base_url: str = ""
    api_version: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    retry_times: int = 3
    enabled: bool = True
    priority: int = 100  # 优先级，数字越小优先级越高
    weight: int = 1  # 负载均衡权重
    # 定价 (CNY / 1M tokens)
    input_price: float = 0.0
    output_price: float = 0.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """提供商配置"""
    provider_name: str
    enabled: bool = True
    api_key: str = ""
    base_url: str = ""
    api_version: str = ""
    timeout: int = 60
    retry_times: int = 3
    models: List[ModelConfig] = field(default_factory=list)


# ============================================================
# 模型定价参考 (单位: CNY / 百万 tokens)
# 更新时间: 2024
# ============================================================

MODEL_PRICING = {
    # ========== 百炼 (阿里云) ==========
    "dashscope": {
        "qwen-max": {"input": 40, "output": 120, "description": "超大规模模型"},
        "qwen-max-longcontext": {"input": 40, "output": 120, "description": "超长上下文"},
        "qwen-plus": {"input": 4, "output": 12, "description": "增强版"},
        "qwen-turbo": {"input": 2, "output": 6, "description": "快速版"},
        "qwen-coder-plus": {"input": 8, "output": 24, "description": "编程增强版"},
        "qwen-coder": {"input": 2, "output": 6, "description": "编程版"},
        "qwq-32b": {"input": 4, "output": 12, "description": "思考模型"},
        "text-embedding-v3": {"input": 0.1, "output": 0, "description": "Embedding v3"},
    },
    
    # ========== 火山引擎 ==========
    "volcengine": {
        "doubao-pro-128k": {"input": 5, "output": 10, "description": "128K上下文"},
        "doubao-pro-32k": {"input": 3, "output": 6, "description": "32K上下文"},
        "doubao-lite-32k": {"input": 1, "output": 2, "description": "轻量版"},
        "doubao-pro": {"input": 3, "output": 6, "description": "标准版"},
        "doubao-embedding": {"input": 0.1, "output": 0, "description": "Embedding"},
    },
    
    # ========== 百度千帆 ==========
    "qianfan": {
        "ernie-4.0-8k-latest": {"input": 120, "output": 120, "description": "ERNIE 4.0 最新版"},
        "ernie-4.0-8k": {"input": 120, "output": 120, "description": "ERNIE 4.0 标准版"},
        "ernie-3.5-8k": {"input": 12, "output": 12, "description": "ERNIE 3.5"},
        "ernie-speed-128k": {"input": 4, "output": 8, "description": "高速版 128K"},
        "ernie-speed-32k": {"input": 4, "output": 8, "description": "高速版 32K"},
        "ernie-lite-8k": {"input": 0.8, "output": 2, "description": "轻量版 8K"},
        "embedding-v1": {"input": 0.5, "output": 0, "description": "Embedding v1"},
    },
    
    # ========== MiniMax ==========
    "minimax": {
        "abab6.5s-chat": {"input": 10, "output": 10, "description": "增强版 6.5S"},
        "abab6.5-chat": {"input": 5, "output": 5, "description": "标准版 6.5"},
        "abab5.5-chat": {"input": 1, "output": 2, "description": "5.5版本"},
        "abab5s-chat": {"input": 1, "output": 1, "description": "5S版本"},
        "MiniMax-Text-01": {"input": 5, "output": 15, "description": "文本模型 01"},
        "MiniMax-Embedding-01": {"input": 0.1, "output": 0, "description": "Embedding"},
    },
    
    # ========== 智谱AI ==========
    "zhipu": {
        "glm-4": {"input": 100, "output": 100, "description": "GLM-4 标准版"},
        "glm-4-plus": {"input": 100, "output": 100, "description": "GLM-4 Plus"},
        "glm-4-flash": {"input": 1, "output": 1, "description": "GLM-4 Flash"},
        "glm-4-air": {"input": 1, "output": 2, "description": "GLM-4 Air"},
        "glm-4-airx": {"input": 2, "output": 4, "description": "GLM-4 AirX"},
        "glm-4-long": {"input": 30, "output": 60, "description": "GLM-4 长文本版"},
        "glm-4v": {"input": 100, "output": 100, "description": "GLM-4V 视觉版"},
        "glm-3-turbo": {"input": 1, "output": 1, "description": "GLM-3 Turbo"},
        "embedding-2": {"input": 0.1, "output": 0, "description": "Embedding v2"},
    },
}


class Config:
    """配置管理类"""
    
    DEFAULT_CONFIG = {
        "version": "2.0.0",
        "default_model": "qwen-plus",
        
        # 第一梯队：低价先试
        "tier1_cheap": {
            "primary": "qwen-turbo",
            "fallback": ["doubao-lite-32k", "ernie-speed-128k", "glm-4-flash"]
        },
        
        # 第二梯队：月费固定
        "tier2_fixed": {
            "primary": "glm-4-flash",
            "fallback": ["abab6.5s-chat"]
        },
        
        # 第三梯队：编程类
        "tier3_coding": {
            "primary": "qwen-coder-plus",
            "fallback": ["qwen-coder", "qwen-plus"]
        },
        
        # 第四梯队：高端旗舰
        "tier4_premium": {
            "primary": "qwen-max",
            "fallback": ["qwen-plus", "ernie-4.0-8k-latest"]
        },
        
        "providers": {
            "dashscope": {
                "enabled": True,
                "api_key": "${DASHSCOPE_API_KEY}",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "timeout": 60,
                "models": [
                    {
                        "name": "qwen-turbo",
                        "model_id": "qwen-turbo",
                        "max_tokens": 8192,
                        "temperature": 0.7,
                        "priority": 5,
                        "input_price": 2,
                        "output_price": 6
                    },
                    {
                        "name": "qwen-plus",
                        "model_id": "qwen-plus",
                        "max_tokens": 32768,
                        "temperature": 0.7,
                        "priority": 10,
                        "input_price": 4,
                        "output_price": 12
                    },
                    {
                        "name": "qwen-max",
                        "model_id": "qwen-max",
                        "max_tokens": 8192,
                        "temperature": 0.7,
                        "priority": 20,
                        "input_price": 40,
                        "output_price": 120
                    },
                    {
                        "name": "qwen-max-longcontext",
                        "model_id": "qwen-max-longcontext",
                        "max_tokens": 32768,
                        "temperature": 0.7,
                        "priority": 25,
                        "input_price": 40,
                        "output_price": 120
                    },
                    {
                        "name": "qwen-coder-plus",
                        "model_id": "qwen-coder-plus",
                        "max_tokens": 8192,
                        "temperature": 0.7,
                        "priority": 15,
                        "input_price": 8,
                        "output_price": 24
                    },
                    {
                        "name": "qwen-coder",
                        "model_id": "qwen-coder",
                        "max_tokens": 8192,
                        "temperature": 0.7,
                        "priority": 12,
                        "input_price": 2,
                        "output_price": 6
                    },
                    {
                        "name": "qwq-32b",
                        "model_id": "qwq-32b",
                        "max_tokens": 32768,
                        "temperature": 0.7,
                        "priority": 18,
                        "input_price": 4,
                        "output_price": 12
                    },
                    {
                        "name": "text-embedding-v3",
                        "model_id": "text-embedding-v3",
                        "max_tokens": 8192,
                        "temperature": 0.0,
                        "priority": 30,
                        "input_price": 0.1,
                        "output_price": 0
                    },
                ]
            },
            
            "volcengine": {
                "enabled": True,
                "api_key": "${VOLCENGINE_API_KEY}",
                "account_id": "${VOLCENGINE_ACCOUNT_ID}",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "timeout": 60,
                "models": [
                    {
                        "name": "doubao-pro-128k",
                        "model_id": "doubao-pro-128k",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 8,
                        "input_price": 5,
                        "output_price": 10
                    },
                    {
                        "name": "doubao-pro-32k",
                        "model_id": "doubao-pro-32k",
                        "max_tokens": 32768,
                        "temperature": 0.7,
                        "priority": 10,
                        "input_price": 3,
                        "output_price": 6
                    },
                    {
                        "name": "doubao-lite-32k",
                        "model_id": "doubao-lite-32k",
                        "max_tokens": 32000,
                        "temperature": 0.7,
                        "priority": 5,
                        "input_price": 1,
                        "output_price": 2
                    },
                    {
                        "name": "doubao-pro-4k",
                        "model_id": "doubao-pro-4k",
                        "max_tokens": 4096,
                        "temperature": 0.7,
                        "priority": 4,
                        "input_price": 1,
                        "output_price": 2
                    },
                ]
            },
            
            "qianfan": {
                "enabled": True,
                "api_key": "${QIANFAN_ACCESS_KEY}",
                "secret_key": "${QIANFAN_SECRET_KEY}",
                "base_url": "https://qianfan.baidubce.com/v2",
                "timeout": 60,
                "models": [
                    {
                        "name": "ernie-4.0-8k-latest",
                        "model_id": "ernie-4.0-8k-latest",
                        "max_tokens": 8192,
                        "temperature": 0.7,
                        "priority": 20,
                        "input_price": 120,
                        "output_price": 120
                    },
                    {
                        "name": "ernie-speed-128k",
                        "model_id": "ernie-speed-128k",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 5,
                        "input_price": 4,
                        "output_price": 8
                    },
                    {
                        "name": "ernie-speed-32k",
                        "model_id": "ernie-speed-32k",
                        "max_tokens": 32000,
                        "temperature": 0.7,
                        "priority": 8,
                        "input_price": 4,
                        "output_price": 8
                    },
                    {
                        "name": "ernie-3.5-8k",
                        "model_id": "ernie-3.5-8k",
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "priority": 12,
                        "input_price": 12,
                        "output_price": 12
                    },
                    {
                        "name": "ernie-lite-8k",
                        "model_id": "ernie-lite-8k",
                        "max_tokens": 2048,
                        "temperature": 0.7,
                        "priority": 4,
                        "input_price": 0.8,
                        "output_price": 2
                    },
                    {
                        "name": "embedding-v1",
                        "model_id": "embedding-v1",
                        "max_tokens": 2048,
                        "temperature": 0.0,
                        "priority": 30,
                        "input_price": 0.5,
                        "output_price": 0
                    },
                ]
            },
            
            "minimax": {
                "enabled": True,
                "api_key": "${MINIMAX_API_KEY}",
                "group_id": "${MINIMAX_GROUP_ID}",
                "base_url": "https://api.minimax.chat/v1",
                "timeout": 60,
                "models": [
                    {
                        "name": "abab6.5s-chat",
                        "model_id": "abab6.5s-chat",
                        "max_tokens": 16384,
                        "temperature": 0.7,
                        "priority": 10,
                        "input_price": 10,
                        "output_price": 10
                    },
                    {
                        "name": "abab6.5-chat",
                        "model_id": "abab6.5-chat",
                        "max_tokens": 16384,
                        "temperature": 0.7,
                        "priority": 12,
                        "input_price": 5,
                        "output_price": 5
                    },
                    {
                        "name": "abab5.5-chat",
                        "model_id": "abab5.5-chat",
                        "max_tokens": 8192,
                        "temperature": 0.7,
                        "priority": 8,
                        "input_price": 1,
                        "output_price": 2
                    },
                    {
                        "name": "MiniMax-Text-01",
                        "model_id": "MiniMax-Text-01",
                        "max_tokens": 32768,
                        "temperature": 0.7,
                        "priority": 15,
                        "input_price": 5,
                        "output_price": 15
                    },
                ]
            },
            
            "zhipu": {
                "enabled": True,
                "api_key": "${ZHIPU_API_KEY}",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "timeout": 60,
                "models": [
                    {
                        "name": "glm-4",
                        "model_id": "glm-4",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 10,
                        "input_price": 100,
                        "output_price": 100
                    },
                    {
                        "name": "glm-4-flash",
                        "model_id": "glm-4-flash",
                        "max_tokens": 32000,
                        "temperature": 0.7,
                        "priority": 4,
                        "input_price": 1,
                        "output_price": 1
                    },
                    {
                        "name": "glm-4-air",
                        "model_id": "glm-4-air",
                        "max_tokens": 32000,
                        "temperature": 0.7,
                        "priority": 6,
                        "input_price": 1,
                        "output_price": 2
                    },
                    {
                        "name": "glm-4-airx",
                        "model_id": "glm-4-airx",
                        "max_tokens": 32000,
                        "temperature": 0.7,
                        "priority": 8,
                        "input_price": 2,
                        "output_price": 4
                    },
                    {
                        "name": "glm-4-long",
                        "model_id": "glm-4-long",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 14,
                        "input_price": 30,
                        "output_price": 60
                    },
                    {
                        "name": "glm-4v",
                        "model_id": "glm-4v",
                        "max_tokens": 4096,
                        "temperature": 0.7,
                        "priority": 12,
                        "input_price": 100,
                        "output_price": 100
                    },
                    {
                        "name": "glm-3-turbo",
                        "model_id": "glm-3-turbo",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 6,
                        "input_price": 1,
                        "output_price": 1
                    },
                    {
                        "name": "embedding-2",
                        "model_id": "embedding-2",
                        "max_tokens": 2048,
                        "temperature": 0.0,
                        "priority": 30,
                        "input_price": 0.1,
                        "output_price": 0
                    },
                ]
            },
            
            "openai": {
                "enabled": False,  # 需要单独配置
                "api_key": "${OPENAI_API_KEY}",
                "base_url": "https://api.openai.com/v1",
                "timeout": 120,
                "models": [
                    {
                        "name": "gpt-4o",
                        "model_id": "gpt-4o",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 50,
                        "input_price": 15,
                        "output_price": 60
                    },
                    {
                        "name": "gpt-4o-mini",
                        "model_id": "gpt-4o-mini",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 30,
                        "input_price": 0.6,
                        "output_price": 2.4
                    },
                    {
                        "name": "gpt-4-turbo",
                        "model_id": "gpt-4-turbo",
                        "max_tokens": 128000,
                        "temperature": 0.7,
                        "priority": 40,
                        "input_price": 30,
                        "output_price": 90
                    },
                ]
            },
            
            "anthropic": {
                "enabled": False,  # 需要单独配置
                "api_key": "${ANTHROPIC_API_KEY}",
                "base_url": "https://api.anthropic.com/v1",
                "timeout": 120,
                "models": [
                    {
                        "name": "claude-3-5-sonnet",
                        "model_id": "claude-3-5-sonnet-20241022",
                        "max_tokens": 200000,
                        "temperature": 0.7,
                        "priority": 50,
                        "input_price": 11,
                        "output_price": 55
                    },
                    {
                        "name": "claude-3-opus",
                        "model_id": "claude-3-opus-20240229",
                        "max_tokens": 200000,
                        "temperature": 0.7,
                        "priority": 60,
                        "input_price": 45,
                        "output_price": 225
                    },
                ]
            },
            
            "gemini": {
                "enabled": False,  # 需要单独配置
                "api_key": "${GEMINI_API_KEY}",
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "timeout": 120,
                "models": [
                    {
                        "name": "gemini-1.5-pro",
                        "model_id": "gemini-1.5-pro",
                        "max_tokens": 2000000,
                        "temperature": 0.7,
                        "priority": 40,
                        "input_price": 3.5,
                        "output_price": 10.5
                    },
                    {
                        "name": "gemini-1.5-flash",
                        "model_id": "gemini-1.5-flash",
                        "max_tokens": 1000000,
                        "temperature": 0.7,
                        "priority": 20,
                        "input_price": 0.35,
                        "output_price": 1.05
                    },
                ]
            },
        },
        
        # 路由配置
        "router": {
            "strategy": "priority",  # priority, round_robin, weighted, failover
            "failover_enabled": True,
            "max_consecutive_failures": 3,
            "health_check_interval": 60
        },
        
        # 预算配置
        "budget": {
            "daily_limit": 0,  # 0 表示不限制
            "monthly_limit": 0,
            "alert_threshold": 0.8  # 达到80%时告警
        }
    }
    
    def __init__(self, config_dict: Optional[Dict] = None):
        self._config = config_dict or self.DEFAULT_CONFIG.copy()
        self.providers: Dict[str, Dict] = self._config.get("providers", {})
        self.coding_providers: Dict[str, Dict] = {}
        self.default_model: str = self._config.get("default_model", "qwen-plus")
        self.router_config: Dict = self._config.get("router", {})
        self.budget_config: Dict = self._config.get("budget", {})
        self.tier_config: Dict = self._config.get("tier1_cheap", {})
    
    def get_provider(self, name: str) -> Optional[Dict]:
        """获取提供商配置"""
        return self.providers.get(name)
    
    def get_model(self, provider: str, model_name: str) -> Optional[Dict]:
        """获取模型配置"""
        provider_config = self.get_provider(provider)
        if not provider_config:
            return None
        
        models = provider_config.get("models", [])
        for model in models:
            if model.get("name") == model_name or model.get("model_id") == model_name:
                return model
        return None
    
    def get_all_models(self) -> List[Dict]:
        """获取所有模型配置"""
        all_models = []
        for provider_name, provider_config in self.providers.items():
            if not provider_config.get("enabled", True):
                continue
            
            for model in provider_config.get("models", []):
                if model.get("enabled", True):
                    model["provider"] = provider_name
                    all_models.append(model)
        
        return all_models
    
    def get_models_by_priority(self, min_priority: int = 0, max_priority: int = 100) -> List[Dict]:
        """按优先级获取模型"""
        models = self.get_all_models()
        return [
            m for m in models
            if min_priority <= m.get("priority", 100) <= max_priority
        ]
    
    def get_pricing(self, provider: str, model_id: str) -> Dict:
        """获取模型定价"""
        return MODEL_PRICING.get(provider, {}).get(model_id, {"input": 0, "output": 0})
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return self._config
    
    @classmethod
    def from_file(cls, filepath: str) -> "Config":
        """从文件加载配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        return cls(config_dict)
    
    def save(self, filepath: str):
        """保存配置到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config(config_dict: Optional[Dict] = None) -> Config:
    """初始化配置"""
    global _config
    _config = Config(config_dict)
    return _config


def reset_config():
    """重置配置"""
    global _config
    _config = None
