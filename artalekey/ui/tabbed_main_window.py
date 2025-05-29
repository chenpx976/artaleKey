from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QCheckBox, QGroupBox, QLineEdit, QScrollArea, QTabWidget
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QResizeEvent

from artalekey.ui.components import HotkeyCard, OCRHotkeyCard
from artalekey.ui.simple_target_selector import SimpleTargetSelector
from artalekey.ui.simple_styles import get_adaptive_style, get_native_style
from artalekey.ui.window_status_widget import WindowStatusWidget
from artalekey.core.hotkey_manager import KeySimulator, HotkeyListener
from artalekey.core.config import config_manager
from artalekey.core.logger import performance_logger
from artalekey.core.window_detector import window_monitor
from artalekey.core.enhanced_ocr import EnhancedOCRManager

class TabbedMainWindow(QMainWindow):
    """带标签页的主窗口 - 每个快捷键功能使用单独的标签页"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtaleKey - 快捷键管理器")
        self.setMinimumSize(QSize(500, 400))
        
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
        """初始化UI"""
        # 创建中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 窗口状态组件（置顶显示）
        self.window_status_widget = WindowStatusWidget()
        main_layout.addWidget(self.window_status_widget)
        
        # 创建标签页容器
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建各个标签页
        self._create_quick_up_tab()
        self._create_ocr_tab()
        self._create_settings_tab()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def _create_quick_up_tab(self):
        """创建快速向上功能标签页"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 热键配置组
        hotkey_group = QGroupBox("快速向上热键配置")
        hotkey_layout = QVBoxLayout(hotkey_group)
        
        self.hotkey_card = HotkeyCard("default")
        hotkey_layout.addWidget(self.hotkey_card)
        
        layout.addWidget(hotkey_group)
        
        # 功能控制组
        control_group = QGroupBox("功能控制")
        control_layout = QVBoxLayout(control_group)
        
        self.global_switch = QCheckBox("启用快速向上功能")
        control_layout.addWidget(self.global_switch)
        
        # 状态指示器
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: blue; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        control_layout.addWidget(self.status_label)
        
        layout.addWidget(control_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        self.tab_widget.addTab(tab_widget, "快速向上")
        
    def _create_ocr_tab(self):
        """创建OCR功能标签页"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # OCR配置组
        ocr_group = QGroupBox("OCR识别配置")
        ocr_layout = QVBoxLayout(ocr_group)
        
        # OCR配置组件
        self.ocr_card = OCRHotkeyCard()
        ocr_layout.addWidget(self.ocr_card)
        
        layout.addWidget(ocr_group)
        
        # OCR状态组
        status_group = QGroupBox("OCR状态")
        status_layout = QVBoxLayout(status_group)
        
        # OCR状态显示
        self.ocr_status_label = QLabel("OCR功能未启用")
        self.ocr_status_label.setStyleSheet("color: gray; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        status_layout.addWidget(self.ocr_status_label)
        
        layout.addWidget(status_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        self.tab_widget.addTab(tab_widget, "OCR识别")
        
    def _create_settings_tab(self):
        """创建设置标签页"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 目标应用设置组
        app_group = QGroupBox("目标应用设置")
        app_layout = QVBoxLayout(app_group)
        
        # 简化的目标应用选择器
        self.target_selector = SimpleTargetSelector()
        app_layout.addWidget(self.target_selector)
        
        layout.addWidget(app_group)
        
        # 数据管理组
        data_group = QGroupBox("数据管理")
        data_layout = QVBoxLayout(data_group)
        
        # 数据清理按钮
        cleanup_layout = QHBoxLayout()
        
        self.cleanup_old_data_btn = QPushButton("清理30天前数据")
        self.cleanup_old_data_btn.clicked.connect(self._cleanup_old_data)
        cleanup_layout.addWidget(self.cleanup_old_data_btn)
        
        self.export_data_btn = QPushButton("导出数据")
        self.export_data_btn.clicked.connect(self._export_data)
        cleanup_layout.addWidget(self.export_data_btn)
        
        cleanup_layout.addStretch()
        data_layout.addLayout(cleanup_layout)
        
        layout.addWidget(data_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        self.tab_widget.addTab(tab_widget, "设置")
        
    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            from artalekey.core.database import game_db
            deleted_count = game_db.delete_old_data(30)
            QMessageBox.information(self, "数据清理", f"已删除 {deleted_count} 条30天前的数据")
            # 刷新窗口状态组件的数据显示
            self.window_status_widget.refresh_data()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据清理失败: {e}")
    
    def _export_data(self):
        """导出数据"""
        try:
            from artalekey.core.database import game_db
            import json
            import os
            from datetime import datetime
            
            # 获取所有数据
            data = game_db.get_data_history(1000)  # 最多导出1000条
            
            # 导出到JSON文件
            export_path = os.path.join(os.getcwd(), 'ocr_data', f'export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "数据导出", f"数据已导出到: {export_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据导出失败: {e}")
        
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
        self.screenshot_ocr_manager.ocr_triggered.connect(self.on_ocr_triggered)
        self.screenshot_ocr_manager.data_extracted.connect(self.on_game_data_extracted)
        self.screenshot_ocr_manager.error_occurred.connect(self.on_ocr_error)
        
        # 窗口状态组件信号
        self.window_status_widget.activate_window_requested.connect(self.on_activate_window_requested)
        
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
            
        # 保存配置
        self.save_config()
        
    def on_global_switch_changed(self, state):
        """全局开关状态变更"""
        enabled = state == Qt.CheckState.Checked.value
        
        if enabled:
            self.status_label.setText("快速向上功能已启用")
            self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        else:
            self.status_label.setText("快速向上功能已禁用")
            self.status_label.setStyleSheet("color: red; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        
        # 保存配置
        self.save_config()
        
    def on_hotkey_detected(self):
        """热键检测到"""
        if not self.global_switch.isChecked():
            return
            
        self.key_simulator.start()
        
    def on_hotkey_released(self):
        """热键释放"""
        self.key_simulator.stop()
        
    def on_simulation_started(self):
        """模拟开始"""
        self._is_simulation_running = True
        self.status_label.setText("正在执行快速向上...")
        self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        
    def on_simulation_stopped(self):
        """模拟停止"""
        self._is_simulation_running = False
        if self.global_switch.isChecked():
            self.status_label.setText("快速向上功能已启用")
            self.status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        else:
            self.status_label.setText("快速向上功能已禁用")
            self.status_label.setStyleSheet("color: red; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
            
    def on_window_filter_enabled(self, enabled):
        """窗口过滤启用状态变更"""
        self._window_filter_enabled = enabled
        
        if enabled:
            target_app = self.target_selector.get_target_app()
            window_monitor.set_target_processes([target_app])
            window_monitor.start()
        else:
            window_monitor.stop()
            
        # 保存配置
        self.save_config()
        
    def on_target_window_activated(self):
        """目标窗口激活"""
        self.statusBar().showMessage("目标窗口已激活")
        
    def on_target_window_deactivated(self):
        """目标窗口失活"""
        self.statusBar().showMessage("目标窗口已失活")
        
    def on_ocr_config_changed(self, config):
        """OCR配置变更"""
        # 更新热键监听器的OCR设置
        self.hotkey_listener.set_ocr_trigger_key(config.get('trigger_key', 'c'))
        self.hotkey_listener.set_target_window_name(config.get('target_window', 'MapleStory Worlds'))
        
        # 保存配置
        self.save_config()
        
    def on_screenshot_ocr_toggle(self):
        """截屏OCR触发 - 单次触发模式"""
        ocr_config = self.ocr_card.get_config()
        if not ocr_config.get('enabled', False):
            return
            
        # 调用单次OCR触发
        self.screenshot_ocr_manager.trigger_ocr()
            
    def on_ocr_triggered(self):
        """OCR触发确认"""
        self.ocr_status_label.setText("🔄 正在执行OCR识别...")
        self.ocr_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 8px; border: 1px solid orange; border-radius: 4px;")
        
    def on_game_data_extracted(self, game_data):
        """游戏数据提取完成"""
        # 刷新窗口状态组件的数据显示
        self.window_status_widget.refresh_data()
        
        # 更新状态栏
        level = game_data.get('level', '未知')
        experience = game_data.get('experience', '未知')
        money = game_data.get('money', '未知')
        
        # 格式化经验显示
        exp_text = "未知"
        if experience and isinstance(experience, dict):
            exp_value = experience.get('value', 0)
            exp_percentage = experience.get('percentage', 0)
            exp_text = f"{exp_value:,} ({exp_percentage:.1f}%)"
        elif experience:
            exp_text = str(experience)
        
        # 格式化金钱显示
        money_text = "未知"
        if money:
            if isinstance(money, (int, float)):
                money_text = f"{money:,}"
            else:
                money_text = str(money)
        
        status_msg = f"OCR识别完成 - 等级: {level}, 经验: {exp_text}, 金钱: {money_text}"
        self.statusBar().showMessage(status_msg)
        
    def on_ocr_error(self, error_message):
        """OCR错误"""
        self.ocr_status_label.setText(f"OCR错误: {error_message}")
        self.ocr_status_label.setStyleSheet("color: red; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
        
    def on_activate_window_requested(self):
        """激活窗口请求"""
        self.statusBar().showMessage("正在尝试激活MapleStory Worlds窗口...")
        
    def closeEvent(self, event):
        """关闭事件"""
        # 保存配置
        self.save_config()
        
        # 停止所有服务
        self.hotkey_listener.stop()
        self.key_simulator.stop()
        window_monitor.stop()
        
        # 停止窗口状态监控
        if hasattr(self, 'window_status_widget'):
            self.window_status_widget.close()
        
        event.accept() 