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
                'enabled': True,
                'target_app': 'MapleStory Worlds'
            },
            'screenshot_ocr': {
                'enabled': True,
                'trigger_key': 'c',
                'target_window': 'MapleStory Worlds',
                'output_folder': 'ocr_data',
                'save_screenshots': False,
                'capture_window_only': True,  # 只截取目标窗口内容
                'screenshot_scale': 2.0       # 截图缩放倍数，2.0表示2x分辨率
            },
            'llm': {
                'api_key': ''  # OpenRouter API 密钥
            }
        }
        
        # 配置缓存，减少文件I/O
        self._config_cache = {}
        self._load_config()
        
    @performance_logger.measure_time("load_config")
    def _load_config(self):
        """加载配置"""
        try:
            # 先复制默认配置
            self._config_cache = self.default_config.copy()
            
            # 获取所有已保存的配置键
            all_keys = self.settings.allKeys()
            
            # 加载所有保存的配置项
            for key in all_keys:
                value = self.settings.value(key)
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    # 处理JSON字符串
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        # 如果解析失败，检查是否有默认值
                        if key in self.default_config:
                            value = self.default_config[key]
                        else:
                            continue
                
                # 设置到缓存中
                self._config_cache[key] = value
            
            # 确保所有默认配置键都存在
            for key in self.default_config:
                if key not in self._config_cache:
                    self._config_cache[key] = self.default_config[key]
                
            performance_logger.info("Configuration loaded successfully")
            performance_logger.debug(f"Loaded config keys: {list(self._config_cache.keys())}")
            
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
        
        # 发送变更信号（优化信号发送逻辑）
        if old_value != value:
            # 构建完整的配置路径和值
            signal_value = value if isinstance(value, dict) else {'value': value}
            self.config_changed.emit(key, signal_value)
            performance_logger.debug(f"配置已变更: {key} = {signal_value}")
        
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

    # UI配置相关便捷方法
    def load_all_ui_configs(self) -> Dict[str, Any]:
        """加载所有UI相关配置"""
        configs = {}
        
        # 加载快速向上配置
        hotkey_config = self.get_hotkey_config("default")
        ui_config = self.get_ui_config()
        configs['quick_up'] = {
            'global_enabled': ui_config.get('global_enabled', False),
            'hotkey_config': hotkey_config
        }
        
        # 加载OCR配置
        ocr_config = self.get('screenshot_ocr', self.default_config['screenshot_ocr'].copy())
        configs['ocr'] = ocr_config
        
        # 加载可视化配置
        configs['visualization'] = {}
        
        # 加载设置配置
        llm_config = self.get('llm', self.default_config['llm'].copy())
        window_filter_config = self.get('window_filter', self.default_config['window_filter'].copy())
        
        configs['settings'] = {
            'llm': llm_config,
            'window_filter': window_filter_config
        }
        
        # 加载UI配置
        configs['ui'] = ui_config
        
        return configs
    
    def save_all_ui_configs(self, configs: Dict[str, Any]):
        """保存所有UI相关配置"""
        # 保存快速向上配置
        if 'quick_up' in configs:
            quick_up_config = configs['quick_up']
            if 'hotkey_config' in quick_up_config:
                self.set_hotkey_config("default", quick_up_config['hotkey_config'], auto_save=False)
        
        # 保存OCR配置
        if 'ocr' in configs:
            self.set('screenshot_ocr', configs['ocr'], auto_save=False)
        
        # 保存设置配置
        if 'settings' in configs:
            settings_config = configs['settings']
            if 'llm' in settings_config:
                self.set('llm', settings_config['llm'], auto_save=False)
            if 'window_filter' in settings_config:
                self.set('window_filter', settings_config['window_filter'], auto_save=False)
        
        # 保存UI配置
        if 'ui' in configs:
            ui_config = configs['ui'].copy()
            # 如果有全局启用状态，从quick_up配置中获取
            if 'quick_up' in configs:
                ui_config['global_enabled'] = configs['quick_up'].get('global_enabled', False)
            self.set_ui_config(ui_config, auto_save=False)
        
        # 统一保存
        self.save_config()
    
    def get_tab_config(self, tab_name: str) -> Dict[str, Any]:
        """获取指定标签页的配置"""
        all_configs = self.load_all_ui_configs()
        default_configs = self._get_default_tab_configs()
        return all_configs.get(tab_name, default_configs.get(tab_name, {}))
    
    def save_tab_config(self, tab_name: str, config: Dict[str, Any]):
        """保存指定标签页的配置"""
        all_configs = self.load_all_ui_configs()
        all_configs[tab_name] = config
        self.save_all_ui_configs(all_configs)
    
    def save_window_geometry(self, geometry):
        """保存窗口几何信息"""
        ui_config = self.get_ui_config()
        if geometry:
            from PyQt6.QtCore import QByteArray
            if isinstance(geometry, QByteArray):
                ui_config['window_geometry'] = geometry.toBase64().data().decode('utf-8')
            else:
                ui_config['window_geometry'] = geometry
            self.set_ui_config(ui_config)
    
    def restore_window_geometry(self, window):
        """恢复窗口几何信息"""
        ui_config = self.get_ui_config()
        if ui_config.get('window_geometry'):
            try:
                from PyQt6.QtCore import QByteArray
                geometry_data = ui_config['window_geometry']
                if isinstance(geometry_data, str):
                    # 从base64字符串恢复QByteArray
                    geometry = QByteArray.fromBase64(geometry_data.encode('utf-8'))
                    window.restoreGeometry(geometry)
                else:
                    # 兼容旧格式
                    window.restoreGeometry(geometry_data)
                return True
            except Exception as e:
                performance_logger.error(f"恢复窗口几何信息失败: {e}")
                return False
        return False
    
    def _get_default_tab_configs(self) -> Dict[str, Any]:
        """获取默认标签页配置"""
        return {
            'quick_up': {
                'global_enabled': False,
                'hotkey_config': self.default_config['hotkeys']['default'].copy()
            },
            'ocr': self.default_config['screenshot_ocr'].copy(),
            'visualization': {},
            'settings': {
                'llm': self.default_config['llm'].copy(),
                'window_filter': self.default_config['window_filter'].copy()
            },
            'ui': self.default_config['ui'].copy()
        }

# 全局配置管理器实例
config_manager = ConfigManager() 