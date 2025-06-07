from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QPushButton
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QResizeEvent

from artalekey.ui.tabs import TabManager
from artalekey.ui.simple_styles import get_adaptive_style
from artalekey.core.config import config_manager
from artalekey.core.hotkey_manager import KeySimulator, HotkeyListener
from artalekey.core.logger import performance_logger
from artalekey.core.window_detector import window_monitor
from artalekey.core.enhanced_ocr import EnhancedOCRManager


class TabbedMainWindow(QMainWindow):
    """重构后的标签页主窗口 - 专注于框架和协调功能"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArtaleKey - 快捷键管理器")
        
        # 设置窗口最小尺寸和初始尺寸
        self.setMinimumSize(QSize(700, 520))  # 微调最小尺寸
        self.resize(QSize(800, 650))  # 设置合适的初始尺寸
        
        # 初始化组件
        self.tab_manager = None
        self.hotkey_listener = None
        self.key_simulator = None
        self.screenshot_ocr_manager = None
        
        # 窗口状态相关组件
        self.window_status_label = None
        self.activate_button = None
        
        # 运行状态
        self._is_simulation_running = False
        self._window_filter_enabled = False
        
        self._init_ui()
        self._init_core_components()
        self._load_and_apply_configs()
        self._connect_signals()
        
        # 启动热键监听
        self.hotkey_listener.start()
        
        # 记录启动性能
        performance_logger.log_memory_usage("after startup")
        
    def _init_ui(self):
        """初始化UI框架"""
        # 创建中央widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建标签页容器和管理器
        tab_widget = QTabWidget()
        self.tab_manager = TabManager(tab_widget, self)
        self.tab_manager.initialize_tabs(self)
        main_layout.addWidget(tab_widget)
        
        # 状态栏（包含窗口状态和激活按钮）
        self._init_status_bar()
        
        # 应用自适应样式
        self.update_adaptive_style()
    
    def _init_status_bar(self):
        """初始化状态栏"""
        status_bar = self.statusBar()
        
        # 窗口状态标签
        self.window_status_label = QLabel("窗口状态: 检测中...")
        self.window_status_label.setStyleSheet("color: gray; margin-right: 10px;")
        status_bar.addWidget(self.window_status_label)
        
        # 中间的弹性空间
        status_bar.addWidget(QLabel(), 1)  # 添加可拉伸的widget
        
        # 激活窗口按钮
        self.activate_button = QPushButton("激活窗口")
        self.activate_button.clicked.connect(self._on_activate_window_clicked)
        self.activate_button.setMaximumWidth(80)
        self.activate_button.setMaximumHeight(25)
        self.activate_button.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 3px;
                background-color: #007ACC;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #005999;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #666666;
            }
        """)
        status_bar.addPermanentWidget(self.activate_button)
        
        # 初始化窗口监控
        self._init_window_monitoring()
    
    def _init_core_components(self):
        """初始化核心组件"""
        self.key_simulator = KeySimulator()
        self.hotkey_listener = HotkeyListener(self)
        self.screenshot_ocr_manager = EnhancedOCRManager(self)
    
    def _load_and_apply_configs(self):
        """加载所有配置"""
        # 恢复窗口几何尺寸
        config_manager.restore_window_geometry(self)
        
        # 加载所有标签页配置
        all_configs = config_manager.load_all_ui_configs()
        
        # 应用配置到各个标签页
        for tab_name, config in all_configs.items():
            if tab_name not in ['ui']:  # 排除UI配置
                tab = self.tab_manager.get_tab(tab_name)
                if tab:
                    tab.set_config(config)
        
        # 应用核心组件配置
        self._apply_core_configs(all_configs)
    
    def _connect_signals(self):
        """连接所有信号"""
        # 连接标签页管理器信号
        signal_manager = self.tab_manager.get_signal_manager()
        signal_manager.tab_config_changed.connect(self._on_tab_config_changed)
        signal_manager.tab_status_changed.connect(self._on_tab_status_changed)
        
        # 连接各个标签页的特定信号
        self._connect_quick_up_signals()
        self._connect_ocr_signals()
        self._connect_logs_signals()
        self._connect_settings_signals()
        
        # 连接核心组件信号
        self._connect_core_signals()
    
    def _connect_quick_up_signals(self):
        """连接快速向上标签页信号"""
        quick_up_tab = self.tab_manager.get_tab('quick_up')
        if quick_up_tab:
            quick_up_tab.global_switch_changed.connect(self._on_global_switch_changed)
            quick_up_tab.hotkey_config_changed.connect(self._on_hotkey_config_changed)
    
    def _connect_ocr_signals(self):
        """连接OCR标签页信号"""
        ocr_tab = self.tab_manager.get_tab('ocr')
        if ocr_tab:
            ocr_tab.ocr_config_changed.connect(self._on_ocr_config_changed)
    
    def _connect_logs_signals(self):
        """连接日志标签页信号"""
        logs_tab = self.tab_manager.get_tab('logs')
        if logs_tab:
            # 日志标签页目前没有特殊信号需要连接
            # 如果将来需要，可以在这里添加
            pass
    
    def _connect_settings_signals(self):
        """连接设置标签页信号"""
        settings_tab = self.tab_manager.get_tab('settings')
        if settings_tab:
            settings_tab.api_key_updated.connect(self._on_api_key_updated)
            settings_tab.window_filter_enabled.connect(self._on_window_filter_enabled)
            settings_tab.target_app_changed.connect(self._on_target_app_changed)
    
    def _connect_core_signals(self):
        """连接核心组件信号"""
        # 热键监听器信号
        self.hotkey_listener.key_combination_detected.connect(self._on_hotkey_detected)
        self.hotkey_listener.key_combination_released.connect(self._on_hotkey_released)
        self.hotkey_listener.screenshot_ocr_toggle.connect(self._on_screenshot_ocr_toggle)
        
        # 模拟器信号
        self.key_simulator.simulation_started.connect(self._on_simulation_started)
        self.key_simulator.simulation_stopped.connect(self._on_simulation_stopped)
        
        # 窗口监控信号
        window_monitor.target_window_activated.connect(self._on_target_window_activated)
        window_monitor.target_window_deactivated.connect(self._on_target_window_deactivated)
        
        # OCR管理器信号
        self.screenshot_ocr_manager.ocr_triggered.connect(self._on_ocr_triggered)
        self.screenshot_ocr_manager.data_extracted.connect(self._on_game_data_extracted)
        self.screenshot_ocr_manager.error_occurred.connect(self._on_ocr_error)
    
    def _apply_core_configs(self, all_configs: dict):
        """应用核心组件配置"""
        # 应用快速向上配置
        quick_up_config = all_configs.get('quick_up', {})
        hotkey_config = quick_up_config.get('hotkey_config', {})
        if hotkey_config:
            self.hotkey_listener.set_hold_time(hotkey_config.get('hold_time', 500))
            self.key_simulator.set_interval(hotkey_config.get('interval', 50))
            # 新增：应用主触发键配置
            trigger_key = hotkey_config.get('trigger_key', 'w')
            self.hotkey_listener.set_main_trigger_key(trigger_key)
        
        # 应用OCR配置
        ocr_config = all_configs.get('ocr', {})
        if ocr_config:
            self.hotkey_listener.set_ocr_trigger_key(ocr_config.get('trigger_key', 'c'))
        
        # 应用窗口过滤配置
        settings_config = all_configs.get('settings', {})
        window_filter_config = settings_config.get('window_filter', {})
        if window_filter_config:
            target_app = window_filter_config.get('target_app', 'MapleStory Worlds')
            self.hotkey_listener.set_target_window_name(target_app)
            
            if window_filter_config.get('enabled', True):
                self._setup_window_monitoring(target_app)
        
        # 应用API密钥配置
        llm_config = settings_config.get('llm', {})
        api_key = llm_config.get('api_key', '')
        if api_key:
            self.screenshot_ocr_manager.update_llm_api_key(api_key)
            performance_logger.info(f"启动时应用 API 密钥到 LLM 处理器，密钥长度: {len(api_key)}")
        else:
            performance_logger.warning("启动时未找到 API 密钥")
    
    def _setup_window_monitoring(self, target_app: str):
        """设置窗口监控"""
        self._window_filter_enabled = True
        window_monitor.set_target_processes([target_app])
        window_monitor.start()
    
    def save_configs(self):
        """保存所有配置"""
        # 收集所有标签页配置
        all_configs = {}
        for tab_name, tab in self.tab_manager.get_all_tabs().items():
            all_configs[tab_name] = tab.get_config()
        
        # 保存窗口几何信息
        geometry = self.saveGeometry()
        if geometry:
            config_manager.save_window_geometry(geometry)
        
        # 保存所有配置
        config_manager.save_all_ui_configs(all_configs)
    
    # 样式和事件处理
    def update_adaptive_style(self):
        """更新自适应样式"""
        width = self.width()
        height = self.height()
        style = get_adaptive_style(width, height)
        self.setStyleSheet(style)
        
    def resizeEvent(self, event: QResizeEvent):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self.update_adaptive_style()
    
    # 信号处理方法
    def _on_tab_config_changed(self, tab_name: str, config: dict):
        """标签页配置变更处理"""
        self.save_configs()
        performance_logger.debug(f"标签页 {tab_name} 配置已更新")
    
    def _on_tab_status_changed(self, tab_name: str, status_message: str):
        """标签页状态变更处理"""
        self.statusBar().showMessage(f"[{tab_name}] {status_message}")
    
    def _on_global_switch_changed(self, enabled: bool):
        """全局开关变更处理"""
        self.save_configs()
    
    def _on_hotkey_config_changed(self, hotkey_id: str, config: dict):
        """热键配置变更处理"""
        if hotkey_id == "default":
            # 应用所有热键配置
            self.hotkey_listener.set_hold_time(config.get('hold_time', 500))
            self.key_simulator.set_interval(config.get('interval', 50))
            # 新增：处理主触发键变更
            trigger_key = config.get('trigger_key', 'w')
            self.hotkey_listener.set_main_trigger_key(trigger_key)
            performance_logger.info(f"热键配置已更新 - 触发键: {trigger_key}, 长按时间: {config.get('hold_time', 500)}ms, 间隔: {config.get('interval', 50)}ms")
        self.save_configs()
    
    def _on_ocr_config_changed(self, config: dict):
        """OCR配置变更处理"""
        self.hotkey_listener.set_ocr_trigger_key(config.get('trigger_key', 'c'))
        target_window = config.get('target_window', 'MapleStory Worlds')
        self.hotkey_listener.set_target_window_name(target_window)
        self.save_configs()
    
    def _on_api_key_updated(self, api_key: str):
        """API密钥更新处理"""
        self.screenshot_ocr_manager.update_llm_api_key(api_key)
        performance_logger.info(f"API 密钥已更新，长度: {len(api_key)}")
        self.save_configs()
    
    def _on_window_filter_enabled(self, enabled: bool):
        """窗口过滤开关变更处理"""
        self.save_configs()
    
    def _on_target_app_changed(self, target_app: str):
        """目标应用变更处理"""
        self.save_configs()
    
    def _on_hotkey_detected(self):
        """热键检测处理"""
        quick_up_tab = self.tab_manager.get_tab('quick_up')
        if quick_up_tab and quick_up_tab.is_enabled():
            self.key_simulator.start()
    
    def _on_hotkey_released(self):
        """热键释放处理"""
        self.key_simulator.stop()
    
    def _on_simulation_started(self):
        """模拟开始处理"""
        self._is_simulation_running = True
        quick_up_tab = self.tab_manager.get_tab('quick_up')
        if quick_up_tab:
            quick_up_tab.set_simulation_status(True)
    
    def _on_simulation_stopped(self):
        """模拟停止处理"""
        self._is_simulation_running = False
        quick_up_tab = self.tab_manager.get_tab('quick_up')
        if quick_up_tab:
            quick_up_tab.set_simulation_status(False)
    
    def _on_target_window_activated(self):
        """目标窗口激活处理"""
        self.statusBar().showMessage("目标窗口已激活")
    
    def _on_target_window_deactivated(self):
        """目标窗口失活处理"""
        self.statusBar().showMessage("目标窗口已失活")
    
    def _on_screenshot_ocr_toggle(self):
        """截屏OCR触发处理"""
        ocr_tab = self.tab_manager.get_tab('ocr')
        if not ocr_tab or not ocr_tab.is_enabled():
            if ocr_tab:
                ocr_tab.update_ocr_status("disabled")
            return
        
        self.screenshot_ocr_manager.trigger_ocr()
    
    def _on_ocr_triggered(self):
        """OCR触发确认处理"""
        ocr_tab = self.tab_manager.get_tab('ocr')
        if ocr_tab:
            ocr_tab.update_ocr_status("processing")
    
    def _on_game_data_extracted(self, game_data: dict):
        """游戏数据提取完成处理"""
        # 刷新OCR标签页中的可视化组件
        ocr_tab = self.tab_manager.get_tab('ocr')
        if ocr_tab:
            QTimer.singleShot(500, ocr_tab.refresh_visualization_data)
        
        # 更新OCR状态
        if ocr_tab:
            ocr_tab.update_ocr_status("success", game_data=game_data)
        
        # 更新状态栏
        level = game_data.get('level', '未知')
        experience = game_data.get('experience', '未知')
        money = game_data.get('money', '未知')
        
        # 格式化显示
        exp_text = self._format_experience(experience)
        money_text = self._format_money(money)
        
        status_msg = f"OCR识别完成 - 等级: {level}, 经验: {exp_text}, 金钱: {money_text}"
        self.statusBar().showMessage(status_msg)
    
    def _on_ocr_error(self, error_message: str):
        """OCR错误处理"""
        ocr_tab = self.tab_manager.get_tab('ocr')
        if ocr_tab:
            ocr_tab.update_ocr_status("error", error_message)
        self.statusBar().showMessage(f"OCR处理失败: {error_message}")
    
    def _on_activate_window_clicked(self):
        """激活窗口按钮点击"""
        from artalekey.core.window_status import window_status_monitor
        window_status_monitor.activate_target_window()
        self.statusBar().showMessage("正在尝试激活MapleStory Worlds窗口...", 3000) 
    
    # 辅助方法
    def _format_experience(self, experience) -> str:
        """格式化经验显示"""
        if experience and isinstance(experience, dict):
            exp_value = experience.get('value', 0)
            exp_percentage = experience.get('percentage', 0)
            return f"{exp_value:,} ({exp_percentage:.1f}%)"
        elif experience:
            return str(experience)
        return "未知"
    
    def _format_money(self, money) -> str:
        """格式化金钱显示"""
        if money:
            if isinstance(money, (int, float)):
                return f"{money:,}"
            else:
                return str(money)
        return "未知"
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            performance_logger.info("应用程序正在关闭...")
            
            # 保存配置
            self.save_configs()
            
            # 清理标签页资源
            if self.tab_manager:
                self.tab_manager.cleanup_all_tabs()
            
            # 停止核心组件
            self._cleanup_core_components()
            
            performance_logger.info("应用程序关闭完成")
            
        except Exception as e:
            performance_logger.error(f"关闭应用程序时发生错误: {e}")
        finally:
            event.accept()
    
    def _cleanup_core_components(self):
        """清理核心组件"""
        # 停止热键监听器
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener:
            performance_logger.info("停止热键监听器...")
            self.hotkey_listener.stop()
            self.hotkey_listener.wait(1000)
        
        # 停止按键模拟器
        if hasattr(self, 'key_simulator') and self.key_simulator:
            performance_logger.info("停止按键模拟器...")
            self.key_simulator.stop()
            self.key_simulator.wait(1000)
        
        # 停止OCR管理器
        if hasattr(self, 'screenshot_ocr_manager') and self.screenshot_ocr_manager:
            performance_logger.info("停止OCR管理器...")
            if self.screenshot_ocr_manager.isRunning():
                self.screenshot_ocr_manager.quit()
                self.screenshot_ocr_manager.wait(1000)
        
        # 清理LLM处理器线程池
        try:
            from artalekey.core.llm_processor import LLMProcessor
            LLMProcessor._cleanup_thread_pool()
            performance_logger.info("LLM处理器线程池已清理")
        except Exception as e:
            performance_logger.warning(f"清理LLM处理器线程池失败: {e}")
    
    def _init_window_monitoring(self):
        """初始化窗口监控"""
        from artalekey.core.window_status import window_status_monitor
        
        # 连接窗口状态信号
        window_status_monitor.window_status_changed.connect(self._update_window_status)
        window_status_monitor.window_found_changed.connect(self._update_window_found)
        
        # 启动窗口状态监控
        window_status_monitor.start_monitoring()
        
        # 初始状态更新
        self._update_window_status(False)
    
    def _update_window_status(self, is_active: bool):
        """更新窗口激活状态"""
        if is_active:
            self.window_status_label.setText("窗口状态: ✅ 已激活")
            self.window_status_label.setStyleSheet("color: green; font-weight: bold; margin-right: 10px;")
            self.activate_button.setEnabled(False)
        else:
            from artalekey.core.window_status import window_status_monitor
            if window_status_monitor.is_window_found():
                self.window_status_label.setText("窗口状态: ⚠️ 未激活") 
                self.window_status_label.setStyleSheet("color: orange; font-weight: bold; margin-right: 10px;")
                self.activate_button.setEnabled(True)
            else:
                self.window_status_label.setText("窗口状态: ❌ 未运行")
                self.window_status_label.setStyleSheet("color: red; font-weight: bold; margin-right: 10px;")
                self.activate_button.setEnabled(False)
    
    def _update_window_found(self, is_found: bool):
        """更新窗口存在状态"""
        from artalekey.core.window_status import window_status_monitor
        # 当窗口存在状态变化时，重新更新激活状态显示
        self._update_window_status(window_status_monitor.is_window_active()) 