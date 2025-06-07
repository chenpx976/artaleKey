from typing import Dict, List, Optional
from PyQt6.QtWidgets import QTabWidget

from artalekey.ui.tabs.base_tab import BaseTab, TabSignalManager
from artalekey.ui.tabs.quick_up_tab import QuickUpTab
from artalekey.ui.tabs.ocr_tab import OCRTab
from artalekey.ui.tabs.settings_tab import SettingsTab
from artalekey.ui.tabs.logs_tab import LogsTab


class TabFactory:
    """标签页工厂 - 负责创建和管理所有标签页"""
    
    TAB_CONFIGS = [
        {"name": "quick_up", "title": "快速向上", "class": QuickUpTab},
        {"name": "ocr", "title": "OCR识别", "class": OCRTab},
        {"name": "logs", "title": "日志", "class": LogsTab},
        {"name": "settings", "title": "设置", "class": SettingsTab},
    ]
    
    @classmethod
    def create_all_tabs(cls, parent=None) -> Dict[str, BaseTab]:
        """创建所有标签页"""
        tabs = {}
        for config in cls.TAB_CONFIGS:
            tab_class = config["class"]
            tab = tab_class(parent)
            tabs[config["name"]] = tab
        return tabs
    
    @classmethod
    def create_tab(cls, tab_name: str, parent=None) -> Optional[BaseTab]:
        """创建指定的标签页"""
        for config in cls.TAB_CONFIGS:
            if config["name"] == tab_name:
                tab_class = config["class"]
                return tab_class(parent)
        return None
    
    @classmethod
    def get_tab_title(cls, tab_name: str) -> str:
        """获取标签页标题"""
        for config in cls.TAB_CONFIGS:
            if config["name"] == tab_name:
                return config["title"]
        return tab_name
    
    @classmethod
    def get_all_tab_names(cls) -> List[str]:
        """获取所有标签页名称"""
        return [config["name"] for config in cls.TAB_CONFIGS]


class TabManager:
    """标签页管理器 - 统一管理标签页的生命周期和信号"""
    
    def __init__(self, tab_widget: QTabWidget, parent=None):
        self.tab_widget = tab_widget
        self.tabs: Dict[str, BaseTab] = {}
        self.signal_manager = TabSignalManager(parent)
        
    def initialize_tabs(self, parent=None):
        """初始化所有标签页"""
        # 创建所有标签页
        self.tabs = TabFactory.create_all_tabs(parent)
        
        # 添加到标签页组件
        for tab_name, tab in self.tabs.items():
            title = TabFactory.get_tab_title(tab_name)
            self.tab_widget.addTab(tab, title)
            
            # 注册到信号管理器
            self.signal_manager.register_tab(tab)
    
    def get_tab(self, tab_name: str) -> Optional[BaseTab]:
        """获取指定标签页"""
        return self.tabs.get(tab_name)
    
    def get_all_tabs(self) -> Dict[str, BaseTab]:
        """获取所有标签页"""
        return self.tabs.copy()
    
    def refresh_all_tabs(self):
        """刷新所有标签页数据"""
        for tab in self.tabs.values():
            tab.refresh_data()
    
    def cleanup_all_tabs(self):
        """清理所有标签页"""
        for tab in self.tabs.values():
            try:
                # 从信号管理器注销
                self.signal_manager.unregister_tab(tab)
                # 清理标签页资源
                tab.cleanup()
            except Exception as e:
                print(f"清理标签页 {tab.get_tab_name()} 时发生错误: {e}")
        
        self.tabs.clear()
    
    def get_signal_manager(self) -> TabSignalManager:
        """获取信号管理器"""
        return self.signal_manager


# 导出主要类和函数
__all__ = [
    'BaseTab',
    'TabSignalManager', 
    'QuickUpTab',
    'OCRTab',
    'LogsTab',
    'SettingsTab',
    'TabFactory',
    'TabManager'
] 