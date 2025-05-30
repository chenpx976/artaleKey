from typing import Dict, Any

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.ui.qt_chart_widget import QtVisualizationWidget


class VisualizationTab(BaseTab):
    """可视化功能标签页"""
    
    def __init__(self, parent=None):
        self._visualization_widget = None
        super().__init__("visualization", parent)
        
    def init_ui(self):
        """初始化UI"""
        # 可视化组件
        self._visualization_widget = QtVisualizationWidget()
        self.main_layout.addWidget(self._visualization_widget)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {}  # 可视化标签页暂无配置
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        pass  # 可视化标签页暂无配置
    
    def refresh_data(self):
        """刷新数据"""
        if self._visualization_widget:
            self._visualization_widget.refresh_data()
            self.emit_status_changed("可视化数据已刷新")
    
    def get_visualization_widget(self):
        """获取可视化组件"""
        return self._visualization_widget 