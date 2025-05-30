from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
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
        super().__init__("settings", parent)
        
    def init_ui(self):
        """初始化UI"""
        # LLM API 配置组
        self._create_llm_config_group()
        
        # 目标应用设置组
        self._create_target_app_group()
        
        # 数据管理组
        self._create_data_management_group()
        
        # 添加弹性空间
        self.main_layout.addStretch()
    
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
        config = {
            'llm': {
                'api_key': self._api_key_input.text().strip() if self._api_key_input else ''
            },
            'window_filter': {
                'enabled': self._target_selector.is_filter_enabled() if self._target_selector else True,
                'target_app': self._target_selector.get_target_app() if self._target_selector else 'MapleStory Worlds'
            }
        }
        return config
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        # 设置LLM配置
        llm_config = config.get('llm', {})
        if self._api_key_input and 'api_key' in llm_config:
            self._api_key_input.setText(llm_config['api_key'])
        
        # 更新API密钥状态
        self._update_api_key_status()
        
        # 设置窗口过滤配置
        window_filter_config = config.get('window_filter', {})
        if self._target_selector:
            self._target_selector.set_filter_enabled(window_filter_config.get('enabled', True))
            target_app = window_filter_config.get('target_app', 'MapleStory Worlds')
            if target_app:
                self._target_selector.set_target_app(target_app)
    
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
            llm_config = config_manager.get('llm', {})
            llm_config['api_key'] = api_key
            config_manager.set('llm', llm_config)
            
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
            llm_config = config_manager.get('llm', {})
            api_key = llm_config.get('api_key', '')
            
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
        self.window_filter_enabled.emit(enabled)
        self.emit_config_changed()
        self.emit_status_changed(f"窗口过滤功能{'已启用' if enabled else '已禁用'}")
    
    def _on_target_app_changed(self, target_app: str):
        """目标应用变更处理"""
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