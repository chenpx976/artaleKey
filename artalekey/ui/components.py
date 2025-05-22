from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QSpinBox, QCheckBox,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

class HotkeyCard(QFrame):
    """热键配置卡片"""
    config_changed = pyqtSignal(str, dict)  # 配置变更信号

    def __init__(self, hotkey_id: str, parent=None):
        super().__init__(parent)
        self.hotkey_id = hotkey_id
        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background: #333333;
                border-radius: 4px;
                padding: 10px;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 主触发键设置
        key_layout = QHBoxLayout()
        key_label = QLabel("主触发键:")
        self.key_combo = QComboBox()
        self.init_key_options()
        
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_combo)
        
        # 提示文字
        hint_label = QLabel("（需同时按住↑键）")
        hint_label.setStyleSheet("color: #999999; font-size: 12px;")
        key_layout.addWidget(hint_label)
        
        key_layout.addStretch()
        layout.addLayout(key_layout)

        # 时间设置
        time_layout = QVBoxLayout()
        
        # 长按时间设置
        hold_layout = QHBoxLayout()
        hold_label = QLabel("长按触发时间(毫秒):")
        self.hold_spin = QSpinBox()
        self.hold_spin.setRange(0, 2000)
        self.hold_spin.setValue(500)
        self.hold_spin.setSingleStep(50)
        hold_layout.addWidget(hold_label)
        hold_layout.addWidget(self.hold_spin)
        hold_layout.addStretch()
        time_layout.addLayout(hold_layout)
        
        # 间隔时间设置
        interval_layout = QHBoxLayout()
        interval_label = QLabel("左右键循环间隔(毫秒):")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 1000)
        self.interval_spin.setValue(40)
        self.interval_spin.setSingleStep(10)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        time_layout.addLayout(interval_layout)
        
        layout.addLayout(time_layout)

        # 启用状态
        self.enabled_check = QCheckBox("启用此功能")
        self.enabled_check.setChecked(False)  # 默认关闭
        layout.addWidget(self.enabled_check)

        # 连接信号
        self.key_combo.currentTextChanged.connect(self.on_config_changed)
        self.hold_spin.valueChanged.connect(self.on_config_changed)
        self.interval_spin.valueChanged.connect(self.on_config_changed)
        self.enabled_check.stateChanged.connect(self.on_config_changed)

    def init_key_options(self):
        """初始化按键选项"""
        # 字母键
        letters = [chr(i) for i in range(ord('a'), ord('z') + 1)]
        self.key_combo.addItems(letters)
        self.key_combo.setCurrentText('w')  # 默认选择w键

    def get_config(self) -> dict:
        """获取当前配置"""
        return {
            'trigger_key': self.key_combo.currentText(),
            'hold_time': self.hold_spin.value(),
            'interval': self.interval_spin.value(),
            'enabled': self.enabled_check.isChecked()
        }

    def on_config_changed(self):
        """配置变更处理"""
        self.config_changed.emit(self.hotkey_id, self.get_config())

class ScrollableHotkeyList(QScrollArea):
    """可滚动的热键列表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4d4d4d;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        content = QWidget()
        self.layout = QVBoxLayout(content)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.addStretch()
        self.setWidget(content)

    def add_hotkey_card(self, hotkey_id: str) -> HotkeyCard:
        """添加新的热键卡片"""
        card = HotkeyCard(hotkey_id)
        # 在stretch之前插入卡片
        self.layout.insertWidget(self.layout.count() - 1, card)
        return card

    def remove_hotkey_card(self, hotkey_id: str):
        """移除热键卡片"""
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, HotkeyCard) and widget.hotkey_id == hotkey_id:
                widget.deleteLater()
                break 