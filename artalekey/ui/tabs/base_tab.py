from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QSizePolicy
from PyQt6.QtCore import pyqtSignal, QSize, Qt, QObject
from PyQt6.QtGui import QResizeEvent
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTabMeta(type(QWidget), type(ABC)):
    """元类用于多重继承兼容性"""
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
        
        # 创建滚动区域
        self._setup_scroll_area()
        
        # 初始化UI
        self.init_ui()
        
    def _setup_scroll_area(self):
        """设置滚动区域"""
        # 主容器布局
        container_layout = QVBoxLayout(self)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建内容容器 - 调整最小尺寸，让它更合理
        self.content_widget = QWidget()
        self.content_widget.setMinimumSize(QSize(580, 400))  # 减小最小尺寸
        # 确保内容容器能够根据子组件动态调整大小
        self.content_widget.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding
        )
        
        # 创建主布局（放在内容容器中）
        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(15)
        
        # 将内容容器设置为滚动区域的widget
        self.scroll_area.setWidget(self.content_widget)
        
        # 将滚动区域添加到主容器
        container_layout.addWidget(self.scroll_area)
        
        # 设置更细致隐蔽的滚动区域样式
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background-color: rgba(0, 0, 0, 0.05);
                width: 6px;
                border-radius: 3px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 3px;
                min-height: 15px;
                margin: 0px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 0, 0, 0.4);
            }
            QScrollBar::handle:vertical:pressed {
                background-color: rgba(0, 0, 0, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background-color: rgba(0, 0, 0, 0.05);
                height: 6px;
                border-radius: 3px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 3px;
                min-width: 15px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgba(0, 0, 0, 0.4);
            }
            QScrollBar::handle:horizontal:pressed {
                background-color: rgba(0, 0, 0, 0.6);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
    
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
    
    def set_content_minimum_size(self, width: int, height: int):
        """设置内容最小尺寸"""
        self.content_widget.setMinimumSize(QSize(width, height))
    
    def get_scroll_area(self) -> QScrollArea:
        """获取滚动区域对象"""
        return self.scroll_area
    
    def get_content_widget(self) -> QWidget:
        """获取内容容器对象"""
        return self.content_widget


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