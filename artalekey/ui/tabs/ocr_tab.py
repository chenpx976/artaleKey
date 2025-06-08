from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import pyqtSignal
from typing import Dict, Any
from datetime import datetime
import pytz

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.ui.components import OCRHotkeyCard
from artalekey.ui.qt_chart_widget import QtVisualizationWidget
from artalekey.core.database import game_db
from artalekey.core.logger import performance_logger


class OCRTab(BaseTab):
    """OCR识别功能标签页"""
    
    # 特定信号
    ocr_config_changed = pyqtSignal(dict)  # OCR配置变更信号
    
    def __init__(self, parent=None):
        self._ocr_card = None
        self._visualization_widget = None
        super().__init__("ocr", parent)
        
        # OCR标签页内容比较多，但调整为更合理的尺寸
        self.set_content_minimum_size(650, 1200)  # 进一步增加高度，确保所有内容都能完整显示
        
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
        
        # 最新游戏数据组（从窗口状态组件移过来）
        game_data_group = QGroupBox("最新游戏数据")
        game_data_layout = QVBoxLayout(game_data_group)
        
        # 游戏数据显示
        self.game_data_label = QLabel("暂无数据")
        self.game_data_label.setStyleSheet("""
            QLabel {
                padding: 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                font-family: 'SF Pro Display', 'Microsoft YaHei', monospace;
                font-size: 13px;
                line-height: 1.6;
                color: #2c3e50;
                min-height: 80px;
            }
        """)
        game_data_layout.addWidget(self.game_data_label)
        
        # 数据统计
        self.stats_label = QLabel("数据库统计: 加载中...")
        self.stats_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                padding: 8px;
                background-color: rgba(108, 117, 125, 0.1);
                border-radius: 4px;
                border: 1px solid #e9ecef;
            }
        """)
        game_data_layout.addWidget(self.stats_label)
        
        self.main_layout.addWidget(game_data_group)
        
        # 可视化组（合并到OCR标签页）
        visualization_group = QGroupBox("游戏数据可视化")
        visualization_layout = QVBoxLayout(visualization_group)
        
        # 可视化组件
        self._visualization_widget = QtVisualizationWidget()
        # 设置可视化组件的最小高度，防止被压缩
        self._visualization_widget.setMinimumHeight(600)  # 进一步增加高度
        # 设置可视化组件的大小策略
        self._visualization_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        visualization_layout.addWidget(self._visualization_widget)
        
        self.main_layout.addWidget(visualization_group)
        
        # 初始化游戏数据显示
        self._update_game_data()
        
        # 添加弹性空间
        self.main_layout.addStretch()
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._ocr_card.get_config() if self._ocr_card else {}
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        if self._ocr_card:
            self._ocr_card.set_config(config)
    
    def update_ocr_status(self, status_type: str, message: str = "", game_data: Dict = None):
        """更新OCR状态显示 - 简化版，主要状态显示已移至主窗口状态栏"""
        if status_type == "success" and game_data:
            # 刷新可视化数据
            self.refresh_visualization_data()
    
    def _on_ocr_config_changed(self, config: dict):
        """OCR配置变更处理"""
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
    
    def refresh_visualization_data(self):
        """刷新可视化数据"""
        if self._visualization_widget:
            self._visualization_widget.refresh_data()
            self.emit_status_changed("可视化数据已刷新")
        
        # 同时刷新游戏数据显示
        self._update_game_data()
    
    def get_visualization_widget(self):
        """获取可视化组件"""
        return self._visualization_widget 

    def _update_game_data(self):
        """更新游戏数据显示"""
        try:
            # 设置北京时区
            beijing_tz = pytz.timezone('Asia/Shanghai')
            
            # 获取最新数据
            latest_data = game_db.get_latest_data()
            if latest_data:
                level = latest_data.get('level', '未知')
                experience = latest_data.get('experience', '未知')
                money = latest_data.get('money', '未知')
                created_at = latest_data.get('created_at', '未知')
                
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
                
                # 获取角色名称和地图信息
                character_name = latest_data.get('character_name', '未知')
                current_map = latest_data.get('map_name', '未知')
                
                # 获取药水数量
                hp_potion_count = latest_data.get('hp_potion_count', '未知')
                mp_potion_count = latest_data.get('mp_potion_count', '未知')
                
                # 格式化药水显示
                hp_potion_text = str(hp_potion_count) if hp_potion_count is not None else "未知"
                mp_potion_text = str(mp_potion_count) if mp_potion_count is not None else "未知"
                
                # 时间转换
                beijing_time = self._convert_utc_to_beijing(created_at)
                
                # 使用更美观的格式，添加图标
                data_text = f"""🎮 等级: {level}
⚡ 经验: {exp_text}
💰 金钱: {money_text}
👤 角色: {character_name}
🗺️ 地图: {current_map}
🧪 HP药水: {hp_potion_text}
🔮 MP药水: {mp_potion_text}
🕒 更新: {beijing_time}"""
                
                self.game_data_label.setText(data_text)
                
            else:
                self.game_data_label.setText("📭 暂无游戏数据\n\n请使用OCR功能获取游戏数据")
            
            # 获取统计信息
            stats = game_db.get_statistics()
            if stats:
                total_records = stats.get('total_records', 0)
                max_level = stats.get('max_level', '未知')
                stats_text = f"📊 总记录数: {total_records} | 🏆 最高等级: {max_level}"
                self.stats_label.setText(stats_text)
            else:
                self.stats_label.setText("📊 数据库统计: 暂无数据")
                
        except Exception as e:
            performance_logger.error(f"更新游戏数据失败: {e}")
            self.game_data_label.setText(f"❌ 数据加载失败\n\n{str(e)}")
            self.stats_label.setText("📊 数据库统计: 加载失败")
    
    def _convert_utc_to_beijing(self, utc_time_str: str) -> str:
        """将UTC时间字符串转换为北京时间字符串"""
        try:
            beijing_tz = pytz.timezone('Asia/Shanghai')
            # 解析UTC时间
            utc_dt = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
            
            # 添加UTC时区信息
            utc_tz = pytz.timezone('UTC')
            utc_dt = utc_tz.localize(utc_dt)
            
            # 转换为北京时间
            beijing_dt = utc_dt.astimezone(beijing_tz)
            
            # 返回格式化的北京时间
            return beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            # 如果转换失败，返回原始时间
            performance_logger.warning(f"时间转换失败: {e}")
            return utc_time_str
    
 