import json
import os
from typing import Dict, Any, Optional
from PyQt6.QtCore import QSettings, QObject, pyqtSignal
from artalekey.core.logger import performance_logger

class ConfigManager(QObject):
    """简化的配置管理器 - 使用标准JSON结构"""
    
    config_changed = pyqtSignal(str, dict)  # 配置变更信号 (section, config_dict)
    
    def __init__(self):
        super().__init__()
        self.app_name = "ArtaleKey"
        self.organization = "ArtaleKey"
        
        # 使用QSettings进行跨平台配置存储
        self.settings = QSettings(self.organization, self.app_name)
        
        # 默认配置 - 标准JSON结构
        self.default_config = {
            'hotkeys': {
                'default': {
                    'trigger_key': 'w',
                    'hold_time': 100,
                    'interval': 88,
                    'enabled': False
                }
            },
            'ui': {
                'global_enabled': False,
                'window_position': None,
                'window_size': None,
                'window_geometry': None
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
                'save_screenshots': True,
                'capture_window_only': True,
                'screenshot_scale': 2.0
            },
            'llm': {
                'api_key': ''
            }
        }
        
        performance_logger.info("配置管理器初始化完成")
    
    def _get_section_raw(self, section: str) -> Optional[Dict]:
        """获取原始节配置，不使用默认值"""
        section_data = self.settings.value(section)
        if section_data is None:
            return None
        elif isinstance(section_data, str):
            try:
                return json.loads(section_data)
            except json.JSONDecodeError:
                return None
        return section_data
    
    def get(self, section: str, key: str = None) -> Any:
        """获取配置值 - 必须存在于配置中
        
        Args:
            section: 配置节名，如 'hotkeys', 'ui' 等
            key: 配置键名，如果为None则返回整个节
        """
        # 从QSettings获取整个节的配置
        section_data = self.settings.value(section)
        
        if section_data is None:
            # 如果没有保存的配置，使用默认配置
            section_data = self.default_config.get(section, {})
        elif isinstance(section_data, str):
            # 如果是JSON字符串，解析它
            try:
                section_data = json.loads(section_data)
            except json.JSONDecodeError:
                performance_logger.error(f"解析配置节 {section} 失败，使用默认配置")
                section_data = self.default_config.get(section, {})
        
        # 如果没有指定key，返回整个节
        if key is None:
            return section_data
        
        # 返回指定的键值，必须存在
        if isinstance(section_data, dict) and key in section_data:
            return section_data[key]
        
        # 如果配置中没有，从默认配置获取
        if section in self.default_config:
            default_section = self.default_config[section]
            if isinstance(default_section, dict) and key in default_section:
                return default_section[key]
        
        # 如果都没有，抛出异常
        raise KeyError(f"配置项 {section}.{key} 不存在")
    
    def set(self, section: str, key: str = None, value: Any = None, config_dict: Dict = None):
        """设置配置值
        
        Args:
            section: 配置节名
            key: 配置键名，如果为None则使用config_dict设置整个节
            value: 配置值
            config_dict: 配置字典，用于设置整个节
        """
        try:
            if config_dict is not None:
                # 设置整个节
                stored_value = json.dumps(config_dict, ensure_ascii=False)
                self.settings.setValue(section, stored_value)
                self.settings.sync()
                
                # 发送信号
                self.config_changed.emit(section, config_dict)
                performance_logger.debug(f"配置节已更新: {section}")
                
            elif key is not None and value is not None:
                # 设置单个键值
                # 先获取当前节的配置
                current_config = self._get_section_raw(section) or {}
                # 更新指定键
                current_config[key] = value
                # 保存整个节
                stored_value = json.dumps(current_config, ensure_ascii=False)
                self.settings.setValue(section, stored_value)
                self.settings.sync()
                
                # 发送信号
                self.config_changed.emit(section, current_config)
                performance_logger.debug(f"配置已更新: {section}.{key} = {value}")
            
        except Exception as e:
            performance_logger.error(f"设置配置失败 {section}.{key}: {e}")
    
    def get_hotkey_config(self, hotkey_id: str) -> Dict[str, Any]:
        """获取特定热键配置 - 必须存在完整配置"""
        hotkeys_config = self.get('hotkeys')
        if not isinstance(hotkeys_config, dict):
            hotkeys_config = {}
        
        if hotkey_id in hotkeys_config:
            return hotkeys_config[hotkey_id]
        
        # 如果不存在，返回默认配置
        if 'hotkeys' in self.default_config and hotkey_id in self.default_config['hotkeys']:
            return self.default_config['hotkeys'][hotkey_id].copy()
        
        # 如果默认配置也没有，抛出异常
        raise KeyError(f"热键配置 {hotkey_id} 不存在")
    
    def set_hotkey_config(self, hotkey_id: str, config: Dict[str, Any], auto_save: bool = True):
        """设置特定热键配置"""
        hotkeys_config = self.get('hotkeys')
        if not isinstance(hotkeys_config, dict):
            hotkeys_config = {}
        hotkeys_config[hotkey_id] = config
        self.set('hotkeys', config_dict=hotkeys_config)
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI配置"""
        return self.get('ui')
    
    def set_ui_config(self, config: Dict[str, Any], auto_save: bool = True):
        """设置UI配置"""
        self.set('ui', config_dict=config)
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.settings.clear()
        performance_logger.info("配置已重置为默认值")
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到文件"""
        try:
            config_data = {}
            for section in self.default_config.keys():
                config_data[section] = self.get(section)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            performance_logger.info(f"配置已导出到: {file_path}")
            return True
        except Exception as e:
            performance_logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for section, section_config in config_data.items():
                self.set(section, config_dict=section_config)
            
            performance_logger.info(f"配置已从文件导入: {file_path}")
            return True
        except Exception as e:
            performance_logger.error(f"导入配置失败: {e}")
            return False
    
    def save_window_geometry(self, geometry):
        """保存窗口几何信息"""
        if geometry:
            from PyQt6.QtCore import QByteArray
            if isinstance(geometry, QByteArray):
                geometry_str = geometry.toBase64().data().decode('utf-8')
            else:
                geometry_str = geometry
            
            self.set('ui', 'window_geometry', geometry_str)
    
    def restore_window_geometry(self, window):
        """恢复窗口几何信息"""
        geometry_data = self.get('ui', 'window_geometry')
        if geometry_data:
            try:
                from PyQt6.QtCore import QByteArray
                if isinstance(geometry_data, str):
                    geometry = QByteArray.fromBase64(geometry_data.encode('utf-8'))
                    window.restoreGeometry(geometry)
                else:
                    window.restoreGeometry(geometry_data)
                return True
            except Exception as e:
                performance_logger.error(f"恢复窗口几何信息失败: {e}")
                return False
        return False

# 全局配置管理器实例
config_manager = ConfigManager() 