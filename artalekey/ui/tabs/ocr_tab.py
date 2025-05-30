from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal
from typing import Dict, Any

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.ui.components import OCRHotkeyCard


class OCRTab(BaseTab):
    """OCR识别功能标签页"""
    
    # 特定信号
    ocr_config_changed = pyqtSignal(dict)  # OCR配置变更信号
    
    def __init__(self, parent=None):
        self._ocr_card = None
        self._ocr_status_label = None
        super().__init__("ocr", parent)
        
    def init_ui(self):
        """初始化UI"""
        # OCR配置组
        ocr_group = QGroupBox("OCR识别配置")
        ocr_layout = QVBoxLayout(ocr_group)
        
        # OCR配置组件
        self._ocr_card = OCRHotkeyCard()
        self._ocr_card.config_changed.connect(self._on_ocr_config_changed)
        ocr_layout.addWidget(self._ocr_card)
        
        self.main_layout.addWidget(ocr_group)
        
        # OCR状态组
        status_group = QGroupBox("OCR状态")
        status_layout = QVBoxLayout(status_group)
        
        # OCR状态显示
        self._ocr_status_label = QLabel("OCR功能未启用")
        self._ocr_status_label.setStyleSheet(
            "color: gray; font-weight: bold; padding: 8px; "
            "border: 1px solid lightgray; border-radius: 4px;"
        )
        status_layout.addWidget(self._ocr_status_label)
        
        self.main_layout.addWidget(status_group)
        
        # 添加弹性空间
        self.main_layout.addStretch()
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._ocr_card.get_config() if self._ocr_card else {}
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        if self._ocr_card:
            self._ocr_card.set_config(config)
        
        # 更新状态显示
        self._update_ocr_status(config)
    
    def update_ocr_status(self, status_type: str, message: str = "", game_data: Dict = None):
        """更新OCR状态显示
        
        Args:
            status_type: 状态类型 ('ready', 'processing', 'success', 'error', 'disabled')
            message: 状态消息
            game_data: 游戏数据（用于成功状态）
        """
        if status_type == "ready":
            config = self.get_config()
            self._update_ocr_status(config)
        elif status_type == "processing":
            self._ocr_status_label.setText("🔄 正在执行OCR识别...")
            self._ocr_status_label.setStyleSheet(
                "color: orange; font-weight: bold; padding: 8px; "
                "border: 1px solid orange; border-radius: 4px;"
            )
        elif status_type == "success":
            if game_data:
                level = game_data.get('level', '未知')
                experience = game_data.get('experience', '未知')
                
                # 格式化经验显示
                exp_text = "未知"
                if experience and isinstance(experience, dict):
                    exp_value = experience.get('value', 0)
                    exp_percentage = experience.get('percentage', 0)
                    exp_text = f"{exp_value:,} ({exp_percentage:.1f}%)"
                elif experience:
                    exp_text = str(experience)
                
                if level != '未知' or (experience and experience != '未知'):
                    # 识别成功
                    self._ocr_status_label.setText(f"✅ OCR识别成功 - 等级: {level}, 经验: {exp_text}")
                    self._ocr_status_label.setStyleSheet(
                        "color: green; font-weight: bold; padding: 8px; "
                        "border: 1px solid green; border-radius: 4px;"
                    )
                else:
                    # 识别失败
                    self._ocr_status_label.setText("⚠️ OCR识别完成，但未提取到有效数据")
                    self._ocr_status_label.setStyleSheet(
                        "color: orange; font-weight: bold; padding: 8px; "
                        "border: 1px solid orange; border-radius: 4px;"
                    )
            else:
                self._ocr_status_label.setText("✅ OCR识别完成")
                self._ocr_status_label.setStyleSheet(
                    "color: green; font-weight: bold; padding: 8px; "
                    "border: 1px solid green; border-radius: 4px;"
                )
        elif status_type == "error":
            self._ocr_status_label.setText(f"❌ OCR错误: {message}")
            self._ocr_status_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 8px; "
                "border: 1px solid red; border-radius: 4px;"
            )
        elif status_type == "disabled":
            self._ocr_status_label.setText("❌ OCR功能未启用，无法触发")
            self._ocr_status_label.setStyleSheet(
                "color: red; font-weight: bold; padding: 8px; "
                "border: 1px solid red; border-radius: 4px;"
            )
    
    def _update_ocr_status(self, ocr_config: Dict[str, Any]):
        """更新OCR状态显示"""
        # 如果配置为空或没有enabled字段，默认认为是启用状态
        enabled = ocr_config.get('enabled', True) if ocr_config else True
        
        if enabled:
            trigger_key = ocr_config.get('trigger_key', 'c')
            self._ocr_status_label.setText(
                f"✅ OCR功能已启用 (按 {trigger_key.upper()} 键触发)"
            )
            self._ocr_status_label.setStyleSheet(
                "color: green; font-weight: bold; padding: 8px; "
                "border: 1px solid green; border-radius: 4px;"
            )
        else:
            self._ocr_status_label.setText("❌ OCR功能未启用")
            self._ocr_status_label.setStyleSheet(
                "color: gray; font-weight: bold; padding: 8px; "
                "border: 1px solid lightgray; border-radius: 4px;"
            )
    
    def _on_ocr_config_changed(self, config: dict):
        """OCR配置变更处理"""
        self._update_ocr_status(config)
        
        # 发射信号
        self.ocr_config_changed.emit(config)
        self.emit_config_changed()
        self.emit_status_changed("OCR配置已更新")
    
    def is_enabled(self) -> bool:
        """检查OCR功能是否启用"""
        config = self.get_config()
        return config.get('enabled', True)
    
    def get_trigger_key(self) -> str:
        """获取触发按键"""
        config = self.get_config()
        return config.get('trigger_key', 'c') 