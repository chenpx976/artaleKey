from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTabMeta(type(QWidget), type(ABC)):
    """解决QWidget和ABC的元类冲突"""
    pass


class BaseTab(QWidget, ABC, metaclass=BaseTabMeta):
    """标签页基类 - 定义所有标签页的通用接口和行为"""
    
    # 通用信号
    config_changed = pyqtSignal(str, dict)  # 配置变更信号
    status_changed = pyqtSignal(str, str)   # 状态变更信号 (tab_name, status_message)
    
    def __init__(self, tab_name: str, parent=None):
        super().__init__(parent)
        self.tab_name = tab_name
        self._config = {}
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        
        # 初始化UI
        self.init_ui()
        
    @abstractmethod
    def init_ui(self):
        """初始化UI - 子类必须实现"""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置 - 子类必须实现"""
        pass
    
    @abstractmethod
    def set_config(self, config: Dict[str, Any]):
        """设置配置 - 子类必须实现"""
        pass
    
    def get_tab_name(self) -> str:
        """获取标签页名称"""
        return self.tab_name
    
    def emit_config_changed(self):
        """发射配置变更信号"""
        config = self.get_config()
        self.config_changed.emit(self.tab_name, config)
    
    def emit_status_changed(self, status_message: str):
        """发射状态变更信号"""
        self.status_changed.emit(self.tab_name, status_message)
    
    def refresh_data(self):
        """刷新数据 - 子类可选实现"""
        pass
    
    def cleanup(self):
        """清理资源 - 子类可选实现"""
        pass


class TabSignalManager(QObject):
    """标签页信号管理器 - 统一管理所有标签页的信号"""
    
    # 聚合信号
    tab_config_changed = pyqtSignal(str, dict)
    tab_status_changed = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._registered_tabs = []
    
    def register_tab(self, tab: BaseTab):
        """注册标签页"""
        if tab not in self._registered_tabs:
            self._registered_tabs.append(tab)
            # 连接标签页信号到管理器
            tab.config_changed.connect(self.tab_config_changed.emit)
            tab.status_changed.connect(self.tab_status_changed.emit)
    
    def unregister_tab(self, tab: BaseTab):
        """注销标签页"""
        if tab in self._registered_tabs:
            self._registered_tabs.remove(tab)
            # 断开信号连接
            tab.config_changed.disconnect(self.tab_config_changed.emit)
            tab.status_changed.disconnect(self.tab_status_changed.emit)
    
    def get_registered_tabs(self):
        """获取已注册的标签页列表"""
        return self._registered_tabs.copy() 