from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QCheckBox, QGroupBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from artalekey.core.window_detector import window_monitor
from artalekey.core.logger import performance_logger

class SimpleTargetSelector(QGroupBox):
    """简化的目标应用选择器 - 原生外观，支持默认应用"""
    
    # 信号
    window_filter_enabled = pyqtSignal(bool)  # 窗口过滤启用状态变化
    
    def __init__(self, parent=None):
        super().__init__("窗口过滤", parent)
        
        # 默认目标应用 - 可以直接修改这里
        self.default_target_app = "MapleStory Worlds"
        
        self.init_ui()
        self.connect_signals()
        
        # 启动窗口监控器
        if not window_monitor.isRunning():
            window_monitor.start()
        
        # 排除当前应用
        window_monitor.add_to_excluded_apps('python')
        window_monitor.add_to_excluded_apps('artalekey')
        
    def init_ui(self):
        """初始化简化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 启用开关
        self.enable_check = QCheckBox("启用窗口过滤（只在指定应用中生效）")
        layout.addWidget(self.enable_check)
        
        # 目标应用设置
        target_layout = QHBoxLayout()
        target_label = QLabel("目标应用:")
        
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.addItems([
            self.default_target_app,
            "Chrome",
            "Safari", 
            "Firefox",
            "Visual Studio Code",
            "Xcode",
            "Finder"
        ])
        self.target_combo.setCurrentText(self.default_target_app)
        
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_combo, 1)
        
        layout.addLayout(target_layout)
        
        # 快速设置按钮
        quick_layout = QHBoxLayout()
        self.set_default_btn = QPushButton("使用默认应用")
        self.set_current_btn = QPushButton("设为当前应用")
        
        quick_layout.addWidget(self.set_default_btn)
        quick_layout.addWidget(self.set_current_btn)
        quick_layout.addStretch()
        
        layout.addLayout(quick_layout)
        
        # 状态显示
        self.status_label = QLabel("窗口过滤已禁用")
        self.status_label.setStyleSheet("color: gray; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # 初始状态
        self.update_enabled_state()
        
    def connect_signals(self):
        """连接信号"""
        self.enable_check.stateChanged.connect(self.on_filter_enabled_changed)
        self.target_combo.currentTextChanged.connect(self.on_target_changed)
        self.set_default_btn.clicked.connect(self.set_default_app)
        self.set_current_btn.clicked.connect(self.set_current_app)
        
        # 窗口监控信号
        window_monitor.target_window_activated.connect(self.on_target_window_activated)
        window_monitor.target_window_deactivated.connect(self.on_target_window_deactivated)
    
    def on_filter_enabled_changed(self, state):
        """窗口过滤启用状态改变"""
        enabled = state == Qt.CheckState.Checked.value
        self.update_enabled_state()
        
        if enabled:
            target_app = self.target_combo.currentText().strip()
            if target_app:
                window_monitor.set_target_processes([target_app])
                self.status_label.setText(f"窗口过滤已启用 - 目标应用: {target_app}")
                self.status_label.setStyleSheet("color: green; font-size: 12px;")
            else:
                self.status_label.setText("窗口过滤已启用 - 请设置目标应用")
                self.status_label.setStyleSheet("color: orange; font-size: 12px;")
        else:
            self.status_label.setText("窗口过滤已禁用")
            self.status_label.setStyleSheet("color: gray; font-size: 12px;")
        
        # 发送信号
        self.window_filter_enabled.emit(enabled)
    
    def on_target_changed(self, target_app):
        """目标应用改变"""
        if self.enable_check.isChecked() and target_app.strip():
            window_monitor.set_target_processes([target_app.strip()])
            self.status_label.setText(f"窗口过滤已启用 - 目标应用: {target_app}")
            self.status_label.setStyleSheet("color: green; font-size: 12px;")
    
    def set_default_app(self):
        """设置默认应用"""
        self.target_combo.setCurrentText(self.default_target_app)
        performance_logger.info(f"Set target app to default: {self.default_target_app}")
    
    def set_current_app(self):
        """设置当前检测到的应用"""
        current_window = window_monitor.get_current_window()
        if current_window and current_window.process_name.lower() not in ['python', 'artalekey']:
            self.target_combo.setCurrentText(current_window.process_name)
            performance_logger.info(f"Set target app to current: {current_window.process_name}")
        else:
            # 如果当前是python/artalekey，获取最近使用的应用
            recent_apps = window_monitor.get_recent_apps(1)
            if recent_apps:
                self.target_combo.setCurrentText(recent_apps[0])
                performance_logger.info(f"Set target app to recent: {recent_apps[0]}")
    
    def update_enabled_state(self):
        """更新启用状态"""
        enabled = self.enable_check.isChecked()
        self.target_combo.setEnabled(enabled)
        self.set_default_btn.setEnabled(enabled)
        self.set_current_btn.setEnabled(enabled)
    
    def on_target_window_activated(self):
        """目标窗口激活"""
        if self.enable_check.isChecked():
            target_app = self.target_combo.currentText()
            self.status_label.setText(f"✅ {target_app} 已激活 - 快捷键功能可用")
            self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 12px;")
    
    def on_target_window_deactivated(self):
        """目标窗口失活"""
        if self.enable_check.isChecked():
            target_app = self.target_combo.currentText()
            self.status_label.setText(f"⏸️ {target_app} 未激活 - 快捷键已暂停")
            self.status_label.setStyleSheet("color: orange; font-size: 12px;")
    
    def is_filter_enabled(self) -> bool:
        """检查窗口过滤是否启用"""
        return self.enable_check.isChecked()
    
    def set_filter_enabled(self, enabled: bool):
        """设置窗口过滤启用状态"""
        self.enable_check.setChecked(enabled)
    
    def get_target_app(self) -> str:
        """获取目标应用"""
        return self.target_combo.currentText().strip()
    
    def set_target_app(self, app_name: str):
        """设置目标应用"""
        self.target_combo.setCurrentText(app_name) 