from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QResizeEvent

from artalekey.ui.tabs import TabManager
from artalekey.ui.simple_styles import get_adaptive_style
from artalekey.ui.multi_status_bar import MultiLineStatusWidget
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
        
        # 多行状态栏组件
        self.multi_status_widget = None
        
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
        main_layout.setContentsMargins(10, 10, 10, 0)  # 底部边距设为0，让状态栏紧贴底部
        main_layout.setSpacing(10)
        
        # 创建标签页容器和管理器
        tab_widget = QTabWidget()
        self.tab_manager = TabManager(tab_widget, self)
        self.tab_manager.initialize_tabs(self)
        main_layout.addWidget(tab_widget)
        
        # 多行状态栏（替代原来的状态栏）
        self._init_multi_status_bar()
        main_layout.addWidget(self.multi_status_widget)
        
        # 应用自适应样式
        self.update_adaptive_style()
    
    def _init_multi_status_bar(self):
        """初始化多行状态栏"""
        self.multi_status_widget = MultiLineStatusWidget()
        self.multi_status_widget.activate_window_requested.connect(self._on_activate_window_clicked)
        
        # 初始化窗口监控
        self._init_window_monitoring()
        
        # 初始化时加载最新的游戏数据
        self._load_latest_game_data()
    
    def _load_latest_game_data(self):
        """加载最新的游戏数据到状态栏"""
        try:
            from artalekey.core.database import game_db
            latest_data = game_db.get_latest_data()
            if latest_data:
                self.multi_status_widget.update_game_data(latest_data)
        except Exception as e:
            performance_logger.warning(f"加载最新游戏数据失败: {e}")
    
    def _init_core_components(self):
        """初始化核心组件"""
        self.key_simulator = KeySimulator()
        self.hotkey_listener = HotkeyListener(self)
        self.screenshot_ocr_manager = EnhancedOCRManager(self)
    
    def _load_and_apply_configs(self):
        """加载所有配置"""
        # 恢复窗口几何尺寸
        config_manager.restore_window_geometry(self)
        
        # 应用核心组件配置
        self._apply_core_configs()
    
    def _apply_core_configs(self):
        """应用核心组件配置"""
        # 应用快速向上配置
        hotkey_config = config_manager.get_hotkey_config("default")
        self.hotkey_listener.set_hold_time(hotkey_config['hold_time'])
        self.key_simulator.set_interval(hotkey_config['interval'])
        # 新增：应用主触发键配置
        trigger_key = hotkey_config['trigger_key']
        self.hotkey_listener.set_main_trigger_key(trigger_key)
        
        # 应用OCR配置
        ocr_trigger_key = config_manager.get('screenshot_ocr', 'trigger_key')
        self.hotkey_listener.set_ocr_trigger_key(ocr_trigger_key)
        
        # 应用窗口过滤配置
        window_filter_enabled = config_manager.get('window_filter', 'enabled')
        target_app = config_manager.get('window_filter', 'target_app')
        self.hotkey_listener.set_target_window_name(target_app)
        
        if window_filter_enabled:
            self._setup_window_monitoring(target_app)
        
        # 应用API密钥配置
        api_key = config_manager.get('llm', 'api_key')
        if api_key:
            self.screenshot_ocr_manager.update_llm_api_key(api_key)
            performance_logger.info(f"启动时应用 API 密钥到 LLM 处理器，密钥长度: {len(api_key)}")
        else:
            performance_logger.warning("启动时未找到 API 密钥")
    
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
    
    def _setup_window_monitoring(self, target_app: str):
        """设置窗口监控"""
        self._window_filter_enabled = True
        window_monitor.set_target_processes([target_app])
        window_monitor.start()
    
    def save_configs(self):
        """保存所有配置"""
        # 保存窗口几何信息
        geometry = self.saveGeometry()
        if geometry:
            config_manager.save_window_geometry(geometry)
    
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
        performance_logger.debug(f"标签页 {tab_name} 配置已更新")
    
    def _on_tab_status_changed(self, tab_name: str, status_message: str):
        """标签页状态变更处理"""
        # 不再使用传统状态栏显示消息，可以考虑其他方式或忽略
        pass
    
    def _on_global_switch_changed(self, enabled: bool):
        """全局开关变更处理"""
        # 配置已在标签页中保存，这里不需要额外操作
        pass
    
    def _on_hotkey_config_changed(self, hotkey_id: str, config: dict):
        """热键配置变更处理"""
        if hotkey_id == "default":
            # 应用所有热键配置
            self.hotkey_listener.set_hold_time(config['hold_time'])
            self.key_simulator.set_interval(config['interval'])
            # 新增：处理主触发键变更
            trigger_key = config['trigger_key']
            self.hotkey_listener.set_main_trigger_key(trigger_key)
            performance_logger.info(f"热键配置已更新 - 触发键: {trigger_key}, 长按时间: {config['hold_time']}ms, 间隔: {config['interval']}ms")
    
    def _on_ocr_config_changed(self, config: dict):
        """OCR配置变更处理"""
        self.hotkey_listener.set_ocr_trigger_key(config['trigger_key'])
        target_window = config['target_window']
        self.hotkey_listener.set_target_window_name(target_window)
        # 更新OCR状态显示
        self._update_ocr_status_display(config)
    
    def _update_ocr_status_display(self, config: dict):
        """更新OCR状态显示"""
        enabled = config.get('enabled', True)
        trigger_key = config.get('trigger_key', 'c')
        
        if enabled:
            status_text = f"✅ 已启用 (按 {trigger_key.upper()} 键触发)"
            status_type = "success"
        else:
            status_text = "❌ 未启用"
            status_type = "error"
        
        if self.multi_status_widget:
            self.multi_status_widget.update_ocr_status(status_text, status_type)
    
    def _on_api_key_updated(self, api_key: str):
        """API密钥更新处理"""
        self.screenshot_ocr_manager.update_llm_api_key(api_key)
        performance_logger.info(f"API 密钥已更新，长度: {len(api_key)}")
    
    def _on_window_filter_enabled(self, enabled: bool):
        """窗口过滤开关变更处理"""
        # 配置已在标签页中保存，这里不需要额外操作
        pass
    
    def _on_target_app_changed(self, target_app: str):
        """目标应用变更处理"""
        # 配置已在标签页中保存，这里不需要额外操作
        pass
    
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
        pass  # 窗口状态已通过_update_window_status处理
    
    def _on_target_window_deactivated(self):
        """目标窗口失活处理"""
        pass  # 窗口状态已通过_update_window_status处理
    
    def _on_screenshot_ocr_toggle(self):
        """截屏OCR触发处理"""
        ocr_tab = self.tab_manager.get_tab('ocr')
        if not ocr_tab or not ocr_tab.is_enabled():
            if self.multi_status_widget:
                self.multi_status_widget.update_ocr_status("❌ 功能未启用，无法触发", "error")
            return
        
        self.screenshot_ocr_manager.trigger_ocr()
    
    def _on_ocr_triggered(self):
        """OCR触发确认处理"""
        if self.multi_status_widget:
            self.multi_status_widget.update_ocr_status("🔄 正在执行识别...", "processing")
    
    def _on_game_data_extracted(self, game_data: dict):
        """游戏数据提取完成处理"""
        # 刷新OCR标签页中的可视化组件
        ocr_tab = self.tab_manager.get_tab('ocr')
        if ocr_tab:
            QTimer.singleShot(500, ocr_tab.refresh_visualization_data)
        
        # 更新OCR状态
        if ocr_tab:
            ocr_tab.update_ocr_status("success", game_data=game_data)
        
        # 更新多行状态栏中的OCR状态和游戏数据
        level = game_data.get('level', '未知')
        experience = game_data.get('experience', '未知')
        
        # 格式化显示
        exp_text = self._format_experience(experience)
        
        # 更新OCR状态
        status_text = f"✅ 识别成功 - 等级: {level}, 经验: {exp_text}"
        if self.multi_status_widget:
            self.multi_status_widget.update_ocr_status(status_text, "success")
            # 更新游戏数据显示
            self.multi_status_widget.update_game_data(game_data)
    
    def _on_ocr_error(self, error_message: str):
        """OCR错误处理"""
        ocr_tab = self.tab_manager.get_tab('ocr')
        if ocr_tab:
            ocr_tab.update_ocr_status("error", error_message)
        
        # 更新多行状态栏中的OCR状态
        if self.multi_status_widget:
            self.multi_status_widget.update_ocr_status(f"❌ 处理失败: {error_message}", "error")
    
    def _on_activate_window_clicked(self):
        """激活窗口按钮点击"""
        from artalekey.core.window_status import window_status_monitor
        window_status_monitor.activate_target_window()
        
        # 临时显示激活中状态
        if self.multi_status_widget:
            self.multi_status_widget.update_window_status(False, True)  # 显示为未激活但存在
            # 可以考虑添加一个临时的"正在激活..."状态
    
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
        from artalekey.core.window_status import window_status_monitor
        is_found = window_status_monitor.is_window_found()
        
        if self.multi_status_widget:
            self.multi_status_widget.update_window_status(is_active, is_found)
    
    def _update_window_found(self, is_found: bool):
        """更新窗口存在状态"""
        from artalekey.core.window_status import window_status_monitor
        # 当窗口存在状态变化时，重新更新激活状态显示
        self._update_window_status(window_status_monitor.is_window_active()) 