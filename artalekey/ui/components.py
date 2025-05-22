from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QSpinBox, QCheckBox,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor

class ModernComboBox(QComboBox):
    """现代风格的下拉框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
                background: #2b2b2b;
                color: #ffffff;
            }
            QComboBox:hover {
                border-color: #4d4d4d;
            }
            QComboBox:focus {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background: #2b2b2b;
                border: 1px solid #3d3d3d;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
            }
        """)

class ModernSpinBox(QSpinBox):
    """现代风格的数字输入框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QSpinBox {
                border: 2px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px;
                background: #2b2b2b;
                color: #ffffff;
            }
            QSpinBox:hover {
                border-color: #4d4d4d;
            }
            QSpinBox:focus {
                border-color: #0078d4;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                border: none;
                background: #3d3d3d;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: #4d4d4d;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 5px solid #ffffff;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
            }
        """)

class ModernCheckBox(QCheckBox):
    """现代风格的复选框"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
                font-size: 14px;
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #3d3d3d;
                background: #2b2b2b;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #4d4d4d;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0078d4;
                background: #0078d4;
            }
            QCheckBox::indicator:checked:hover {
                background: #006cbd;
                border-color: #006cbd;
            }
        """)

class HotkeyCard(QFrame):
    """热键配置卡片"""
    deleted = pyqtSignal(str)  # 删除信号
    config_changed = pyqtSignal(str, dict)  # 配置变更信号

    def __init__(self, hotkey_id: str, parent=None):
        super().__init__(parent)
        self.hotkey_id = hotkey_id
        self.init_ui()

    def init_ui(self):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            HotkeyCard {
                background: #333333;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel {
                color: #ffffff;
            }
            .hint {
                color: #999999;
                font-size: 12px;
                font-style: italic;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 主触发键设置
        key_layout = QHBoxLayout()
        key_label = QLabel("主触发键:")
        self.key_combo = ModernComboBox()
        self.init_key_options()
        
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_combo)
        
        # 提示文字
        hint_label = QLabel("（需同时按住↑键）")
        hint_label.setProperty("class", "hint")
        key_layout.addWidget(hint_label)
        
        key_layout.addStretch()
        layout.addLayout(key_layout)

        # 时间设置
        time_layout = QVBoxLayout()
        
        # 长按时间设置
        hold_layout = QHBoxLayout()
        hold_label = QLabel("长按触发时间(毫秒):")
        self.hold_spin = ModernSpinBox()
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
        self.interval_spin = ModernSpinBox()
        self.interval_spin.setRange(10, 1000)
        self.interval_spin.setValue(40)
        self.interval_spin.setSingleStep(10)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        time_layout.addLayout(interval_layout)
        
        layout.addLayout(time_layout)

        # 启用状态
        self.enabled_check = ModernCheckBox("启用此功能")
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