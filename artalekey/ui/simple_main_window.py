from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QResizeEvent

from .components import HotkeyCard
from .simple_target_selector import SimpleTargetSelector
from .simple_styles import get_adaptive_style, get_native_style
from ..core.hotkey_manager import KeySimulator, HotkeyListener
from ..core.config import config_manager
from ..core.logger import performance_logger
from ..core.window_detector import window_monitor

class SimpleMainWindow(QMainWindow):
    """简化的主窗口 - 原生外观，字体自适应"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtaleKey - 快捷键管理器")
        self.setMinimumSize(QSize(400, 300))
        
        # 初始化管理器
        self.key_simulator = KeySimulator()
        self.hotkey_listener = HotkeyListener(self)
        
        # 状态追踪
        self._is_simulation_running = False
        self._window_filter_enabled = False
        
        # 字体自适应
        self.update_adaptive_style()
        
        # 加载配置
        self.load_config()
        
        self.init_ui()
        self.connect_signals()
        self.hotkey_listener.start()
        
        # 记录启动性能
        performance_logger.log_memory_usage("after startup")
        
    def update_adaptive_style(self):
        """更新自适应样式"""
        width = self.width()
        height = self.height()
        style = get_adaptive_style(width, height)
        self.setStyleSheet(style)
        
    def resizeEvent(self, event: QResizeEvent):
        """窗口大小改变事件 - 自动调整字体"""
        super().resizeEvent(event)
        self.update_adaptive_style()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 热键配置组
        hotkey_group = QGroupBox("热键配置")
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        self.hotkey_card = HotkeyCard("default")
        hotkey_layout.addWidget(self.hotkey_card)
        
        layout.addWidget(hotkey_group)
        
        # 简化的目标应用选择器
        self.target_selector = SimpleTargetSelector()
        layout.addWidget(self.target_selector)
        
        # 全局控制组
        control_group = QGroupBox("功能控制")
        control_layout = QVBoxLayout(control_group)
        
        self.global_switch = QCheckBox("启用快速向上功能")
        control_layout.addWidget(self.global_switch)
        
        # 状态指示器
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: blue; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        control_layout.addWidget(self.status_label)
        
        layout.addWidget(control_group)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def load_config(self):
        """加载配置"""
        # 加载热键配置
        hotkey_config = config_manager.get_hotkey_config("default")
        
        # 加载UI配置
        ui_config = config_manager.get_ui_config()
        self._ui_config = ui_config
        
        # 恢复窗口几何尺寸
        if ui_config.get('window_geometry'):
            try:
                self.restoreGeometry(ui_config['window_geometry'])
            except Exception:
                pass  # 忽略几何恢复错误
    
    def save_config(self):
        """保存配置"""
        # 保存热键配置
        config_manager.set_hotkey_config("default", self.hotkey_card.get_config())
        
        # 保存UI配置
        ui_config = self._ui_config.copy()
        ui_config['global_enabled'] = self.global_switch.isChecked()
        ui_config['window_geometry'] = self.saveGeometry()
        config_manager.set_ui_config(ui_config)
        
        # 保存窗口过滤配置
        window_filter_config = {
            'enabled': self.target_selector.is_filter_enabled(),
            'target_app': self.target_selector.get_target_app()
        }
        config_manager.set('window_filter', window_filter_config)
        
    def connect_signals(self):
        """连接所有信号"""
        # 全局开关信号
        self.global_switch.stateChanged.connect(self.on_global_switch_changed)
        
        # 配置变更信号
        self.hotkey_card.config_changed.connect(self.on_config_changed)
        
        # 热键监听器信号
        self.hotkey_listener.key_combination_detected.connect(self.on_hotkey_detected)
        self.hotkey_listener.key_combination_released.connect(self.on_hotkey_released)
        
        # 模拟器信号
        self.key_simulator.simulation_started.connect(self.on_simulation_started)
        self.key_simulator.simulation_stopped.connect(self.on_simulation_stopped)
        
        # 目标应用选择器信号
        self.target_selector.window_filter_enabled.connect(self.on_window_filter_enabled)
        
        # 窗口监控信号
        window_monitor.target_window_activated.connect(self.on_target_window_activated)
        window_monitor.target_window_deactivated.connect(self.on_target_window_deactivated)
        
        # 应用保存的配置
        self.apply_saved_config()
        
    def apply_saved_config(self):
        """应用保存的配置"""
        # 应用热键配置
        hotkey_config = config_manager.get_hotkey_config("default")
        self.hotkey_card.set_config(hotkey_config)
        
        # 应用UI配置
        self.global_switch.setChecked(self._ui_config.get('global_enabled', False))
        
        # 应用窗口过滤配置
        window_filter_config = config_manager.get('window_filter', {})
        self.target_selector.set_filter_enabled(window_filter_config.get('enabled', False))
        target_app = window_filter_config.get('target_app', '')
        if target_app:
            self.target_selector.set_target_app(target_app)
        
        # 更新热键监听器和模拟器设置
        self.hotkey_listener.set_hold_time(hotkey_config['hold_time'])
        self.key_simulator.set_interval(hotkey_config['interval'])
        
    def on_config_changed(self, hotkey_id: str, config: dict):
        """配置变更处理"""
        if hotkey_id == "default":
            # 更新长按时间
            self.hotkey_listener.set_hold_time(config['hold_time'])
            # 更新模拟器间隔
            self.key_simulator.set_interval(config['interval'])
            
            # 更新状态显示
            self.status_label.setText(f"配置已更新 - 长按: {config['hold_time']}ms, 间隔: {config['interval']}ms")
            self.status_label.setStyleSheet("color: blue; font-weight: bold; padding: 8px; border: 1px solid lightblue; border-radius: 4px;")
            
            # 自动保存配置
            config_manager.set_hotkey_config(hotkey_id, config, auto_save=False)
            
            # 延迟保存
            if not hasattr(self, '_save_timer'):
                self._save_timer = QTimer()
                self._save_timer.setSingleShot(True)
                self._save_timer.timeout.connect(config_manager.save_config)
            self._save_timer.stop()
            self._save_timer.start(1000)
        
    def on_global_switch_changed(self, state):
        """全局开关状态改变"""
        if state:
            self.statusBar().showMessage("快速向上功能已启用")
            self.status_label.setText("✅ 功能已启用 - 等待热键触发")
            self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid lightgreen; border-radius: 4px;")
        else:
            if self._is_simulation_running:
                self.key_simulator.stop()
            self.statusBar().showMessage("快速向上功能已禁用")
            self.status_label.setText("❌ 功能已禁用")
            self.status_label.setStyleSheet("color: red; font-weight: bold; padding: 8px; border: 1px solid lightcoral; border-radius: 4px;")
            
    def on_hotkey_detected(self):
        """热键组合检测到"""
        if not (self.global_switch.isChecked() and not self._is_simulation_running):
            return
        
        if not self.hotkey_card.get_config().get('enabled', False):
            return
        
        # 检查窗口过滤状态
        if self._window_filter_enabled:
            if window_monitor.is_target_window_active():
                self.key_simulator.start()
        else:
            self.key_simulator.start()
            
    def on_hotkey_released(self):
        """热键组合释放"""
        if self._is_simulation_running:
            self.key_simulator.stop()
            
    def on_simulation_started(self):
        """模拟开始"""
        self._is_simulation_running = True
        self.statusBar().showMessage("按键模拟运行中...")
        self.status_label.setText("🚀 按键模拟运行中...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 8px; border: 1px solid orange; border-radius: 4px;")
        
    def on_simulation_stopped(self):
        """模拟停止"""
        self._is_simulation_running = False
        if self.global_switch.isChecked():
            self.statusBar().showMessage("等待热键触发")
            self.status_label.setText("✅ 功能已启用 - 等待热键触发")
            self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid lightgreen; border-radius: 4px;")
        else:
            self.statusBar().showMessage("功能已禁用")
    
    def on_window_filter_enabled(self, enabled):
        """窗口过滤启用状态变化"""
        self._window_filter_enabled = enabled
        performance_logger.info(f"Window filter enabled: {enabled}")
        
        if enabled:
            if not window_monitor.isRunning():
                window_monitor.start()
        
        # 更新状态显示
        if self._is_simulation_running and enabled and not window_monitor.is_target_window_active():
            self.key_simulator.stop()
    
    def on_target_window_activated(self):
        """目标窗口激活"""
        if self._window_filter_enabled:
            target_app = self.target_selector.get_target_app()
            self.status_label.setText(f"✅ {target_app} 已激活 - 快捷键功能可用")
            self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid lightgreen; border-radius: 4px;")
    
    def on_target_window_deactivated(self):
        """目标窗口失活"""
        if self._window_filter_enabled:
            if self._is_simulation_running:
                self.key_simulator.stop()
            
            target_app = self.target_selector.get_target_app()
            self.status_label.setText(f"⏸️ {target_app} 未激活 - 快捷键已暂停")
            self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 8px; border: 1px solid orange; border-radius: 4px;")
            
    def closeEvent(self, event):
        """关闭窗口事件"""
        reply = QMessageBox.question(
            self, "确认", "确定要退出吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 保存配置
            self.save_config()
            
            # 停止所有组件
            if self._is_simulation_running:
                self.key_simulator.stop()
                self.key_simulator.wait(1000)
                
            self.hotkey_listener.stop()
            
            if window_monitor.isRunning():
                window_monitor.stop()
            
            performance_logger.log_memory_usage("before shutdown")
            performance_logger.info("Application shutdown completed")
            
            event.accept()
        else:
            event.ignore() 