from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon

from .components import HotkeyCard
from ..core.hotkey_manager import KeySimulator, HotkeyListener
from ..core.config import config_manager
from ..core.logger import performance_logger

class MainWindow(QMainWindow):
    """优化的主窗口 - 改善响应性和资源管理"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtaleKey - 快捷键管理器")
        self.setMinimumSize(QSize(400, 300))
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #2b2b2b;
                color: #ffffff;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QCheckBox {
                font-size: 14px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                background: #444444;
                border: 2px solid #666666;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background: #4CAF50;
                border-color: #4CAF50;
            }
        """)
        
        # 初始化管理器
        self.key_simulator = KeySimulator()
        self.hotkey_listener = HotkeyListener(self)
        
        # 状态追踪
        self._is_simulation_running = False
        
        # 加载配置
        self.load_config()
        
        self.init_ui()
        self.connect_signals()
        self.hotkey_listener.start()
        
        # 记录启动性能
        performance_logger.log_memory_usage("after startup")
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 添加配置卡片
        self.hotkey_card = HotkeyCard("default")
        layout.addWidget(self.hotkey_card)
        
        # 全局开关
        self.global_switch = QCheckBox("启用快速向上功能")
        layout.addWidget(self.global_switch)
        
        # 添加状态指示器
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                background: #333333;
                padding: 8px;
                border-radius: 4px;
                border-left: 4px solid #4CAF50;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    @performance_logger.measure_time("load_config")
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
    
    @performance_logger.measure_time("save_config")
    def save_config(self):
        """保存配置"""
        # 保存热键配置
        config_manager.set_hotkey_config("default", self.hotkey_card.get_config())
        
        # 保存UI配置
        ui_config = self._ui_config.copy()
        ui_config['global_enabled'] = self.global_switch.isChecked()
        ui_config['window_geometry'] = self.saveGeometry()
        config_manager.set_ui_config(ui_config)
        
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
        
        # 应用保存的配置
        self.apply_saved_config()
        
    def apply_saved_config(self):
        """应用保存的配置"""
        # 应用热键配置
        hotkey_config = config_manager.get_hotkey_config("default")
        self.hotkey_card.set_config(hotkey_config)
        
        # 应用UI配置
        self.global_switch.setChecked(self._ui_config.get('global_enabled', False))
        
        # 更新热键监听器和模拟器设置
        self.hotkey_listener.set_hold_time(hotkey_config['hold_time'])
        self.key_simulator.set_interval(hotkey_config['interval'])
        
    def on_config_changed(self, hotkey_id: str, config: dict):
        """配置变更处理 - 实时应用设置"""
        if hotkey_id == "default":
            # 更新长按时间
            self.hotkey_listener.set_hold_time(config['hold_time'])
            # 更新模拟器间隔
            self.key_simulator.set_interval(config['interval'])
            
            # 更新状态显示
            self.status_label.setText(f"配置已更新 - 长按时间: {config['hold_time']}ms, 间隔: {config['interval']}ms")
            
            # 自动保存配置
            config_manager.set_hotkey_config(hotkey_id, config, auto_save=False)  # 延迟保存
            
            # 使用定时器延迟保存，避免频繁I/O
            if not hasattr(self, '_save_timer'):
                self._save_timer = QTimer()
                self._save_timer.setSingleShot(True)
                self._save_timer.timeout.connect(config_manager.save_config)
            self._save_timer.stop()
            self._save_timer.start(1000)  # 1秒后保存
        
    def on_global_switch_changed(self, state):
        """全局开关状态改变"""
        if state:
            self.statusBar().showMessage("快速向上功能已启用")
            self.status_label.setText("功能已启用 - 等待热键触发")
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #333333;
                    padding: 8px;
                    border-radius: 4px;
                    border-left: 4px solid #4CAF50;
                }
            """)
        else:
            if self._is_simulation_running:
                self.key_simulator.stop()
            self.statusBar().showMessage("快速向上功能已禁用")
            self.status_label.setText("功能已禁用")
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #333333;
                    padding: 8px;
                    border-radius: 4px;
                    border-left: 4px solid #f44336;
                }
            """)
            
    def on_hotkey_detected(self):
        """热键组合检测到"""
        if self.global_switch.isChecked() and not self._is_simulation_running:
            if self.hotkey_card.get_config().get('enabled', False):
                self.key_simulator.start()
            
    def on_hotkey_released(self):
        """热键组合释放"""
        if self._is_simulation_running:
            self.key_simulator.stop()
            
    def on_simulation_started(self):
        """模拟开始"""
        self._is_simulation_running = True
        self.statusBar().showMessage("按键模拟运行中...")
        self.status_label.setText("按键模拟运行中...")
        self.status_label.setStyleSheet("""
            QLabel {
                background: #333333;
                padding: 8px;
                border-radius: 4px;
                border-left: 4px solid #FF9800;
            }
        """)
        
    def on_simulation_stopped(self):
        """模拟停止"""
        self._is_simulation_running = False
        if self.global_switch.isChecked():
            self.statusBar().showMessage("等待热键触发")
            self.status_label.setText("功能已启用 - 等待热键触发")
            self.status_label.setStyleSheet("""
                QLabel {
                    background: #333333;
                    padding: 8px;
                    border-radius: 4px;
                    border-left: 4px solid #4CAF50;
                }
            """)
        else:
            self.statusBar().showMessage("功能已禁用")
            
    def closeEvent(self, event):
        """优化的关闭窗口事件 - 确保资源正确释放"""
        reply = QMessageBox.question(
            self, "确认", "确定要退出吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 保存配置
            self.save_config()
            
            # 安全停止所有组件
            if self._is_simulation_running:
                self.key_simulator.stop()
                self.key_simulator.wait(1000)  # 等待最多1秒
                
            self.hotkey_listener.stop()
            
            # 记录关闭性能
            performance_logger.log_memory_usage("before shutdown")
            performance_logger.info("Application shutdown completed")
            
            event.accept()
        else:
            event.ignore() 