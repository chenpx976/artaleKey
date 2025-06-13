from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QMessageBox, QFrame, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, QTimer
from typing import Dict, Any
import os
import json
import platform
import subprocess
from datetime import datetime

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.ui.simple_target_selector import SimpleTargetSelector
from artalekey.core.config import config_manager
from artalekey.core.logger import performance_logger
from artalekey.core.permissions import (
    permission_manager, PermissionType, PermissionStatus,
    get_permission_status_text, get_permission_name, get_permission_description
)


class SettingsTab(BaseTab):
    """设置标签页"""
    
    # 特定信号
    api_key_updated = pyqtSignal(str)  # API密钥更新信号
    window_filter_enabled = pyqtSignal(bool)  # 窗口过滤启用信号
    target_app_changed = pyqtSignal(str)  # 目标应用变更信号
    
    def __init__(self, parent=None):
        self._api_key_input = None
        self._show_api_key_btn = None
        self._save_api_key_btn = None
        self._api_key_status_label = None
        self._target_selector = None
        self._cleanup_old_data_btn = None
        self._export_data_btn = None
        self._open_data_dir_btn = None
        
        # 权限相关UI组件
        self._permission_labels = {}
        self._permission_buttons = {}
        self._refresh_permissions_btn = None
        self._permission_timer = None
        
        super().__init__("settings", parent)
        
    def init_ui(self):
        """初始化UI"""
        # macOS 权限管理组（仅在macOS上显示）
        if permission_manager.is_supported():
            self._create_permissions_group()
        
        # LLM API 配置组
        self._create_llm_config_group()
        
        # 目标应用设置组
        self._create_target_app_group()
        
        # 数据管理组
        self._create_data_management_group()
        
        # 添加弹性空间
        self.main_layout.addStretch()
        
        # 启动权限检查定时器（仅在macOS上）
        if permission_manager.is_supported():
            self._start_permission_timer()
        
        # 加载当前配置到UI组件
        self._load_config_to_ui()
    
    def _create_permissions_group(self):
        """创建权限管理组（仅macOS）"""
        permissions_group = QGroupBox("macOS 系统权限")
        permissions_layout = QVBoxLayout(permissions_group)
        
        # 权限说明
        info_label = QLabel(
            "⚠️ ArtaleKey 需要以下系统权限才能正常工作。"
            "请点击对应按钮授予权限，然后重启应用。"
        )
        info_label.setStyleSheet("color: #666; font-weight: bold; padding: 5px;")
        info_label.setWordWrap(True)
        permissions_layout.addWidget(info_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        permissions_layout.addWidget(line)
        
        # 为每个权限创建UI
        for perm_type in PermissionType:
            self._create_permission_row(permissions_layout, perm_type)
        
        # 权限操作按钮
        button_layout = QHBoxLayout()
        
        self._refresh_permissions_btn = QPushButton("🔄 刷新权限状态")
        self._refresh_permissions_btn.clicked.connect(self._refresh_permissions)
        button_layout.addWidget(self._refresh_permissions_btn)
        
        open_settings_btn = QPushButton("⚙️ 打开隐私设置")
        open_settings_btn.clicked.connect(self._open_privacy_settings)
        button_layout.addWidget(open_settings_btn)
        
        button_layout.addStretch()
        permissions_layout.addLayout(button_layout)
        
        self.main_layout.addWidget(permissions_group)
        
        # 初始权限检查
        self._refresh_permissions()
    
    def _create_permission_row(self, layout: QVBoxLayout, perm_type: PermissionType):
        """为单个权限创建UI行"""
        row_layout = QHBoxLayout()
        
        # 权限名称和描述
        name_label = QLabel(f"🔧 {get_permission_name(perm_type)}")
        name_label.setStyleSheet("font-weight: bold; min-width: 80px;")
        row_layout.addWidget(name_label)
        
        desc_label = QLabel(get_permission_description(perm_type))
        desc_label.setStyleSheet("color: #666; font-size: 11px;")
        row_layout.addWidget(desc_label)
        
        row_layout.addStretch()
        
        # 权限状态标签
        status_label = QLabel("检查中...")
        status_label.setStyleSheet("min-width: 80px; font-weight: bold;")
        self._permission_labels[perm_type] = status_label
        row_layout.addWidget(status_label)
        
        # 权限请求按钮
        request_btn = QPushButton("请求权限")
        request_btn.setMaximumWidth(80)
        request_btn.clicked.connect(lambda: self._request_permission(perm_type))
        self._permission_buttons[perm_type] = request_btn
        row_layout.addWidget(request_btn)
        
        layout.addLayout(row_layout)
    
    def _refresh_permissions(self):
        """刷新权限状态"""
        if not permission_manager.is_supported():
            return
            
        try:
            performance_logger.info("开始刷新权限状态")
            permissions = permission_manager.check_all_permissions()
            
            for perm_type, status in permissions.items():
                if perm_type in self._permission_labels:
                    status_text = get_permission_status_text(status)
                    self._permission_labels[perm_type].setText(status_text)
                    
                    # 根据状态设置颜色
                    if status == PermissionStatus.GRANTED:
                        self._permission_labels[perm_type].setStyleSheet(
                            "color: green; font-weight: bold; min-width: 80px;"
                        )
                        # 隐藏请求按钮
                        if perm_type in self._permission_buttons:
                            self._permission_buttons[perm_type].setVisible(False)
                    elif status == PermissionStatus.DENIED:
                        self._permission_labels[perm_type].setStyleSheet(
                            "color: red; font-weight: bold; min-width: 80px;"
                        )
                        # 显示请求按钮
                        if perm_type in self._permission_buttons:
                            self._permission_buttons[perm_type].setVisible(True)
                    else:
                        self._permission_labels[perm_type].setStyleSheet(
                            "color: orange; font-weight: bold; min-width: 80px;"
                        )
                        # 显示请求按钮
                        if perm_type in self._permission_buttons:
                            self._permission_buttons[perm_type].setVisible(True)
            
            performance_logger.info("权限状态刷新完成")
            
        except Exception as e:
            performance_logger.error(f"刷新权限状态失败: {e}")
            QMessageBox.warning(self, "错误", f"刷新权限状态失败: {e}")
    
    def _request_permission(self, perm_type: PermissionType):
        """请求特定权限"""
        try:
            performance_logger.info(f"请求权限: {get_permission_name(perm_type)}")
            
            success = False
            
            if perm_type == PermissionType.ACCESSIBILITY:
                success = permission_manager.request_accessibility_permission()
                if success:
                    QMessageBox.information(
                        self, "权限请求", 
                        "辅助功能权限请求已发送。\n"
                        "请在弹出的系统对话框中点击'打开系统偏好设置'，\n"
                        "然后在辅助功能列表中勾选 ArtaleKey。"
                    )
                else:
                    QMessageBox.information(
                        self, "权限设置", 
                        "请手动打开：\n"
                        "系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能\n"
                        "然后添加 ArtaleKey 到允许列表。"
                    )
                    
            elif perm_type == PermissionType.INPUT_MONITORING:
                success = permission_manager.open_input_monitoring_settings()
                QMessageBox.information(
                    self, "权限设置", 
                    "请在打开的系统偏好设置中：\n"
                    "在'输入监控'列表中勾选 ArtaleKey。\n"
                    "设置完成后请重启应用。"
                )
                
            elif perm_type == PermissionType.SCREEN_CAPTURE:
                success = permission_manager.request_screen_capture_permission()
                if success:
                    QMessageBox.information(
                        self, "权限请求", 
                        "屏幕录制权限请求已发送。\n"
                        "请在弹出的系统对话框中点击'允许'。"
                    )
                else:
                    QMessageBox.information(
                        self, "权限设置", 
                        "请手动打开：\n"
                        "系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制\n"
                        "然后添加 ArtaleKey 到允许列表。"
                    )
            
            # 延迟刷新权限状态
            QTimer.singleShot(2000, self._refresh_permissions)
            
        except Exception as e:
            performance_logger.error(f"请求权限失败: {e}")
            QMessageBox.critical(self, "错误", f"请求权限失败: {e}")
    
    def _open_privacy_settings(self):
        """打开隐私设置"""
        try:
            if permission_manager.open_privacy_settings():
                QMessageBox.information(
                    self, "设置指南", 
                    "已打开隐私设置页面。\n\n"
                    "请在以下位置添加 ArtaleKey：\n"
                    "• 辅助功能 - 用于快捷键监听\n"
                    "• 输入监控 - 用于全局快捷键\n"
                    "• 屏幕录制 - 用于截图和OCR\n\n"
                    "设置完成后请重启应用。"
                )
            else:
                QMessageBox.warning(self, "错误", "无法打开隐私设置页面")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开隐私设置失败: {e}")
    
    def _start_permission_timer(self):
        """启动权限检查定时器"""
        if self._permission_timer is None:
            self._permission_timer = QTimer()
            self._permission_timer.timeout.connect(self._refresh_permissions)
            # 每30秒检查一次权限状态
            self._permission_timer.start(30000)
    
    def _create_llm_config_group(self):
        """创建LLM API配置组"""
        llm_group = QGroupBox("LLM API 配置")
        llm_layout = QVBoxLayout(llm_group)
        
        # API 密钥输入
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("OpenRouter API 密钥:"))
        
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("请输入您的 OpenRouter API 密钥")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)  # 密码模式隐藏输入
        api_key_layout.addWidget(self._api_key_input)
        
        # 显示/隐藏密钥按钮
        self._show_api_key_btn = QPushButton("显示")
        self._show_api_key_btn.setMaximumWidth(60)
        self._show_api_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_key_layout.addWidget(self._show_api_key_btn)
        
        llm_layout.addLayout(api_key_layout)
        
        # 保存按钮和状态
        api_key_control_layout = QHBoxLayout()
        
        self._save_api_key_btn = QPushButton("保存 API 密钥")
        self._save_api_key_btn.clicked.connect(self._save_api_key)
        api_key_control_layout.addWidget(self._save_api_key_btn)
        
        self._api_key_status_label = QLabel("未配置")
        self._api_key_status_label.setStyleSheet("color: gray; font-weight: bold;")
        api_key_control_layout.addWidget(self._api_key_status_label)
        
        api_key_control_layout.addStretch()
        llm_layout.addLayout(api_key_control_layout)
        
        # API 信息说明
        info_label = QLabel(
            "• 获取 API 密钥：访问 <a href='https://openrouter.ai/'>OpenRouter</a> 注册并获取密钥<br>"
            "• 使用模型：qwen/qwen2.5-vl-72b-instruct:free (免费)<br>"
            "• 密钥将安全存储在本地配置文件中"
        )
        info_label.setOpenExternalLinks(True)
        info_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        info_label.setWordWrap(True)
        llm_layout.addWidget(info_label)
        
        self.main_layout.addWidget(llm_group)
    
    def _create_target_app_group(self):
        """创建目标应用设置组"""
        # 简化的目标应用选择器
        self._target_selector = SimpleTargetSelector()
        self._target_selector.window_filter_enabled.connect(self._on_window_filter_enabled)
        self._target_selector.target_app_changed.connect(self._on_target_app_changed)
        
        self.main_layout.addWidget(self._target_selector)
    
    def _create_data_management_group(self):
        """创建数据管理组"""
        data_group = QGroupBox("数据管理")
        data_layout = QVBoxLayout(data_group)
        
        # 截图保存配置
        screenshot_layout = QHBoxLayout()
        screenshot_layout.addWidget(QLabel("保存截图:"))
        
        self._save_screenshots_checkbox = QCheckBox("启用截图保存")
        self._save_screenshots_checkbox.setChecked(True)  # 默认启用
        self._save_screenshots_checkbox.stateChanged.connect(self._on_save_screenshots_changed)
        screenshot_layout.addWidget(self._save_screenshots_checkbox)
        
        screenshot_layout.addStretch()
        data_layout.addLayout(screenshot_layout)
        
        # 第一行按钮：数据操作
        data_operation_layout = QHBoxLayout()
        
        self._cleanup_old_data_btn = QPushButton("清理30天前数据")
        self._cleanup_old_data_btn.clicked.connect(self._cleanup_old_data)
        data_operation_layout.addWidget(self._cleanup_old_data_btn)
        
        self._export_data_btn = QPushButton("导出数据")
        self._export_data_btn.clicked.connect(self._export_data)
        data_operation_layout.addWidget(self._export_data_btn)
        
        data_operation_layout.addStretch()
        data_layout.addLayout(data_operation_layout)
        
        # 第二行按钮：文件夹操作
        folder_operation_layout = QHBoxLayout()
        
        self._open_data_dir_btn = QPushButton("打开数据目录")
        self._open_data_dir_btn.clicked.connect(self._open_data_directory)
        folder_operation_layout.addWidget(self._open_data_dir_btn)
        
        folder_operation_layout.addStretch()
        data_layout.addLayout(folder_operation_layout)
        
        self.main_layout.addWidget(data_group)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            'api_key': self._api_key_input.text().strip() if self._api_key_input else '',
            'target_app': self._target_selector.get_target_app() if self._target_selector else 'MapleStory Worlds',
            'window_filter_enabled': self._target_selector.is_filter_enabled() if self._target_selector else True,
            'save_screenshots': self._save_screenshots_checkbox.isChecked() if hasattr(self, '_save_screenshots_checkbox') else True
        }
    
    def _load_config_to_ui(self):
        """加载配置到UI组件"""
        # 设置LLM配置
        api_key = config_manager.get('llm', 'api_key')
        if self._api_key_input:
            self._api_key_input.setText(api_key)
        
        # 更新API密钥状态
        self._update_api_key_status()
        
        # 设置窗口过滤配置
        if self._target_selector:
            window_filter_enabled = config_manager.get('window_filter', 'enabled')
            target_app = config_manager.get('window_filter', 'target_app')
            self._target_selector.set_filter_enabled(window_filter_enabled)
            self._target_selector.set_target_app(target_app)
        
        # 设置截图保存配置
        if hasattr(self, '_save_screenshots_checkbox'):
            save_screenshots = config_manager.get('screenshot_ocr', 'save_screenshots')
            self._save_screenshots_checkbox.setChecked(save_screenshots)
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置 - 兼容性方法"""
        # 为了保持兼容性，直接调用加载方法
        self._load_config_to_ui()
    
    def _toggle_api_key_visibility(self):
        """切换 API 密钥显示/隐藏"""
        if self._api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_api_key_btn.setText("隐藏")
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_api_key_btn.setText("显示")
    
    def _save_api_key(self):
        """保存 API 密钥"""
        api_key = self._api_key_input.text().strip()
        
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
            config_manager.set('llm', 'api_key', api_key)
            
            performance_logger.info("API 密钥已保存到配置文件")
            
            # 更新状态显示
            self._update_api_key_status()
            
            # 发射信号
            self.api_key_updated.emit(api_key)
            self.emit_config_changed()
            self.emit_status_changed("API 密钥已保存")
            
            QMessageBox.information(self, "成功", "API 密钥已保存并成功配置")
            performance_logger.info("用户保存 API 密钥操作完成")
            
        except Exception as e:
            error_msg = f"保存 API 密钥失败: {e}"
            QMessageBox.critical(self, "错误", error_msg)
            performance_logger.error(error_msg)
    
    def _update_api_key_status(self):
        """更新 API 密钥状态显示"""
        try:
            api_key = config_manager.get('llm', 'api_key')
            
            performance_logger.info(f"更新 API 密钥状态 - 密钥长度: {len(api_key) if api_key else 0}")
            
            if api_key:
                # 隐藏密钥，只显示前4位和后4位
                if len(api_key) > 8:
                    masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
                else:
                    masked_key = "*" * len(api_key)
                
                self._api_key_status_label.setText(f"已配置: {masked_key}")
                self._api_key_status_label.setStyleSheet("color: green; font-weight: bold;")
                
                # 在输入框中显示当前密钥
                if self._api_key_input:
                    self._api_key_input.setText(api_key)
            else:
                self._api_key_status_label.setText("未配置")
                self._api_key_status_label.setStyleSheet("color: gray; font-weight: bold;")
                if self._api_key_input:
                    self._api_key_input.clear()
                performance_logger.info("API 密钥未配置")
                
        except Exception as e:
            performance_logger.error(f"更新 API 密钥状态失败: {e}")
            self._api_key_status_label.setText("状态错误")
            self._api_key_status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            from artalekey.core.database import game_db
            deleted_count = game_db.delete_old_data(30)
            QMessageBox.information(self, "数据清理", f"已删除 {deleted_count} 条30天前的数据")
            self.emit_status_changed(f"已清理 {deleted_count} 条旧数据")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据清理失败: {e}")
    
    def _export_data(self):
        """导出数据到JSON文件"""
        try:
            from artalekey.core.database import get_app_data_dir, game_db
            
            # 获取所有数据
            data = game_db.get_data_history(1000)  # 最多导出1000条
            
            # 使用应用数据目录而不是当前工作目录
            export_path = os.path.join(
                get_app_data_dir(), 
                f'export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(self, "数据导出", f"数据已导出到: {export_path}")
            self.emit_status_changed(f"数据已导出到: {export_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"数据导出失败: {e}")
    
    def _open_data_directory(self):
        """打开数据目录"""
        try:
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
            
            self.emit_status_changed(f"已打开数据目录: {data_dir}")
            
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "错误", f"无法打开数据目录: {e}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开数据目录失败: {e}")
    
    def _on_window_filter_enabled(self, enabled: bool):
        """窗口过滤启用状态变更处理"""
        config_manager.set('window_filter', 'enabled', enabled)
        self.window_filter_enabled.emit(enabled)
        self.emit_config_changed()
        self.emit_status_changed(f"窗口过滤功能{'已启用' if enabled else '已禁用'}")
    
    def _on_target_app_changed(self, target_app: str):
        """目标应用变更处理"""
        config_manager.set('window_filter', 'target_app', target_app)
        self.target_app_changed.emit(target_app)
        self.emit_config_changed()
        self.emit_status_changed(f"目标应用已更改为: {target_app}")
    
    def get_api_key(self) -> str:
        """获取API密钥"""
        return self._api_key_input.text().strip() if self._api_key_input else ''
    
    def get_target_app(self) -> str:
        """获取目标应用"""
        return self._target_selector.get_target_app() if self._target_selector else 'MapleStory Worlds'
    
    def is_window_filter_enabled(self) -> bool:
        """检查窗口过滤是否启用"""
        return self._target_selector.is_filter_enabled() if self._target_selector else True
    
    def get_permissions_status(self) -> Dict[PermissionType, PermissionStatus]:
        """获取权限状态"""
        if permission_manager.is_supported():
            return permission_manager.check_all_permissions()
        return {}
    
    def _on_save_screenshots_changed(self, state):
        """截图保存配置变更处理"""
        try:
            # 直接设置配置
            config_manager.set('screenshot_ocr', 'save_screenshots', bool(state))
            
            # 发送状态变更信号
            self.emit_config_changed()
            self.emit_status_changed(f"截图保存功能{'已启用' if state else '已禁用'}")
            
        except Exception as e:
            performance_logger.error(f"更新截图保存配置失败: {e}")
            QMessageBox.warning(self, "错误", f"更新截图保存配置失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止权限检查定时器
        if self._permission_timer:
            self._permission_timer.stop()
            self._permission_timer = None
        super().closeEvent(event) if hasattr(super(), 'closeEvent') else None 