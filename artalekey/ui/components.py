from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QSpinBox, QCheckBox,
    QFrame, QScrollArea, QSizePolicy, QSlider, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

class HotkeyCard(QGroupBox):
    """简化的热键配置卡片 - 原生外观"""
    config_changed = pyqtSignal(str, dict)  # 配置变更信号

    def __init__(self, hotkey_id: str, parent=None):
        super().__init__("热键设置", parent)
        self.hotkey_id = hotkey_id
        self._debounce_timer = QTimer()  # 防抖计时器
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_config_changed)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 主触发键设置
        key_layout = QHBoxLayout()
        key_label = QLabel("主触发键:")
        key_label.setMinimumWidth(120)
        
        self.key_combo = QComboBox()
        self.key_combo.setMinimumWidth(80)
        self.init_key_options()
        
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_combo)
        
        # 提示文字
        hint_label = QLabel("（需同时按住↑键）")
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        key_layout.addWidget(hint_label)
        
        key_layout.addStretch()
        layout.addLayout(key_layout)

        # 长按时间设置
        hold_layout = QVBoxLayout()
        hold_header = QHBoxLayout()
        hold_label = QLabel("长按触发时间:")
        hold_label.setMinimumWidth(120)
        self.hold_value_label = QLabel("500ms")
        self.hold_value_label.setStyleSheet("color: blue; font-weight: bold;")
        hold_header.addWidget(hold_label)
        hold_header.addWidget(self.hold_value_label)
        hold_header.addStretch()
        
        self.hold_slider = QSlider(Qt.Orientation.Horizontal)
        self.hold_slider.setRange(100, 2000)
        self.hold_slider.setValue(500)
        self.hold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.hold_slider.setTickInterval(500)
        
        hold_layout.addLayout(hold_header)
        hold_layout.addWidget(self.hold_slider)
        layout.addLayout(hold_layout)
        
        # 间隔时间设置
        interval_layout = QVBoxLayout()
        interval_header = QHBoxLayout()
        interval_label = QLabel("循环间隔时间:")
        interval_label.setMinimumWidth(120)
        self.interval_value_label = QLabel("40ms")
        self.interval_value_label.setStyleSheet("color: blue; font-weight: bold;")
        interval_header.addWidget(interval_label)
        interval_header.addWidget(self.interval_value_label)
        interval_header.addStretch()
        
        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setRange(10, 200)
        self.interval_slider.setValue(40)
        self.interval_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.interval_slider.setTickInterval(50)
        
        interval_layout.addLayout(interval_header)
        interval_layout.addWidget(self.interval_slider)
        layout.addLayout(interval_layout)

        # 启用状态
        self.enabled_check = QCheckBox("启用此功能")
        self.enabled_check.setChecked(False)  # 默认关闭
        layout.addWidget(self.enabled_check)

        # 连接信号 - 使用防抖机制
        self.key_combo.currentTextChanged.connect(self._on_config_changed_debounced)
        self.hold_slider.valueChanged.connect(self._on_hold_time_changed)
        self.interval_slider.valueChanged.connect(self._on_interval_changed)
        self.enabled_check.stateChanged.connect(self._on_config_changed_debounced)

    def init_key_options(self):
        """初始化按键选项 - 优化选项列表"""
        # 常用字母键
        common_keys = ['w', 'a', 's', 'd', 'q', 'e', 'r', 't', 'f', 'g']
        self.key_combo.addItems(common_keys)
        
        # 其他字母键
        other_letters = [chr(i) for i in range(ord('a'), ord('z') + 1) if chr(i) not in common_keys]
        self.key_combo.addItems(other_letters)
        
        self.key_combo.setCurrentText('w')  # 默认选择w键

    def _on_hold_time_changed(self, value):
        """长按时间改变处理"""
        self.hold_value_label.setText(f"{value}ms")
        self._on_config_changed_debounced()
        
    def _on_interval_changed(self, value):
        """间隔时间改变处理"""
        self.interval_value_label.setText(f"{value}ms")
        self._on_config_changed_debounced()

    def _on_config_changed_debounced(self):
        """防抖的配置变更处理"""
        self._debounce_timer.stop()
        self._debounce_timer.start(150)  # 150ms防抖

    def _emit_config_changed(self):
        """发送配置变更信号"""
        self.config_changed.emit(self.hotkey_id, self.get_config())

    def get_config(self) -> dict:
        """获取当前配置"""
        return {
            'trigger_key': self.key_combo.currentText(),
            'hold_time': self.hold_slider.value(),
            'interval': self.interval_slider.value(),
            'enabled': self.enabled_check.isChecked()
        }

    def set_config(self, config: dict):
        """设置配置 - 避免触发信号"""
        self.key_combo.blockSignals(True)
        self.hold_slider.blockSignals(True)
        self.interval_slider.blockSignals(True)
        self.enabled_check.blockSignals(True)
        
        try:
            if 'trigger_key' in config:
                self.key_combo.setCurrentText(config['trigger_key'])
            if 'hold_time' in config:
                self.hold_slider.setValue(config['hold_time'])
                self.hold_value_label.setText(f"{config['hold_time']}ms")
            if 'interval' in config:
                self.interval_slider.setValue(config['interval'])
                self.interval_value_label.setText(f"{config['interval']}ms")
            if 'enabled' in config:
                self.enabled_check.setChecked(config['enabled'])
        finally:
            self.key_combo.blockSignals(False)
            self.hold_slider.blockSignals(False)
            self.interval_slider.blockSignals(False)
            self.enabled_check.blockSignals(False)

class ScrollableHotkeyList(QScrollArea):
    """简化的可滚动热键列表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hotkey_cards = {}  # 缓存卡片引用
        self.init_ui()

    def init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.content = QWidget()
        self.layout = QVBoxLayout(self.content)
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.addStretch()
        self.setWidget(self.content)
        
        # 启用平滑滚动
        self.setVerticalScrollMode(QScrollArea.ScrollMode.ScrollPerPixel)

    def add_hotkey_card(self, hotkey_id: str, config: dict = None) -> HotkeyCard:
        """添加新的热键卡片"""
        if hotkey_id in self.hotkey_cards:
            return self.hotkey_cards[hotkey_id]
            
        card = HotkeyCard(hotkey_id)
        if config:
            card.set_config(config)
            
        # 在stretch之前插入卡片
        self.layout.insertWidget(self.layout.count() - 1, card)
        self.hotkey_cards[hotkey_id] = card
        return card

    def remove_hotkey_card(self, hotkey_id: str):
        """移除热键卡片"""
        if hotkey_id in self.hotkey_cards:
            card = self.hotkey_cards.pop(hotkey_id)
            card.deleteLater()
            
    def get_all_configs(self) -> dict:
        """获取所有卡片的配置"""
        configs = {}
        for hotkey_id, card in self.hotkey_cards.items():
            configs[hotkey_id] = card.get_config()
        return configs 