from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from artalekey.core.window_status import window_status_monitor
from artalekey.core.database import game_db

class WindowStatusWidget(QWidget):
    """窗口状态显示组件"""
    
    # 信号定义
    activate_window_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
        
        # 启动窗口状态监控
        window_status_monitor.start_monitoring()
        
        # 初始状态更新
        self._update_window_status(False)
        self._update_window_found(False)
        self._update_game_data()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 窗口状态组
        status_group = QGroupBox("MapleStory Worlds 状态")
        status_layout = QVBoxLayout(status_group)
        
        # 窗口状态行
        window_status_layout = QHBoxLayout()
        
        # 状态标签
        self.status_label = QLabel("窗口状态: 未知")
        self.status_label.setFont(QFont("", 12, QFont.Weight.Bold))
        window_status_layout.addWidget(self.status_label)
        
        # 激活按钮
        self.activate_button = QPushButton("激活窗口")
        self.activate_button.clicked.connect(self._on_activate_clicked)
        self.activate_button.setMaximumWidth(100)
        window_status_layout.addWidget(self.activate_button)
        
        window_status_layout.addStretch()
        status_layout.addLayout(window_status_layout)
        
        # 详细状态信息
        self.detail_label = QLabel("检测中...")
        self.detail_label.setStyleSheet("color: gray; font-size: 10px;")
        status_layout.addWidget(self.detail_label)
        
        layout.addWidget(status_group)
        
        # 游戏数据组
        data_group = QGroupBox("最新游戏数据")
        data_layout = QVBoxLayout(data_group)
        
        # 游戏数据显示
        self.game_data_label = QLabel("暂无数据")
        self.game_data_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                border: 1px solid lightgray;
                border-radius: 4px;
                background-color: #000000;
                font-family: monospace;
            }
        """)
        data_layout.addWidget(self.game_data_label)
        
        # 数据统计
        self.stats_label = QLabel("数据库统计: 加载中...")
        self.stats_label.setStyleSheet("color: gray; font-size: 10px;")
        data_layout.addWidget(self.stats_label)
        
        layout.addWidget(data_group)
        
        # 设置整体样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid lightgray;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def _connect_signals(self):
        """连接信号"""
        window_status_monitor.window_status_changed.connect(self._update_window_status)
        window_status_monitor.window_found_changed.connect(self._update_window_found)
    
    def _update_window_status(self, is_active: bool):
        """更新窗口激活状态"""
        if is_active:
            self.status_label.setText("窗口状态: ✅ 已激活")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.activate_button.setEnabled(False)
            self.detail_label.setText("MapleStory Worlds 窗口当前处于激活状态")
        else:
            if window_status_monitor.is_window_found():
                self.status_label.setText("窗口状态: ⚠️ 未激活")
                self.status_label.setStyleSheet("color: orange; font-weight: bold;")
                self.activate_button.setEnabled(True)
                self.detail_label.setText("MapleStory Worlds 正在运行但未激活")
            else:
                self.status_label.setText("窗口状态: ❌ 未运行")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                self.activate_button.setEnabled(False)
                self.detail_label.setText("MapleStory Worlds 未运行")
    
    def _update_window_found(self, is_found: bool):
        """更新窗口存在状态"""
        # 当窗口存在状态变化时，重新更新激活状态显示
        self._update_window_status(window_status_monitor.is_window_active())
    
    def _update_game_data(self):
        """更新游戏数据显示"""
        try:
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
                
                data_text = f"""等级: {level}
经验: {exp_text}
金钱: {money_text}
更新时间: {created_at}"""
                
                self.game_data_label.setText(data_text)
            else:
                self.game_data_label.setText("暂无游戏数据")
            
            # 获取统计信息
            stats = game_db.get_statistics()
            if stats:
                total_records = stats.get('total_records', 0)
                max_level = stats.get('max_level', '未知')
                stats_text = f"总记录数: {total_records}, 最高等级: {max_level}"
                self.stats_label.setText(f"数据库统计: {stats_text}")
            else:
                self.stats_label.setText("数据库统计: 暂无数据")
                
        except Exception as e:
            self.game_data_label.setText(f"数据加载失败: {e}")
            self.stats_label.setText("数据库统计: 加载失败")
    
    def _on_activate_clicked(self):
        """激活窗口按钮点击"""
        window_status_monitor.activate_target_window()
        self.activate_window_requested.emit()
    
    def refresh_data(self):
        """刷新数据显示"""
        self._update_game_data()
    
    def closeEvent(self, event):
        """关闭事件"""
        window_status_monitor.stop_monitoring()
        super().closeEvent(event) 