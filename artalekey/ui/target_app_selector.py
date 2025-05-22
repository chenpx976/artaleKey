from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QLineEdit, QCheckBox,
    QFrame, QMessageBox, QComboBox, QGroupBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
from .styles import get_selector_style, get_status_style
from ..core.window_detector import window_monitor, WindowDetector
from ..core.logger import performance_logger
import threading

class TargetAppSelector(QFrame):
    """目标应用选择器组件"""
    
    # 信号
    target_apps_changed = pyqtSignal(list)  # 目标应用列表变化
    window_filter_enabled = pyqtSignal(bool)  # 窗口过滤启用状态变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.detector = WindowDetector()
        self._current_apps = []
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_running_apps)
        self.init_ui()
        self.connect_signals()
        
        # 启动窗口监控器以收集历史记录
        if not window_monitor.isRunning():
            window_monitor.start()
        
        # 排除当前应用
        window_monitor.add_to_excluded_apps('python')
        window_monitor.add_to_excluded_apps('artalekey')
        
    def init_ui(self):
        """初始化UI"""
        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
        self.setStyleSheet(get_selector_style())
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题和启用开关
        header_layout = QHBoxLayout()
        
        title_label = QLabel("窗口过滤设置")
        title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        
        self.enable_filter_check = QCheckBox("启用窗口过滤")
        self.enable_filter_check.setToolTip("只有指定应用程序在前台时才启用快捷键功能")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.enable_filter_check)
        
        layout.addLayout(header_layout)
        
        # 说明文字
        info_label = QLabel("选择需要启用快捷键功能的应用程序。只有这些应用程序在前台时，快捷键功能才会生效。")
        info_label.setStyleSheet("color: #999999; font-size: 12px; font-weight: normal;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 最近使用的应用程序显示
        recent_apps_layout = QVBoxLayout()
        recent_apps_label = QLabel("最近使用的应用程序:")
        recent_apps_label.setFont(QFont("", 14, QFont.Weight.Bold))
        
        # 最近应用列表
        self.recent_apps_list = QListWidget()
        self.recent_apps_list.setMaximumHeight(120)
        self.recent_apps_list.setToolTip("双击应用名称快速添加到目标列表")
        
        recent_apps_layout.addWidget(recent_apps_label)
        recent_apps_layout.addWidget(self.recent_apps_list)
        
        layout.addLayout(recent_apps_layout)
        
        # 应用选择区域
        selection_layout = QHBoxLayout()
        
        # 左侧：可用应用列表
        left_panel = QVBoxLayout()
        available_label = QLabel("可用应用程序:")
        
        # 刷新按钮和搜索框
        refresh_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新列表")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索应用程序...")
        
        refresh_layout.addWidget(self.refresh_btn)
        refresh_layout.addWidget(self.search_edit)
        
        self.available_list = QListWidget()
        self.available_list.setMaximumHeight(180)
        
        left_panel.addWidget(available_label)
        left_panel.addLayout(refresh_layout)
        left_panel.addWidget(self.available_list)
        
        # 中间：操作按钮
        buttons_layout = QVBoxLayout()
        buttons_layout.addStretch()
        
        self.add_btn = QPushButton("→ 添加")
        self.add_btn.setToolTip("将选中的应用程序添加到目标列表")
        self.remove_btn = QPushButton("← 移除")
        self.remove_btn.setToolTip("从目标列表中移除选中的应用程序")
        
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.remove_btn)
        buttons_layout.addStretch()
        
        # 右侧：目标应用列表
        right_panel = QVBoxLayout()
        target_label = QLabel("目标应用程序:")
        
        self.target_list = QListWidget()
        self.target_list.setMaximumHeight(180)
        
        # 手动添加
        manual_layout = QHBoxLayout()
        self.manual_edit = QLineEdit()
        self.manual_edit.setPlaceholderText("手动输入应用程序名称...")
        self.manual_add_btn = QPushButton("手动添加")
        
        manual_layout.addWidget(self.manual_edit)
        manual_layout.addWidget(self.manual_add_btn)
        
        right_panel.addWidget(target_label)
        right_panel.addWidget(self.target_list)
        right_panel.addLayout(manual_layout)
        
        # 组装选择区域
        selection_layout.addLayout(left_panel, 2)
        selection_layout.addLayout(buttons_layout, 0)
        selection_layout.addLayout(right_panel, 2)
        
        layout.addLayout(selection_layout)
        
        # 底部状态
        self.status_label = QLabel("窗口过滤已禁用")
        self.status_label.setStyleSheet(get_status_style('error'))
        layout.addWidget(self.status_label)
        
    def connect_signals(self):
        """连接信号"""
        # UI信号
        self.enable_filter_check.stateChanged.connect(self.on_filter_enabled_changed)
        self.refresh_btn.clicked.connect(self.refresh_available_apps)
        self.add_btn.clicked.connect(self.add_selected_app)
        self.remove_btn.clicked.connect(self.remove_selected_app)
        self.manual_add_btn.clicked.connect(self.add_manual_app)
        self.search_edit.textChanged.connect(self.filter_available_apps)
        self.manual_edit.returnPressed.connect(self.add_manual_app)
        
        # 列表信号
        self.available_list.itemDoubleClicked.connect(self.add_selected_app)
        self.target_list.itemDoubleClicked.connect(self.remove_selected_app)
        self.recent_apps_list.itemDoubleClicked.connect(self.add_recent_app)
        
        # 窗口监控信号
        window_monitor.window_history_updated.connect(self.on_window_history_updated)
        window_monitor.target_window_activated.connect(self.on_target_window_activated)
        window_monitor.target_window_deactivated.connect(self.on_target_window_deactivated)
        
        # 定时刷新
        self._refresh_timer.start(5000)  # 每5秒刷新一次
        
        # 初始加载
        self.refresh_available_apps()
        self.update_recent_apps()
    
    def on_filter_enabled_changed(self, state):
        """窗口过滤启用状态改变"""
        enabled = state == Qt.CheckState.Checked.value
        
        # 启用/禁用相关控件
        self.available_list.setEnabled(enabled)
        self.target_list.setEnabled(enabled)
        self.recent_apps_list.setEnabled(enabled)
        self.add_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled)
        self.manual_edit.setEnabled(enabled)
        self.manual_add_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.search_edit.setEnabled(enabled)
        
        # 更新状态显示
        if enabled:
            target_count = self.target_list.count()
            if target_count > 0:
                self.status_label.setText(f"窗口过滤已启用 - {target_count}个目标应用")
                self.status_label.setStyleSheet(get_status_style('success'))
                # 启动窗口监控
                if not window_monitor.isRunning():
                    window_monitor.start()
                window_monitor.set_target_processes(self.get_target_apps())
            else:
                self.status_label.setText("窗口过滤已启用 - 请添加目标应用")
                self.status_label.setStyleSheet(get_status_style('warning'))
        else:
            self.status_label.setText("窗口过滤已禁用")
            self.status_label.setStyleSheet(get_status_style('error'))
        
        # 发送信号
        self.window_filter_enabled.emit(enabled)
    
    def refresh_available_apps(self):
        """刷新可用应用列表"""
        try:
            # 在后台线程中获取应用列表
            def get_apps():
                apps = self.detector.get_running_applications()
                # 过滤掉系统应用和已添加的应用
                target_apps = self.get_target_apps()
                filtered_apps = []
                
                for app in apps:
                    if app and len(app) > 1:  # 过滤掉太短的名称
                        app_lower = app.lower()
                        # 过滤系统进程
                        if not any(sys_name in app_lower for sys_name in 
                                 ['kernel', 'system', 'service', 'daemon', 'helper']):
                            if app not in target_apps:
                                filtered_apps.append(app)
                
                return filtered_apps
            
            # 使用线程池或直接调用
            apps = get_apps()
            self._current_apps = apps
            self.filter_available_apps()
            
            performance_logger.info(f"Refreshed {len(apps)} available applications")
            
        except Exception as e:
            performance_logger.error(f"Failed to refresh applications: {e}")
    
    def _refresh_running_apps(self):
        """定时刷新运行中的应用"""
        if self.enable_filter_check.isChecked():
            self.refresh_available_apps()
    
    def filter_available_apps(self):
        """根据搜索框过滤可用应用"""
        search_text = self.search_edit.text().lower()
        self.available_list.clear()
        
        for app in self._current_apps:
            if search_text in app.lower():
                self.available_list.addItem(app)
    
    def add_selected_app(self):
        """添加选中的应用"""
        current_item = self.available_list.currentItem()
        if current_item:
            app_name = current_item.text()
            self.add_target_app(app_name)
    
    def remove_selected_app(self):
        """移除选中的应用"""
        current_item = self.target_list.currentItem()
        if current_item:
            app_name = current_item.text()
            self.remove_target_app(app_name)
    
    def add_manual_app(self):
        """手动添加应用"""
        app_name = self.manual_edit.text().strip()
        if app_name:
            self.add_target_app(app_name)
            self.manual_edit.clear()
    
    def add_target_app(self, app_name: str):
        """添加目标应用"""
        if app_name and app_name not in self.get_target_apps():
            self.target_list.addItem(app_name)
            self.update_target_apps()
            self.refresh_available_apps()  # 刷新可用列表
            self.update_recent_apps()  # 刷新最近应用列表
            performance_logger.info(f"Added target app: {app_name}")
    
    def remove_target_app(self, app_name: str):
        """移除目标应用"""
        for i in range(self.target_list.count()):
            item = self.target_list.item(i)
            if item.text() == app_name:
                self.target_list.takeItem(i)
                self.update_target_apps()
                self.refresh_available_apps()  # 刷新可用列表
                self.update_recent_apps()  # 刷新最近应用列表
                performance_logger.info(f"Removed target app: {app_name}")
                break
    
    def get_target_apps(self) -> list:
        """获取目标应用列表"""
        apps = []
        for i in range(self.target_list.count()):
            apps.append(self.target_list.item(i).text())
        return apps
    
    def set_target_apps(self, apps: list):
        """设置目标应用列表"""
        self.target_list.clear()
        for app in apps:
            if app:
                self.target_list.addItem(app)
        self.update_target_apps()
    
    def update_target_apps(self):
        """更新目标应用配置"""
        target_apps = self.get_target_apps()
        
        # 更新窗口监控器
        if self.enable_filter_check.isChecked():
            window_monitor.set_target_processes(target_apps)
        
        # 更新状态显示
        if self.enable_filter_check.isChecked():
            if target_apps:
                self.status_label.setText(f"窗口过滤已启用 - {len(target_apps)}个目标应用")
                self.status_label.setStyleSheet(get_status_style('success'))
            else:
                self.status_label.setText("窗口过滤已启用 - 请添加目标应用")
                self.status_label.setStyleSheet(get_status_style('warning'))
        
        # 发送信号
        self.target_apps_changed.emit(target_apps)
    
    def on_window_history_updated(self, recent_apps):
        """窗口历史更新处理"""
        self.update_recent_apps(recent_apps)
    
    def update_recent_apps(self, recent_apps=None):
        """更新最近使用的应用程序列表"""
        if recent_apps is None:
            recent_apps = window_monitor.get_recent_apps(10)
        
        self.recent_apps_list.clear()
        target_apps = self.get_target_apps()
        
        # 添加最近使用的应用（排除已添加的）
        for app in recent_apps:
            if app not in target_apps:  # 只显示还未添加的应用
                item_text = f"{app} (最近使用)"
                self.recent_apps_list.addItem(item_text)
        
        # 如果列表为空，显示提示信息
        if self.recent_apps_list.count() == 0:
            hint_item = QListWidgetItem("使用其他应用程序后，这里会显示最近使用的应用...")
            hint_item.setFlags(hint_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)  # 禁用选择
            hint_item.setToolTip("切换到其他应用程序，然后回到这里查看最近使用的应用列表")
            self.recent_apps_list.addItem(hint_item)
    
    def add_recent_app(self):
        """从最近应用列表添加选中的应用"""
        current_item = self.recent_apps_list.currentItem()
        if current_item and current_item.flags() & Qt.ItemFlag.ItemIsEnabled:
            # 提取应用名称（移除 " (最近使用)" 后缀）
            item_text = current_item.text()
            if item_text.endswith(" (最近使用)"):
                app_name = item_text[:-7]  # 移除 " (最近使用)"
                self.add_target_app(app_name)
                # 刷新最近应用列表
                self.update_recent_apps()
    
    def on_target_window_activated(self):
        """目标窗口激活"""
        if self.enable_filter_check.isChecked():
            self.status_label.setText("目标窗口已激活 - 快捷键功能可用")
            self.status_label.setStyleSheet(get_status_style('success'))
    
    def on_target_window_deactivated(self):
        """目标窗口失活"""
        if self.enable_filter_check.isChecked():
            self.status_label.setText("目标窗口未激活 - 快捷键功能已暂停")
            self.status_label.setStyleSheet(get_status_style('warning'))
    
    def is_filter_enabled(self) -> bool:
        """检查窗口过滤是否启用"""
        return self.enable_filter_check.isChecked()
    
    def set_filter_enabled(self, enabled: bool):
        """设置窗口过滤启用状态"""
        self.enable_filter_check.setChecked(enabled) 