import uuid
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction
from pynput.keyboard import Key

from .components import HotkeyCard, ModernCheckBox
from ..core.hotkey_manager import KeySimulator, HotkeyListener
from ..core.logger import logger

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtaleKey - 快捷键管理器")
        self.setMinimumSize(QSize(400, 300))
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background: #2b2b2b;
            }
            QWidget {
                color: #ffffff;
            }
            QStatusBar {
                background: #1e1e1e;
                color: #ffffff;
            }
        """)
        
        # 初始化管理器
        self.key_simulator = KeySimulator()
        self.hotkey_listener = HotkeyListener(self)
        
        self.init_ui()
        self.hotkey_listener.start()
        logger.info("应用程序已启动")
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 添加配置卡片
        self.hotkey_card = HotkeyCard("default")
        layout.addWidget(self.hotkey_card)
        
        # 全局开关
        self.global_switch = ModernCheckBox("启用快速向上功能")
        self.global_switch.setChecked(False)  # 默认关闭
        self.global_switch.stateChanged.connect(self.on_global_switch_changed)
        layout.addWidget(self.global_switch)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def on_global_switch_changed(self, state):
        """全局开关状态改变"""
        if state:
            logger.info("快速向上功能已启用")
            self.statusBar().showMessage("快速向上功能已启用")
        else:
            if self.key_simulator.running:
                self.key_simulator.running = False
            logger.info("快速向上功能已禁用")
            self.statusBar().showMessage("快速向上功能已禁用")
            
    def closeEvent(self, event):
        """关闭窗口事件"""
        reply = QMessageBox.question(
            self, "确认", "确定要退出吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 确保停止所有功能
            if self.key_simulator.running:
                self.key_simulator.running = False
            self.hotkey_listener.running = False
            self.hotkey_listener.wait()
            logger.info("应用程序已关闭")
            event.accept()
        else:
            event.ignore() 