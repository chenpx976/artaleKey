from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QCheckBox, QGroupBox, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QResizeEvent

from artalekey.ui.components import HotkeyCard, OCRHotkeyCard
from artalekey.ui.simple_target_selector import SimpleTargetSelector
from artalekey.ui.simple_styles import get_adaptive_style, get_native_style
from artalekey.core.hotkey_manager import KeySimulator, HotkeyListener
from artalekey.core.config import config_manager
from artalekey.core.logger import performance_logger
from artalekey.core.window_detector import window_monitor
from artalekey.core.enhanced_ocr import EnhancedOCRManager

class SimpleMainWindow(QMainWindow):
    """简化的主窗口 - 原生外观，字体自适应"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtaleKey - 快捷键管理器")
        self.setMinimumSize(QSize(400, 300))
        
        # 初始化管理器
        self.key_simulator = KeySimulator()
        self.hotkey_listener = HotkeyListener(self)
        self.screenshot_ocr_manager = EnhancedOCRManager(self)
        
        # 状态追踪
        self._is_simulation_running = False
        self._window_filter_enabled = False
        self._is_ocr_running = False
        
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
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建内容widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 设置滚动区域
        scroll_area.setWidget(content_widget)
        self.setCentralWidget(scroll_area)
        
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
        
        # OCR配置组件
        self.ocr_card = OCRHotkeyCard()
        control_layout.addWidget(self.ocr_card)
        
        # OCR状态显示
        self.ocr_status_label = QLabel("OCR功能未启用")
        self.ocr_status_label.setStyleSheet("color: gray; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        control_layout.addWidget(self.ocr_status_label)
        
        # 最新游戏数据显示
        self.game_data_label = QLabel("暂无游戏数据")
        self.game_data_label.setStyleSheet("color: black; padding: 8px; border: 1px solid lightgray; border-radius: 4px; background-color: #f5f5f5;")
        control_layout.addWidget(self.game_data_label)
        
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
        
        # 加载OCR配置
        ocr_config = config_manager.get('screenshot_ocr', {})
        self._ocr_trigger_key = ocr_config.get('trigger_key', 's')
        
        # 恢复窗口几何尺寸
        if ui_config.get('window_geometry'):
            try:
                from PyQt6.QtCore import QByteArray
                geometry_data = ui_config['window_geometry']
                if isinstance(geometry_data, str):
                    # 从base64字符串恢复QByteArray
                    geometry = QByteArray.fromBase64(geometry_data.encode('utf-8'))
                    self.restoreGeometry(geometry)
                else:
                    # 兼容旧格式
                    self.restoreGeometry(geometry_data)
            except Exception:
                pass  # 忽略几何恢复错误
    
    def save_config(self):
        """保存配置"""
        # 保存热键配置
        config_manager.set_hotkey_config("default", self.hotkey_card.get_config())
        
        # 保存UI配置
        ui_config = self._ui_config.copy()
        ui_config['global_enabled'] = self.global_switch.isChecked()
        # 将QByteArray转换为base64字符串
        geometry = self.saveGeometry()
        if geometry:
            ui_config['window_geometry'] = geometry.toBase64().data().decode('utf-8')
        config_manager.set_ui_config(ui_config)
        
        # 保存OCR配置
        ocr_config = self.ocr_card.get_config()
        config_manager.set('screenshot_ocr', ocr_config)
        
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
        
        # OCR配置卡片信号
        self.ocr_card.config_changed.connect(self.on_ocr_config_changed)
        

        
        # 配置变更信号
        self.hotkey_card.config_changed.connect(self.on_config_changed)
        
        # 热键监听器信号
        self.hotkey_listener.key_combination_detected.connect(self.on_hotkey_detected)
        self.hotkey_listener.key_combination_released.connect(self.on_hotkey_released)
        self.hotkey_listener.screenshot_ocr_toggle.connect(self.on_screenshot_ocr_toggle)
        
        # 模拟器信号
        self.key_simulator.simulation_started.connect(self.on_simulation_started)
        self.key_simulator.simulation_stopped.connect(self.on_simulation_stopped)
        
        # 目标应用选择器信号
        self.target_selector.window_filter_enabled.connect(self.on_window_filter_enabled)
        
        # 窗口监控信号
        window_monitor.target_window_activated.connect(self.on_target_window_activated)
        window_monitor.target_window_deactivated.connect(self.on_target_window_deactivated)
        
        # 截屏OCR管理器信号
        self.screenshot_ocr_manager.ocr_started.connect(self.on_ocr_started)
        self.screenshot_ocr_manager.ocr_stopped.connect(self.on_ocr_stopped)
        self.screenshot_ocr_manager.data_extracted.connect(self.on_game_data_extracted)
        self.screenshot_ocr_manager.error_occurred.connect(self.on_ocr_error)
        
        # 应用保存的配置
        self.apply_saved_config()
        
    def apply_saved_config(self):
        """应用保存的配置"""
        # 应用热键配置
        hotkey_config = config_manager.get_hotkey_config("default")
        self.hotkey_card.set_config(hotkey_config)
        
        # 应用UI配置
        self.global_switch.setChecked(self._ui_config.get('global_enabled', False))
        
        # 应用OCR配置
        ocr_config = config_manager.get('screenshot_ocr', {})
        self.ocr_card.set_config(ocr_config)
        

        
        # 应用窗口过滤配置
        window_filter_config = config_manager.get('window_filter', {})
        self.target_selector.set_filter_enabled(window_filter_config.get('enabled', False))
        target_app = window_filter_config.get('target_app', '')
        if target_app:
            self.target_selector.set_target_app(target_app)
        
        # 更新热键监听器和模拟器设置
        self.hotkey_listener.set_hold_time(hotkey_config['hold_time'])
        self.key_simulator.set_interval(hotkey_config['interval'])
        
        # 设置OCR快捷键和目标窗口
        ocr_config = self.ocr_card.get_config()
        self.hotkey_listener.set_ocr_trigger_key(ocr_config.get('trigger_key', 's'))
        self.hotkey_listener.set_target_window_name(ocr_config.get('target_window', 'MapleStory Worlds'))
        
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
    
    def on_ocr_config_changed(self, config):
        """OCR配置改变"""
        # 保存配置
        config_manager.set('screenshot_ocr', config)
        
        # 更新热键监听器
        self.hotkey_listener.set_ocr_trigger_key(config.get('trigger_key', 's'))
        self.hotkey_listener.set_target_window_name(config.get('target_window', 'MapleStory Worlds'))
        
        # 更新状态显示
        if config.get('enabled', False):
            trigger_key = config.get('trigger_key', 's')
            self.ocr_status_label.setText(f"✅ OCR功能已启用 - 按 '{trigger_key}' 键开始/停止（仅在目标窗口激活时）")
            self.ocr_status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid lightgreen; border-radius: 4px;")
        else:
            if self._is_ocr_running:
                self.screenshot_ocr_manager.stop_monitoring()
            self.ocr_status_label.setText("❌ OCR功能已禁用")
            self.ocr_status_label.setStyleSheet("color: red; font-weight: bold; padding: 8px; border: 1px solid lightcoral; border-radius: 4px;")
    
    def on_screenshot_ocr_toggle(self):
        """截屏OCR切换"""
        ocr_config = self.ocr_card.get_config()
        if not ocr_config.get('enabled', False):
            return
            
        if self._is_ocr_running:
            self.screenshot_ocr_manager.stop_monitoring()
        else:
            self.screenshot_ocr_manager.start_monitoring()
    
    def on_ocr_started(self):
        """OCR监控开始"""
        self._is_ocr_running = True
        self.ocr_status_label.setText("🔄 OCR监控运行中... (EasyOCR)")
        self.ocr_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 8px; border: 1px solid orange; border-radius: 4px;")
        performance_logger.info("OCR监控已启动")
    
    def on_ocr_stopped(self):
        """OCR监控停止"""
        self._is_ocr_running = False
        ocr_config = self.ocr_card.get_config()
        if ocr_config.get('enabled', False):
            trigger_key = ocr_config.get('trigger_key', 's')
            self.ocr_status_label.setText(f"✅ OCR功能已启用 - 按 '{trigger_key}' 键开始/停止（仅在目标窗口激活时）")
            self.ocr_status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid lightgreen; border-radius: 4px;")
        performance_logger.info("OCR监控已停止")
    
    def on_game_data_extracted(self, game_data):
        """游戏数据提取完成"""
        try:
            # 格式化显示游戏数据
            data_text = "游戏数据: "
            
            if game_data.get('level'):
                data_text += f"等级: {game_data['level']} | "
            
            if game_data.get('experience'):
                exp_data = game_data['experience']
                if isinstance(exp_data, dict):
                    exp_value = exp_data.get('value', 0)
                    exp_percentage = exp_data.get('percentage', 0)
                    data_text += f"经验: {exp_value:,} ({exp_percentage:.1f}%) | "
                else:
                    data_text += f"经验: {exp_data} | "
            
            if game_data.get('money'):
                data_text += f"金钱: {game_data['money']:,} | "
            
            data_text += f"时间: {game_data.get('timestamp', 'N/A')}"
            
            self.game_data_label.setText(data_text)
            self.game_data_label.setStyleSheet("color: darkgreen; padding: 8px; border: 1px solid lightgreen; border-radius: 4px; background-color: #f0fff0;")
            
            performance_logger.info(f"游戏数据已更新: Level={game_data.get('level')}, Exp={game_data.get('experience')}, Money={game_data.get('money')}")
            
        except Exception as e:
            performance_logger.error(f"显示游戏数据失败: {e}")
    
    def on_ocr_error(self, error_message):
        """OCR错误处理"""
        self.game_data_label.setText(f"OCR错误: {error_message}")
        self.game_data_label.setStyleSheet("color: red; padding: 8px; border: 1px solid lightcoral; border-radius: 4px; background-color: #fff0f0;")
        performance_logger.error(f"OCR错误: {error_message}")
    

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
            
            if self._is_ocr_running:
                self.screenshot_ocr_manager.stop_monitoring()
                self.screenshot_ocr_manager.wait(1000)
                
            self.hotkey_listener.stop()
            
            if window_monitor.isRunning():
                window_monitor.stop()
            
            performance_logger.log_memory_usage("before shutdown")
            performance_logger.info("Application shutdown completed")
            
            event.accept()
        else:
            event.ignore() 