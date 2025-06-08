from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal
from typing import Dict, Any


class MultiLineStatusWidget(QWidget):
    """多行状态显示组件"""
    
    # 信号定义
    activate_window_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window_status_label = None
        self.ocr_status_label = None
        self.game_data_label = None
        self.activate_button = None
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(3)
        
        # 第一行：窗口状态 + 激活按钮
        first_row = QHBoxLayout()
        first_row.setContentsMargins(0, 0, 0, 0)
        
        self.window_status_label = QLabel("窗口状态: 检测中...")
        self.window_status_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        first_row.addWidget(self.window_status_label)
        
        first_row.addStretch()
        
        self.activate_button = QPushButton("激活窗口")
        self.activate_button.clicked.connect(self.activate_window_requested.emit)
        self.activate_button.setMaximumWidth(80)
        self.activate_button.setMaximumHeight(24)
        self.activate_button.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 4px;
                background-color: #007ACC;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005999;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #CCCCCC;
            }
        """)
        first_row.addWidget(self.activate_button)
        
        layout.addLayout(first_row)
        
        # 第二行：OCR状态
        self.ocr_status_label = QLabel("OCR状态: 未初始化")
        self.ocr_status_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.ocr_status_label)
        
        # 第三行：游戏数据摘要（新增）
        self.game_data_label = QLabel("游戏数据: 暂无数据")
        self.game_data_label.setStyleSheet("color: white; font-size: 12px; font-family: monospace;")
        layout.addWidget(self.game_data_label)
        
        # 设置整体样式
        self.setStyleSheet("""
            MultiLineStatusWidget {
                border-top: 1px solid #555555;
                background-color: #2b2b2b;
            }
        """)
    
    def update_window_status(self, is_active: bool, is_found: bool = True):
        """更新窗口状态"""
        if is_active:
            self.window_status_label.setText("窗口状态: ✅ MapleStory Worlds 已激活")
            self.window_status_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 13px;")
            self.activate_button.setEnabled(False)
        else:
            if is_found:
                self.window_status_label.setText("窗口状态: ⚠️ MapleStory Worlds 未激活")
                self.window_status_label.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 13px;")
                self.activate_button.setEnabled(True)
            else:
                self.window_status_label.setText("窗口状态: ❌ MapleStory Worlds 未运行")
                self.window_status_label.setStyleSheet("color: #F44336; font-weight: bold; font-size: 13px;")
                self.activate_button.setEnabled(False)
    
    def update_ocr_status(self, status_text: str, status_type: str = "info"):
        """更新OCR状态"""
        color_map = {
            "info": "#FFFFFF",
            "success": "#4CAF50", 
            "error": "#F44336",
            "warning": "#FF9800",
            "processing": "#2196F3"
        }
        color = color_map.get(status_type, "#FFFFFF")
        
        self.ocr_status_label.setText(f"OCR状态: {status_text}")
        self.ocr_status_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")
    
    def update_game_data(self, game_data: Dict[str, Any] = None):
        """更新游戏数据摘要显示"""
        if not game_data:
            self.game_data_label.setText("游戏数据: 暂无数据")
            self.game_data_label.setStyleSheet("color: #BBBBBB; font-size: 12px; font-family: monospace;")
            return
        
        # 提取关键信息
        level = game_data.get('level', '?')
        character_name = game_data.get('character_name', '未知')
        character_class = game_data.get('character_class', '未知')
        map_name = game_data.get('map_name', '未知')
        
        # 格式化经验
        experience = game_data.get('experience', {})
        if isinstance(experience, dict):
            exp_value = experience.get('value', 0)
            exp_percentage = experience.get('percentage', 0)
            exp_text = f"{exp_value:,}({exp_percentage:.1f}%)"
        else:
            exp_text = str(experience) if experience else "未知"
        
        # 格式化金钱
        money = game_data.get('money')
        if money is not None:
            if isinstance(money, (int, float)):
                money_text = f"{money:,}"
            else:
                money_text = str(money)
        else:
            money_text = "未知"
        
        # 格式化HP/MP
        max_hp = game_data.get('max_hp', '?')
        max_mp = game_data.get('max_mp', '?')
        
        # 格式化药水数量
        hp_potion = game_data.get('hp_potion_count', '?')
        mp_potion = game_data.get('mp_potion_count', '?')
        
        # 构建显示文本 - 包含更多信息
        data_parts = [
            f"👤{character_name}({character_class})",
            f"⭐Lv.{level}",
            f"⚡{exp_text}",
            f"💰{money_text}",
            f"❤️{max_hp}",
            f"💙{max_mp}",
            f"🧪{hp_potion}/{mp_potion}",
            f"🗺️{map_name}"
        ]
        
        # 限制地图名称长度，避免状态栏过长
        if len(map_name) > 12:
            data_parts[-1] = f"🗺️{map_name[:12]}..."
        
        data_text = " | ".join(data_parts)
        
        self.game_data_label.setText(f"游戏数据: {data_text}")
        self.game_data_label.setStyleSheet("color: #E8F5E8; font-size: 12px; font-family: monospace; font-weight: bold;")
    
    def clear_game_data(self):
        """清空游戏数据显示"""
        self.update_game_data(None) 