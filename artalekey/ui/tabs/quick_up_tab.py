from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Any

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.ui.components import HotkeyCard
from artalekey.core.config import config_manager


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
        # 功能控制组（移到顶部）
        control_group = QGroupBox("快速向上功能控制")
        control_layout = QVBoxLayout(control_group)
        
        self._global_switch = QCheckBox("启用快速向上功能")
        self._global_switch.stateChanged.connect(self._on_global_switch_changed)
        control_layout.addWidget(self._global_switch)
        
        # 状态指示器
        self._status_label = QLabel("功能已禁用")
        self._status_label.setStyleSheet(
            "color: red; font-weight: bold; padding: 8px; "
            "border: 1px solid lightgray; border-radius: 4px;"
        )
        control_layout.addWidget(self._status_label)
        
        self.main_layout.addWidget(control_group)
        
        # 热键配置组（移到下面）
        hotkey_group = QGroupBox("热键配置")
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        self._hotkey_card = HotkeyCard("default", enable_internal_switch=False)  # 禁用内部开关
        self._hotkey_card.config_changed.connect(self._on_hotkey_config_changed)
        hotkey_layout.addWidget(self._hotkey_card)
        
        self.main_layout.addWidget(hotkey_group)
        
        # 添加弹性空间
        self.main_layout.addStretch()
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        try:
            # 加载全局开关状态
            global_enabled = config_manager.get('ui', 'global_enabled')
            self._global_switch.setChecked(global_enabled)
            
            # 加载热键配置
            hotkey_config = config_manager.get_hotkey_config("default")
            if self._hotkey_card:
                # 确保enabled状态与全局开关一致
                hotkey_config['enabled'] = global_enabled
                self._hotkey_card.set_config(hotkey_config)
            
            # 更新状态显示
            self._update_status()
            
        except Exception as e:
            from artalekey.core.logger import performance_logger
            performance_logger.error(f"加载快速向上配置失败: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        hotkey_config = self._hotkey_card.get_config() if self._hotkey_card else {}
        # 强制设置enabled为全局开关状态
        hotkey_config['enabled'] = self._global_switch.isChecked() if self._global_switch else False
        
        config = {
            'global_enabled': self._global_switch.isChecked() if self._global_switch else False,
            'hotkey_config': hotkey_config
        }
        return config
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        global_enabled = config.get('global_enabled', False)
        if self._global_switch:
            self._global_switch.setChecked(global_enabled)
        
        if self._hotkey_card and 'hotkey_config' in config:
            hotkey_config = config['hotkey_config'].copy()
            # 强制设置enabled为全局开关状态
            hotkey_config['enabled'] = global_enabled
            self._hotkey_card.set_config(hotkey_config)
        
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
                "border: 1px solid orange; border-radius: 4px;"
            )
        else:
            self._update_status()
    
    def _update_status(self):
        """更新状态显示"""
        if self._global_switch and self._global_switch.isChecked():
            hotkey_config = self._hotkey_card.get_config() if self._hotkey_card else {}
            trigger_key = hotkey_config.get('trigger_key', 'w').upper()
            self._status_label.setText(f"功能已启用 - 按住 {trigger_key}+↑ 键触发")
            self._status_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 8px; "
                "border: 1px solid green; border-radius: 4px;"
            )
            # 启用热键配置
            if self._hotkey_card:
                self._hotkey_card.setEnabled(True)
        else:
            self._status_label.setText("功能已禁用")
            self._status_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 8px; "
                "border: 1px solid lightgray; border-radius: 4px;"
            )
            # 禁用热键配置
            if self._hotkey_card:
                self._hotkey_card.setEnabled(False)
    
    def _on_global_switch_changed(self, state):
        """全局开关状态变更处理"""
        enabled = state == Qt.CheckState.Checked.value
        
        # 保存全局开关状态
        config_manager.set('ui', 'global_enabled', enabled)
        
        # 同步更新HotkeyCard的enabled状态
        if self._hotkey_card:
            current_config = self._hotkey_card.get_config()
            current_config['enabled'] = enabled
            self._hotkey_card.set_config(current_config)
            # 保存热键配置
            config_manager.set_hotkey_config("default", current_config)
        
        self._update_status()
        
        # 发射信号
        self.global_switch_changed.emit(enabled)
        self.emit_config_changed()
        self.emit_status_changed(f"快速向上功能{'已启用' if enabled else '已禁用'}")
    
    def _on_hotkey_config_changed(self, hotkey_id: str, config: dict):
        """热键配置变更处理"""
        # 确保enabled状态与全局开关一致
        config['enabled'] = self._global_switch.isChecked() if self._global_switch else False
        
        # 保存热键配置
        config_manager.set_hotkey_config(hotkey_id, config)
        
        # 更新状态显示（触发键可能变化了）
        self._update_status()
        
        self.hotkey_config_changed.emit(hotkey_id, config)
        self.emit_config_changed()
        self.emit_status_changed(f"热键配置已更新: {hotkey_id}")
    
    def get_hotkey_config(self) -> Dict[str, Any]:
        """获取热键配置"""
        return self._hotkey_card.get_config() if self._hotkey_card else {}
    
    def set_hotkey_config(self, config: Dict[str, Any]):
        """设置热键配置"""
        if self._hotkey_card:
            # 确保enabled状态与全局开关一致
            config = config.copy()
            config['enabled'] = self._global_switch.isChecked() if self._global_switch else False
            self._hotkey_card.set_config(config) 