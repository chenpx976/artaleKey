from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.ui.components import HotkeyCard


class QuickUpTab(BaseTab):
    """快速向上功能标签页"""
    
    # 特定信号
    global_switch_changed = pyqtSignal(bool)  # 全局开关变更信号
    hotkey_config_changed = pyqtSignal(str, dict)  # 热键配置变更信号
    
    def __init__(self, parent=None):
        self._hotkey_card = None
        self._global_switch = None
        self._status_label = None
        super().__init__("quick_up", parent)
        
    def init_ui(self):
        """初始化UI"""
        # 热键配置组
        hotkey_group = QGroupBox("快速向上热键配置")
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        self._hotkey_card = HotkeyCard("default")
        self._hotkey_card.config_changed.connect(self._on_hotkey_config_changed)
        hotkey_layout.addWidget(self._hotkey_card)
        
        self.main_layout.addWidget(hotkey_group)
        
        # 功能控制组
        control_group = QGroupBox("功能控制")
        control_layout = QVBoxLayout(control_group)
        
        self._global_switch = QCheckBox("启用快速向上功能")
        self._global_switch.stateChanged.connect(self._on_global_switch_changed)
        control_layout.addWidget(self._global_switch)
        
        # 状态指示器
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet(
            "color: blue; font-weight: bold; padding: 8px; "
            "border: 1px solid lightgray; border-radius: 4px;"
        )
        control_layout.addWidget(self._status_label)
        
        self.main_layout.addWidget(control_group)
        
        # 添加弹性空间
        self.main_layout.addStretch()
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        config = {
            'global_enabled': self._global_switch.isChecked() if self._global_switch else False,
            'hotkey_config': self._hotkey_card.get_config() if self._hotkey_card else {}
        }
        return config
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        if self._global_switch:
            self._global_switch.setChecked(config.get('global_enabled', False))
        
        if self._hotkey_card and 'hotkey_config' in config:
            self._hotkey_card.set_config(config['hotkey_config'])
        
        # 更新状态显示
        self._update_status()
    
    def is_enabled(self) -> bool:
        """检查功能是否启用"""
        return self._global_switch.isChecked() if self._global_switch else False
    
    def set_simulation_status(self, is_running: bool):
        """设置模拟状态"""
        if is_running:
            self._status_label.setText("正在执行快速向上...")
            self._status_label.setStyleSheet(
                "color: orange; font-weight: bold; padding: 8px; "
                "border: 1px solid lightgray; border-radius: 4px;"
            )
        else:
            self._update_status()
    
    def _update_status(self):
        """更新状态显示"""
        if self._global_switch and self._global_switch.isChecked():
            self._status_label.setText("快速向上功能已启用")
            self._status_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 8px; "
                "border: 1px solid lightgray; border-radius: 4px;"
            )
        else:
            self._status_label.setText("快速向上功能已禁用")
            self._status_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 8px; "
                "border: 1px solid lightgray; border-radius: 4px;"
            )
    
    def _on_global_switch_changed(self, state):
        """全局开关状态变更处理"""
        enabled = state == Qt.CheckState.Checked.value
        self._update_status()
        
        # 发射信号
        self.global_switch_changed.emit(enabled)
        self.emit_config_changed()
        self.emit_status_changed(f"快速向上功能{'已启用' if enabled else '已禁用'}")
    
    def _on_hotkey_config_changed(self, hotkey_id: str, config: dict):
        """热键配置变更处理"""
        self.hotkey_config_changed.emit(hotkey_id, config)
        self.emit_config_changed()
        self.emit_status_changed(f"热键配置已更新: {hotkey_id}")
    
    def get_hotkey_config(self) -> Dict[str, Any]:
        """获取热键配置"""
        return self._hotkey_card.get_config() if self._hotkey_card else {}
    
    def set_hotkey_config(self, config: Dict[str, Any]):
        """设置热键配置"""
        if self._hotkey_card:
            self._hotkey_card.set_config(config) 