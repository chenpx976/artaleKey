from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QMessageBox, QCheckBox, QGroupBox, QLineEdit, QScrollArea, QTabWidget
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QResizeEvent
import os
import json

from artalekey.ui.components import HotkeyCard, OCRHotkeyCard
from artalekey.ui.simple_target_selector import SimpleTargetSelector
from artalekey.ui.simple_styles import get_adaptive_style, get_native_style
from artalekey.ui.window_status_widget import WindowStatusWidget
from artalekey.ui.qt_chart_widget import QtVisualizationWidget
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
        self._create_visualization_tab()
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
        
    def _create_visualization_tab(self):
        """创建可视化标签页"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 可视化组件
        self.visualization_widget = QtVisualizationWidget()
        layout.addWidget(self.visualization_widget)
        
        self.tab_widget.addTab(tab_widget, "可视化")
        
    def _create_settings_tab(self):
        """创建设置标签页"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # LLM API 配置组
        llm_group = QGroupBox("LLM API 配置")
        llm_layout = QVBoxLayout(llm_group)
        
        # API 密钥输入
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("OpenRouter API 密钥:"))
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("请输入您的 OpenRouter API 密钥")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)  # 密码模式隐藏输入
        api_key_layout.addWidget(self.api_key_input)
        
        # 显示/隐藏密钥按钮
        self.show_api_key_btn = QPushButton("显示")
        self.show_api_key_btn.setMaximumWidth(60)
        self.show_api_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(self.show_api_key_btn)
        
        llm_layout.addLayout(api_key_layout)
        
        # 保存按钮和状态
        api_key_control_layout = QHBoxLayout()
        
        self.save_api_key_btn = QPushButton("保存 API 密钥")
        self.save_api_key_btn.clicked.connect(self._save_api_key)
        api_key_control_layout.addWidget(self.save_api_key_btn)
        
        self.api_key_status_label = QLabel("未配置")
        self.api_key_status_label.setStyleSheet("color: gray; font-weight: bold;")
        api_key_control_layout.addWidget(self.api_key_status_label)
        
        api_key_control_layout.addStretch()
        llm_layout.addLayout(api_key_control_layout)
        
        # API 信息说明
        info_label = QLabel("• 获取 API 密钥：访问 <a href='https://openrouter.ai/'>OpenRouter</a> 注册并获取密钥<br>"
                           "• 使用模型：qwen/qwen2.5-vl-72b-instruct:free (免费)<br>"
                           "• 密钥将安全存储在本地配置文件中")
        info_label.setOpenExternalLinks(True)
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        info_label.setWordWrap(True)
        llm_layout.addWidget(info_label)
        
        layout.addWidget(llm_group)
        
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
        
        # 第一行按钮：数据操作
        data_operation_layout = QHBoxLayout()
        
        self.cleanup_old_data_btn = QPushButton("清理30天前数据")
        self.cleanup_old_data_btn.clicked.connect(self._cleanup_old_data)
        data_operation_layout.addWidget(self.cleanup_old_data_btn)
        
        self.export_data_btn = QPushButton("导出数据")
        self.export_data_btn.clicked.connect(self._export_data)
        data_operation_layout.addWidget(self.export_data_btn)
        
        data_operation_layout.addStretch()
        data_layout.addLayout(data_operation_layout)
        
        # 第二行按钮：文件夹操作
        folder_operation_layout = QHBoxLayout()
        
        self.open_data_dir_btn = QPushButton("打开数据目录")
        self.open_data_dir_btn.clicked.connect(self._open_data_directory)
        folder_operation_layout.addWidget(self.open_data_dir_btn)
        
        folder_operation_layout.addStretch()
        data_layout.addLayout(folder_operation_layout)
        
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
        """导出数据到JSON文件"""
        try:
            from datetime import datetime
            from artalekey.core.database import get_app_data_dir, game_db
            
            # 获取所有数据
            data = game_db.get_data_history(1000)  # 最多导出1000条
            
            # 使用应用数据目录而不是当前工作目录
            export_path = os.path.join(get_app_data_dir(), f'export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "数据导出", f"数据已导出到: {export_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据导出失败: {e}")
    
    def _open_data_directory(self):
        """打开数据目录"""
        try:
            import platform
            import subprocess
            from artalekey.core.database import get_app_data_dir
            
            data_dir = get_app_data_dir()
            
            # 确保目录存在
            os.makedirs(data_dir, exist_ok=True)
            
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", data_dir], check=True)
            elif system == "Windows":
                # Windows 使用 explorer
                subprocess.run(["explorer", data_dir], check=True)
            else:  # Linux 和其他系统
                # 尝试使用 xdg-open
                subprocess.run(["xdg-open", data_dir], check=True)
            
            self.statusBar().showMessage(f"已打开数据目录: {data_dir}")
            
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "错误", f"无法打开数据目录: {e}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开数据目录失败: {e}")
        
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
        self.target_selector.target_app_changed.connect(self.on_target_app_changed)
        
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
        
        # 应用OCR配置 - 首次启动时默认启用
        ocr_config = config_manager.get('screenshot_ocr', {})
        # 如果配置为空，设置默认启用状态
        if not ocr_config:
            ocr_config = {
                'enabled': True,  # 默认启用OCR功能
                'trigger_key': 'c',
                'target_window': 'MapleStory Worlds',
                'save_screenshots': False,  # 默认不保存截图文件
                'capture_window_only': True,
                'output_folder': 'ocr_data'
            }
        self.ocr_card.set_config(ocr_config)
        
        # 应用窗口过滤配置 - 修改：默认启用
        window_filter_config = config_manager.get('window_filter', {})
        # 如果配置为空，设置默认启用状态
        if not window_filter_config:
            window_filter_config = {
                'enabled': True,  # 默认启用窗口过滤
                'target_app': 'MapleStory Worlds'
            }
        self.target_selector.set_filter_enabled(window_filter_config.get('enabled', True))  # 默认启用
        target_app = window_filter_config.get('target_app', 'MapleStory Worlds')
        if target_app:
            self.target_selector.set_target_app(target_app)
        
        # 更新热键监听器和模拟器设置
        self.hotkey_listener.set_hold_time(hotkey_config['hold_time'])
        self.key_simulator.set_interval(hotkey_config['interval'])
        
        # 设置OCR快捷键，使用统一的目标窗口配置
        ocr_config = self.ocr_card.get_config()
        self.hotkey_listener.set_ocr_trigger_key(ocr_config.get('trigger_key', 'c'))
        # 修改：使用统一的窗口过滤配置而不是OCR独立配置
        self.hotkey_listener.set_target_window_name(target_app)
        
        # 更新OCR状态显示
        self._update_ocr_status(ocr_config, target_app)
        
        # 如果是首次启动，立即保存默认配置
        if not config_manager.get('screenshot_ocr', {}) or not config_manager.get('window_filter', {}):
            self.save_config()  # 保存默认配置，确保下次启动能记住状态
        
        # 加载并应用 API 密钥状态 - 确保 LLM 处理器得到密钥
        self._update_api_key_status()
        
        # 重要：确保 LLM 处理器立即获得 API 密钥
        llm_config = config_manager.get('llm', {})
        api_key = llm_config.get('api_key', '')
        if api_key and hasattr(self, 'screenshot_ocr_manager'):
            self.screenshot_ocr_manager.update_llm_api_key(api_key)
            performance_logger.info(f"启动时应用 API 密钥到 LLM 处理器，密钥长度: {len(api_key)}")
        else:
            performance_logger.warning("启动时未找到 API 密钥或 OCR 管理器未初始化")
        
    def _update_ocr_status(self, ocr_config, target_window):
        """更新OCR状态显示"""
        # 修改：如果配置为空或没有enabled字段，默认认为是启用状态
        enabled = ocr_config.get('enabled', True) if ocr_config else True
        
        if enabled:
            trigger_key = ocr_config.get('trigger_key', 'c')
            self.ocr_status_label.setText(f"✅ OCR功能已启用 (按 {trigger_key.upper()} 键触发，目标: {target_window})")
            self.ocr_status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid green; border-radius: 4px;")
        else:
            self.ocr_status_label.setText("❌ OCR功能未启用")
            self.ocr_status_label.setStyleSheet("color: gray; font-weight: bold; padding: 8px; border: 1px solid lightgray; border-radius: 4px;")
    
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
            
            # 同步更新热键监听器的目标窗口
            self.hotkey_listener.set_target_window_name(target_app)
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
        
        # 更新OCR状态显示
        self._update_ocr_status(config, config.get('target_window', 'MapleStory Worlds'))
        
        # 保存配置
        self.save_config()
        
    def on_screenshot_ocr_toggle(self):
        """截屏OCR触发 - 单次触发模式"""
        ocr_config = self.ocr_card.get_config()
        if not ocr_config.get('enabled', False):
            self.ocr_status_label.setText("❌ OCR功能未启用，无法触发")
            self.ocr_status_label.setStyleSheet("color: red; font-weight: bold; padding: 8px; border: 1px solid red; border-radius: 4px;")
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
        
        # 延迟刷新可视化组件，避免与其他刷新冲突
        if hasattr(self, 'visualization_widget'):
            QTimer.singleShot(500, self.visualization_widget.refresh_data)  # 延迟500ms刷新
        
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
        
        # 恢复OCR状态显示
        ocr_config = self.ocr_card.get_config()
        if level != '未知' or (experience and experience != '未知'):
            # 识别成功
            self.ocr_status_label.setText(f"✅ OCR识别成功 - 等级: {level}, 经验: {exp_text}")
            self.ocr_status_label.setStyleSheet("color: green; font-weight: bold; padding: 8px; border: 1px solid green; border-radius: 4px;")
        else:
            # 识别失败
            self.ocr_status_label.setText("⚠️ OCR识别完成，但未提取到有效数据")
            self.ocr_status_label.setStyleSheet("color: orange; font-weight: bold; padding: 8px; border: 1px solid orange; border-radius: 4px;")
        
    def on_ocr_error(self, error_message):
        """OCR错误"""
        self.ocr_status_label.setText(f"❌ OCR错误: {error_message}")
        self.ocr_status_label.setStyleSheet("color: red; font-weight: bold; padding: 8px; border: 1px solid red; border-radius: 4px;")
        self.statusBar().showMessage(f"OCR处理失败: {error_message}")
        
    def on_activate_window_requested(self):
        """激活窗口请求"""
        self.statusBar().showMessage("正在尝试激活MapleStory Worlds窗口...")
        
    def on_target_app_changed(self, target_app):
        """目标应用变更"""
        # 同步更新热键监听器的目标窗口
        if target_app:
            self.hotkey_listener.set_target_window_name(target_app)
        
        # 保存配置
        self.save_config()
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            performance_logger.info("应用程序正在关闭...")
            
            # 停止热键监听器
            if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
                performance_logger.info("停止热键监听器...")
                self.hotkey_listener.stop()
                self.hotkey_listener.wait(1000)  # 等待最多1秒
            
            # 停止按键模拟器
            if hasattr(self, 'key_simulator') and self.key_simulator:
                performance_logger.info("停止按键模拟器...")
                self.key_simulator.stop()
                self.key_simulator.wait(1000)  # 等待最多1秒
            
            # 停止OCR管理器
            if hasattr(self, 'screenshot_ocr_manager') and self.screenshot_ocr_manager:
                performance_logger.info("停止OCR管理器...")
                if self.screenshot_ocr_manager.isRunning():
                    self.screenshot_ocr_manager.quit()
                    self.screenshot_ocr_manager.wait(1000)  # 等待最多1秒
            
            # 清理LLM处理器线程池
            try:
                from artalekey.core.llm_processor import LLMProcessor
                LLMProcessor._cleanup_thread_pool()
                performance_logger.info("LLM处理器线程池已清理")
            except Exception as e:
                performance_logger.warning(f"清理LLM处理器线程池失败: {e}")
            
            performance_logger.info("应用程序关闭完成")
            
        except Exception as e:
            performance_logger.error(f"关闭应用程序时发生错误: {e}")
        finally:
            event.accept()

    def _toggle_api_key_visibility(self):
        """切换 API 密钥显示/隐藏"""
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_api_key_btn.setText("隐藏")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_api_key_btn.setText("显示")
    
    def _save_api_key(self):
        """保存 API 密钥"""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "警告", "请输入 API 密钥")
            return
        
        # 基本格式验证
        if len(api_key) < 10:
            QMessageBox.warning(self, "警告", "API 密钥格式可能不正确，长度太短")
            return
        
        try:
            performance_logger.info(f"保存 API 密钥，长度: {len(api_key)}")
            
            # 保存到配置
            llm_config = config_manager.get('llm', {})
            llm_config['api_key'] = api_key
            config_manager.set('llm', llm_config)
            
            performance_logger.info("API 密钥已保存到配置文件")
            
            # 更新 LLM 处理器
            if hasattr(self, 'screenshot_ocr_manager'):
                performance_logger.info("开始更新 LLM 处理器...")
                self.screenshot_ocr_manager.update_llm_api_key(api_key)
                
                # 验证更新是否成功
                if hasattr(self.screenshot_ocr_manager, 'llm_processor') and self.screenshot_ocr_manager.llm_processor.api_key:
                    performance_logger.info("LLM 处理器更新成功")
                    success_msg = "API 密钥已保存并成功配置 LLM 处理器"
                else:
                    performance_logger.warning("LLM 处理器更新失败")
                    success_msg = "API 密钥已保存，但 LLM 处理器配置可能有问题"
            else:
                performance_logger.warning("OCR 管理器未找到")
                success_msg = "API 密钥已保存，但无法更新 LLM 处理器"
            
            # 更新状态显示
            self._update_api_key_status()
            
            QMessageBox.information(self, "成功", success_msg)
            performance_logger.info("用户保存 API 密钥操作完成")
            
        except Exception as e:
            error_msg = f"保存 API 密钥失败: {e}"
            QMessageBox.critical(self, "错误", error_msg)
            performance_logger.error(error_msg)
    
    def _update_api_key_status(self):
        """更新 API 密钥状态显示"""
        try:
            llm_config = config_manager.get('llm', {})
            api_key = llm_config.get('api_key', '')
            
            performance_logger.info(f"更新 API 密钥状态 - 密钥长度: {len(api_key) if api_key else 0}")
            
            if api_key:
                # 隐藏密钥，只显示前4位和后4位
                if len(api_key) > 8:
                    masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
                else:
                    masked_key = "*" * len(api_key)
                
                self.api_key_status_label.setText(f"已配置: {masked_key}")
                self.api_key_status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # 在输入框中显示当前密钥
                self.api_key_input.setText(api_key)
                
                # 确保 LLM 处理器也更新了密钥
                if hasattr(self, 'screenshot_ocr_manager'):
                    performance_logger.info("正在更新 LLM 处理器的 API 密钥...")
                    self.screenshot_ocr_manager.update_llm_api_key(api_key)
                    
                    # 验证LLM处理器是否成功初始化
                    if hasattr(self.screenshot_ocr_manager, 'llm_processor') and self.screenshot_ocr_manager.llm_processor.api_key:
                        performance_logger.info("LLM 处理器 API 密钥更新成功")
                    else:
                        performance_logger.warning("LLM 处理器 API 密钥更新后，客户端仍未初始化")
                else:
                    performance_logger.warning("OCR 管理器未找到，无法更新 API 密钥")
            else:
                self.api_key_status_label.setText("未配置")
                self.api_key_status_label.setStyleSheet("color: gray; font-weight: bold;")
                self.api_key_input.clear()
                performance_logger.info("API 密钥未配置")
                
        except Exception as e:
            performance_logger.error(f"更新 API 密钥状态失败: {e}")
            self.api_key_status_label.setText("状态错误")
            self.api_key_status_label.setStyleSheet("color: red; font-weight: bold;") 