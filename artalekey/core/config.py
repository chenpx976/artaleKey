import json
import os
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings, QObject, pyqtSignal
from artalekey.core.logger import performance_logger

class ConfigManager(QObject):
    """优化的配置管理器 - 支持自动保存和性能监控"""
    
    config_changed = pyqtSignal(str, dict)  # 配置变更信号
    
    def __init__(self):
        super().__init__()
        self.app_name = "ArtaleKey"
        self.organization = "ArtaleKey"
        
        # 使用QSettings进行跨平台配置存储
        self.settings = QSettings(self.organization, self.app_name)
        
        # 默认配置
        self.default_config = {
            'hotkeys': {
                'default': {
                    'trigger_key': 'w',
                    'hold_time': 500,
                    'interval': 40,
                    'enabled': False
                }
            },
            'ui': {
                'theme': 'dark',
                'window_geometry': None,
                'global_enabled': False
            },
            'performance': {
                'enable_logging': True,
                'log_level': 'INFO'
            },
            'window_filter': {
                'enabled': False,
                'target_apps': []
            }
        }
        
        # 配置缓存，减少文件I/O
        self._config_cache = {}
        self._load_config()
        
    @performance_logger.measure_time("load_config")
    def _load_config(self):
        """加载配置"""
        try:
            # 尝试从QSettings加载
            for key in self.default_config:
                value = self.settings.value(key, self.default_config[key])
                if isinstance(value, str) and value.startswith('{'):
                    # 处理JSON字符串
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        value = self.default_config[key]
                self._config_cache[key] = value
                
            performance_logger.info("Configuration loaded successfully")
            
        except Exception as e:
            performance_logger.error(f"Failed to load config: {e}")
            self._config_cache = self.default_config.copy()
    
    @performance_logger.measure_time("save_config")
    def save_config(self):
        """保存配置"""
        try:
            for key, value in self._config_cache.items():
                if isinstance(value, (dict, list)):
                    # 将复杂对象序列化为JSON
                    self.settings.setValue(key, json.dumps(value))
                else:
                    self.settings.setValue(key, value)
            
            self.settings.sync()
            performance_logger.info("Configuration saved successfully")
            
        except Exception as e:
            performance_logger.error(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        current = self._config_cache
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set(self, key: str, value: Any, auto_save: bool = True):
        """设置配置值"""
        keys = key.split('.')
        current = self._config_cache
        
        # 导航到父级字典
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # 设置值
        old_value = current.get(keys[-1])
        current[keys[-1]] = value
        
        # 发送变更信号
        if old_value != value:
            self.config_changed.emit(key, value)
        
        # 自动保存
        if auto_save:
            self.save_config()
    
    def get_hotkey_config(self, hotkey_id: str) -> Dict[str, Any]:
        """获取特定热键配置"""
        return self.get(f'hotkeys.{hotkey_id}', self.default_config['hotkeys']['default'].copy())
    
    def set_hotkey_config(self, hotkey_id: str, config: Dict[str, Any], auto_save: bool = True):
        """设置特定热键配置"""
        self.set(f'hotkeys.{hotkey_id}', config, auto_save=auto_save)
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置"""
        return self.get('ui', self.default_config['ui'].copy())
    
    def set_ui_config(self, config: Dict[str, Any], auto_save: bool = True):
        """设置UI配置"""
        self.set('ui', config, auto_save=auto_save)
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self._config_cache = self.default_config.copy()
        self.save_config()
        performance_logger.info("Configuration reset to defaults")
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._config_cache, f, indent=2, ensure_ascii=False)
            performance_logger.info(f"Configuration exported to {file_path}")
            return True
        except Exception as e:
            performance_logger.error(f"Failed to export config: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 验证并合并配置
            self._merge_config(imported_config)
            self.save_config()
            performance_logger.info(f"Configuration imported from {file_path}")
            return True
        except Exception as e:
            performance_logger.error(f"Failed to import config: {e}")
            return False
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """合并新配置，保持结构完整性"""
        def merge_dict(base: dict, new: dict):
            for key, value in new.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(self._config_cache, new_config)

# 全局配置管理器实例
config_manager = ConfigManager() 