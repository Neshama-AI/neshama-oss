# Soul层 - 配置加载器
"""
Soul配置加载器：管理Soul配置的加载、验证和保存

功能：
- YAML/JSON配置加载
- 配置验证
- 配置合并与覆盖
- 配置保存
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import yaml
import json
import os


@dataclass
class ModuleConfig:
    """模块配置"""
    enabled: bool = True
    path: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SoulLoaderConfig:
    """加载器配置"""
    config_dir: str = "./Neshama/soul"
    default_config_name: str = "soul.yaml"
    
    # 加载选项
    validate_on_load: bool = True
    merge_with_defaults: bool = True
    allow_missing_modules: bool = True
    
    # 保存选项
    auto_save: bool = False
    save_dir: str = "./Neshama/soul"


class SoulLoader:
    """Soul配置加载器"""
    
    def __init__(self, config: SoulLoaderConfig = None):
        self.config = config or SoulLoaderConfig()
        self.loaded_config: Dict[str, Any] = {}
        self.module_configs: Dict[str, Dict] = {}
        self.config_history: List[Dict] = []
    
    def load(
        self,
        config_path: str = None,
        config_data: Dict = None
    ) -> Dict[str, Any]:
        """加载配置"""
        if config_path:
            config_data = self._load_from_file(config_path)
        elif config_data is None:
            # 加载默认配置
            default_path = os.path.join(
                self.config.config_dir,
                self.config.default_config_name
            )
            if os.path.exists(default_path):
                config_data = self._load_from_file(default_path)
        
        if not config_data:
            return self._get_default_config()
        
        # 验证
        if self.config.validate_on_load:
            config_data = self._validate_config(config_data)
        
        # 合并默认值
        if self.config.merge_with_defaults:
            config_data = self._merge_with_defaults(config_data)
        
        self.loaded_config = config_data
        self._record_load(config_data)
        
        return config_data
    
    def _load_from_file(self, path: str) -> Dict:
        """从文件加载"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.endswith('.json'):
                return json.load(f)
            else:
                return yaml.safe_load(f) or {}
    
    def _validate_config(self, config: Dict) -> Dict:
        """验证配置"""
        errors = []
        warnings = []
        
        # 检查必需字段
        required_fields = ["name", "version"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # 检查版本格式
        if "version" in config:
            if not self._is_valid_version(config["version"]):
                warnings.append(f"Version format may be invalid: {config['version']}")
        
        # 检查模块配置
        if "modules" in config:
            for module_name, module_config in config["modules"].items():
                if isinstance(module_config, dict):
                    if "enabled" not in module_config:
                        warnings.append(f"Module '{module_name}' missing 'enabled' field")
        
        # 检查数值范围
        if "characteristics" in config:
            for char_name, char_config in config["characteristics"].items():
                if isinstance(char_config, dict) and "level" in char_config:
                    level = char_config["level"]
                    if not 0 <= level <= 1:
                        errors.append(f"Characteristic '{char_name}' level must be 0-1, got {level}")
        
        if errors:
            raise ValueError(f"Config validation errors: {', '.join(errors)}")
        
        if warnings:
            print(f"Config warnings: {', '.join(warnings)}")
        
        return config
    
    def _is_valid_version(self, version: str) -> bool:
        """验证版本格式"""
        parts = version.split('.')
        if len(parts) < 2:
            return False
        return all(part.isdigit() for part in parts)
    
    def _merge_with_defaults(self, config: Dict) -> Dict:
        """与默认配置合并"""
        defaults = self._get_default_config()
        
        # 深度合并
        merged = defaults.copy()
        
        for key, value in config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _merge_dicts(self, base: Dict, override: Dict) -> Dict:
        """合并两个字典"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "name": "Neshama Soul",
            "version": "2.0.0",
            "modules": {
                "emotions": {
                    "enabled": True,
                    "path": "./modules/emotions.yaml"
                },
                "drives": {
                    "enabled": True,
                    "path": "./modules/drives.yaml"
                },
                "learning": {
                    "enabled": True,
                    "path": "./modules/learning.yaml"
                },
                "creativity": {
                    "enabled": True,
                    "path": "./modules/creativity.yaml"
                },
                "boundaries": {
                    "enabled": True,
                    "path": "./modules/boundaries.yaml"
                }
            },
            "characteristics": {
                "willpower": {"level": 0.7},
                "execution": {"level": 0.8},
                "empathy": {"level": 0.75},
                "humor": {"level": 0.5},
                "habits": {"level": 0.6}
            },
            "evolution": {
                "enabled": True,
                "max_snapshot_count": 100,
                "snapshot_interval_minutes": 60,
                "stability_threshold": 0.7
            },
            "entertainment": {
                "enabled": True,
                "user_controllable": True,
                "max_daily_activities": 5,
                "default_token_budget": 50
            }
        }
    
    def _record_load(self, config: Dict):
        """记录加载历史"""
        self.config_history.append({
            "timestamp": datetime.now().isoformat(),
            "name": config.get("name"),
            "version": config.get("version")
        })
    
    def load_module(self, module_name: str, module_path: str = None) -> Dict:
        """加载模块配置"""
        if module_path is None:
            # 使用默认路径
            module_path = os.path.join(
                self.config.config_dir,
                "modules",
                f"{module_name}.yaml"
            )
        
        if not os.path.exists(module_path):
            if self.config.allow_missing_modules:
                return {}
            raise FileNotFoundError(f"Module file not found: {module_path}")
        
        with open(module_path, 'r', encoding='utf-8') as f:
            module_config = yaml.safe_load(f) or {}
        
        self.module_configs[module_name] = module_config
        return module_config
    
    def save(self, config: Dict = None, path: str = None):
        """保存配置"""
        if config is None:
            config = self.loaded_config
        
        if path is None:
            path = os.path.join(
                self.config.save_dir,
                self.config.default_config_name
            )
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            if path.endswith('.json'):
                json.dump(config, f, indent=2, ensure_ascii=False)
            else:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    def get_module_config(self, module_name: str) -> Optional[Dict]:
        """获取模块配置"""
        return self.module_configs.get(module_name)
    
    def update_config(self, updates: Dict):
        """更新配置"""
        self.loaded_config = self._merge_dicts(self.loaded_config, updates)
        
        if self.config.auto_save:
            self.save(self.loaded_config)
    
    def get_load_history(self) -> List[Dict]:
        """获取加载历史"""
        return self.config_history
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.loaded_config = self._get_default_config()
    
    def export_config(self, format: str = "yaml") -> str:
        """导出配置"""
        if format == "json":
            return json.dumps(self.loaded_config, indent=2, ensure_ascii=False)
        else:
            return yaml.dump(self.loaded_config, allow_unicode=True, default_flow_style=False)


class SoulConfigBuilder:
    """Soul配置构建器"""
    
    def __init__(self):
        self.config = {}
    
    def set_name(self, name: str) -> "SoulConfigBuilder":
        """设置名称"""
        self.config["name"] = name
        return self
    
    def set_version(self, version: str) -> "SoulConfigBuilder":
        """设置版本"""
        self.config["version"] = version
        return self
    
    def enable_module(self, module_name: str, settings: Dict = None) -> "SoulConfigBuilder":
        """启用模块"""
        if "modules" not in self.config:
            self.config["modules"] = {}
        self.config["modules"][module_name] = {
            "enabled": True,
            **(settings or {})
        }
        return self
    
    def disable_module(self, module_name: str) -> "SoulConfigBuilder":
        """禁用模块"""
        if "modules" not in self.config:
            self.config["modules"] = {}
        self.config["modules"][module_name] = {"enabled": False}
        return self
    
    def set_characteristic(self, name: str, level: float, **kwargs) -> "SoulConfigBuilder":
        """设置特征"""
        if "characteristics" not in self.config:
            self.config["characteristics"] = {}
        self.config["characteristics"][name] = {"level": level, **kwargs}
        return self
    
    def set_evolution_config(self, **kwargs) -> "SoulConfigBuilder":
        """设置演化配置"""
        self.config["evolution"] = kwargs
        return self
    
    def set_entertainment_config(self, **kwargs) -> "SoulConfigBuilder":
        """设置娱乐配置"""
        self.config["entertainment"] = kwargs
        return self
    
    def build(self) -> Dict:
        """构建配置"""
        return self.config.copy()


# 全局加载器实例
soul_loader = SoulLoader()


# 便捷函数
def load_soul_config(config_path: str = None) -> Dict:
    """加载配置的便捷函数"""
    return soul_loader.load(config_path)


def create_soul_config() -> SoulConfigBuilder:
    """创建配置构建器"""
    return SoulConfigBuilder()


def save_soul_config(config: Dict, path: str = None):
    """保存配置的便捷函数"""
    soul_loader.save(config, path)
