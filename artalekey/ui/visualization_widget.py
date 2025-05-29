from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import QTimer, pyqtSignal, QSettings
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np
import pytz

from artalekey.core.database import game_db
from artalekey.core.logger import performance_logger

class VisualizationWidget(QWidget):
    """经验获取效率可视化组件"""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings('ArtaleKey', 'VisualizationWidget')
        # 设置北京时区
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        self._setup_matplotlib()
        self.init_ui()
        # 移除自动定时刷新，改为事件驱动
        # self.setup_auto_refresh()
        # 延迟刷新，让界面先显示
        QTimer.singleShot(2000, self.refresh_data)  # 2秒后刷新一次
    
    def _setup_matplotlib(self):
        """设置matplotlib中文字体"""
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        # 限制最大tick数量，避免性能问题
        plt.rcParams['axes.formatter.limits'] = [-5, 6]
        plt.rcParams['figure.max_open_warning'] = 0  # 禁用最大打开图形警告
    
    def _convert_to_beijing_time(self, time_str: str) -> datetime:
        """将数据库时间字符串转换为北京时间"""
        try:
            # 解析数据库时间
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            
            # 数据库存储的是UTC时间，需要转换为北京时间
            utc_tz = pytz.timezone('UTC')
            utc_dt = utc_tz.localize(dt)
            
            # 转换为北京时间
            beijing_dt = utc_dt.astimezone(self.beijing_tz)
            
            return beijing_dt
        except Exception as e:
            performance_logger.error(f"时间转换失败: {e}")
            # 如果转换失败，直接假设是北京时间
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            return self.beijing_tz.localize(dt)
    
    def _format_time_hms(self, time_str: str) -> str:
        """格式化时间为时分秒格式"""
        try:
            beijing_dt = self._convert_to_beijing_time(time_str)
            return beijing_dt.strftime('%H:%M:%S')
        except Exception as e:
            performance_logger.error(f"时间格式化失败: {e}")
            return time_str
    
    def _format_interval(self, total_seconds: int) -> str:
        """格式化时间间隔为分钟和秒"""
        if total_seconds < 60:
            return f"{total_seconds}秒"
        
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        if minutes < 60:
            if seconds == 0:
                return f"{minutes}分钟"
            else:
                return f"{minutes}分{seconds}秒"
        else:
            hours = minutes // 60
            remaining_minutes = minutes % 60
            
            if remaining_minutes == 0 and seconds == 0:
                return f"{hours}小时"
            elif seconds == 0:
                return f"{hours}小时{remaining_minutes}分钟"
            else:
                return f"{hours}小时{remaining_minutes}分{seconds}秒"
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 控制面板
        control_group = self._create_control_panel()
        layout.addWidget(control_group)
        
        # 经验趋势图
        chart_group = self._create_chart_panel()
        layout.addWidget(chart_group, stretch=2)
        
        # 经验增长统计表
        stats_group = self._create_stats_panel()
        layout.addWidget(stats_group, stretch=1)
    
    def _create_control_panel(self) -> QGroupBox:
        """创建控制面板"""
        group = QGroupBox("控制面板")
        layout = QHBoxLayout(group)
        
        # 等级过滤
        layout.addWidget(QLabel("等级过滤:"))
        self.level_combo = QComboBox()
        self.level_combo.addItem("全部等级", None)
        self.level_combo.currentIndexChanged.connect(self.on_level_filter_changed)
        layout.addWidget(self.level_combo)
        
        # 时间范围
        layout.addWidget(QLabel("时间范围:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["最近1小时", "最近6小时", "最近12小时", "最近24小时"])
        self.time_range_combo.setCurrentText("最近6小时")
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        layout.addWidget(self.time_range_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_btn)
        
        layout.addStretch()
        
        return group
    
    def _create_chart_panel(self) -> QGroupBox:
        """创建图表面板"""
        group = QGroupBox("经验增长趋势")
        layout = QVBoxLayout(group)
        
        # 创建matplotlib图表
        self.figure = Figure(figsize=(12, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 状态标签
        self.chart_status_label = QLabel("正在加载图表数据...")
        self.chart_status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.chart_status_label)
        
        return group
    
    def _create_stats_panel(self) -> QGroupBox:
        """创建统计面板"""
        group = QGroupBox("经验增长记录")
        layout = QVBoxLayout(group)
        
        # 创建表格
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(7)  # 调整为7列
        self.stats_table.setHorizontalHeaderLabels([
            "起始时间", "结束时间", "间隔时间", "经验增长", "等级", "预估十分钟", "结束经验值"
        ])
        
        # 设置表格样式
        header = self.stats_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.stats_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.stats_table)
        
        # 统计状态标签
        self.stats_status_label = QLabel("正在加载统计数据...")
        self.stats_status_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.stats_status_label)
        
        return group
    
    def get_time_range_hours(self) -> int:
        """获取选择的时间范围（小时）"""
        text = self.time_range_combo.currentText()
        if "1小时" in text:
            return 1
        elif "6小时" in text:
            return 6
        elif "12小时" in text:
            return 12
        elif "24小时" in text:
            return 24
        return 6
    
    def get_selected_level(self):
        """获取选择的等级过滤"""
        return self.level_combo.currentData()
    
    def save_selected_level(self, level):
        """保存选择的等级"""
        self.settings.setValue('selected_level', level)
    
    def load_selected_level(self):
        """加载保存的等级选择"""
        return self.settings.value('selected_level', None)
    
    def refresh_data(self):
        """刷新数据"""
        try:
            performance_logger.info("开始刷新可视化数据")
            
            # 更新等级下拉框
            self._update_level_combo()
            
            # 刷新图表
            self.refresh_chart()
            
            # 刷新统计表
            self.refresh_stats_table()
            
            self.refresh_requested.emit()
            
        except Exception as e:
            performance_logger.error(f"刷新可视化数据失败: {e}")
    
    def _update_level_combo(self):
        """更新等级下拉框"""
        try:
            # 获取所有存在的等级
            data = game_db.get_data_history(1000)
            levels = set()
            for record in data:
                level = record.get('level')
                if level and isinstance(level, int) and level > 0:
                    levels.add(level)
            
            # 保存当前选择
            current_level = self.get_selected_level()
            if current_level is None:
                # 尝试加载保存的等级选择
                current_level = self.load_selected_level()
            
            # 清空并重新填充
            self.level_combo.clear()
            self.level_combo.addItem("全部等级", None)
            
            for level in sorted(levels):
                self.level_combo.addItem(f"等级 {level}", level)
            
            # 恢复选择
            if current_level is not None:
                index = self.level_combo.findData(current_level)
                if index >= 0:
                    self.level_combo.setCurrentIndex(index)
                else:
                    # 如果保存的等级不存在，清除保存的设置
                    self.settings.remove('selected_level')
            
        except Exception as e:
            performance_logger.error(f"更新等级下拉框失败: {e}")
    
    def refresh_chart(self):
        """刷新经验趋势图"""
        try:
            self.chart_status_label.setText("正在加载图表数据...")
            
            # 获取数据
            hours_limit = self.get_time_range_hours()
            level_filter = self.get_selected_level()
            
            data = game_db.get_experience_data_for_visualization(
                level_filter=level_filter,
                hours_limit=hours_limit
            )
            
            # 清空图表
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            if not data:
                ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', transform=ax.transAxes, 
                       fontsize=16, color='gray')
                self.chart_status_label.setText("暂无数据显示")
                self.canvas.draw()
                return
            
            # 准备数据
            times = []
            exp_values = []
            exp_percentages = []
            levels = []
            
            for record in data:
                try:
                    # 解析时间
                    time_str = record['created_at']
                    dt = self._convert_to_beijing_time(time_str)
                    times.append(dt)
                    
                    # 解析经验
                    experience = record['experience']
                    if isinstance(experience, dict):
                        exp_values.append(experience.get('value', 0))
                        exp_percentages.append(experience.get('percentage', 0))
                    else:
                        exp_values.append(0)
                        exp_percentages.append(0)
                    
                    levels.append(record.get('level', 0))
                    
                except Exception as e:
                    performance_logger.warning(f"解析记录失败: {e}")
                    continue
            
            if not times:
                ax.text(0.5, 0.5, '数据解析失败', ha='center', va='center', transform=ax.transAxes,
                       fontsize=16, color='red')
                self.chart_status_label.setText("数据解析失败")
                self.canvas.draw()
                return
            
            # 绘制经验值趋势
            ax.plot(times, exp_values, 'b-', linewidth=2, marker='o', markersize=4, 
                   label=f'经验值 (共{len(exp_values)}个数据点)')
            
            # 设置x轴格式和范围
            if times:
                # 设置x轴范围，减少空白
                start_time = min(times)
                end_time = max(times)
                time_span = end_time - start_time
                
                # 检查时间跨度，避免生成过多tick
                total_seconds = time_span.total_seconds()
                
                # 当只有很少数据点或时间跨度很小时，使用固定刻度
                if len(times) <= 3 or total_seconds < 300:  # 少于3个数据点或5分钟
                    # 使用手动设置刻度，避免matplotlib自动生成过多tick
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    # 只显示数据点对应的时间
                    ax.set_xticks(times)
                    # 禁用小刻度
                    ax.xaxis.set_minor_locator(plt.NullLocator())
                    # 强制限制最大tick数量
                    ax.xaxis.set_major_locator(MaxNLocator(nbins=min(5, len(times)), prune='both'))
                    # 设置合理的x轴范围
                    if total_seconds > 0:
                        margin = max(timedelta(minutes=10), time_span * 0.2)
                    else:
                        margin = timedelta(minutes=30)
                    ax.set_xlim(start_time - margin, end_time + margin)
                elif total_seconds < 60:  # 少于1分钟的跨度
                    # 只显示几个点，不设置复杂的时间格式
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                    # 限制最多5个主要刻度
                    ax.xaxis.set_major_locator(mdates.SecondLocator(interval=max(1, int(total_seconds / 5))))
                    # 禁用小刻度
                    ax.xaxis.set_minor_locator(plt.NullLocator())
                    # 强制限制最大tick数量
                    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, prune='both'))
                elif total_seconds < 3600:  # 少于1小时的跨度
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    # 根据分钟数设置合理的间隔
                    interval_minutes = max(1, int(total_seconds / 300))  # 最多5个刻度
                    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=interval_minutes))
                    # 禁用小刻度
                    ax.xaxis.set_minor_locator(plt.NullLocator())
                    # 强制限制最大tick数量
                    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
                elif hours_limit <= 6:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    # 限制小时刻度的数量
                    interval_hours = max(1, int(total_seconds / 3600 / 6))  # 最多6个刻度
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=interval_hours))
                    # 禁用小刻度
                    ax.xaxis.set_minor_locator(plt.NullLocator())
                    # 强制限制最大tick数量
                    ax.xaxis.set_major_locator(MaxNLocator(nbins=6, prune='both'))
                else:
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                    # 限制刻度数量
                    interval_hours = max(1, int(total_seconds / 3600 / 8))  # 最多8个刻度
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=interval_hours))
                    # 禁用小刻度
                    ax.xaxis.set_minor_locator(plt.NullLocator())
                    # 强制限制最大tick数量
                    ax.xaxis.set_major_locator(MaxNLocator(nbins=8, prune='both'))
                
                # 为其他情况设置x轴范围
                if len(times) > 3 and total_seconds >= 300:
                    # 添加少量边距（5%的时间跨度）
                    if total_seconds > 0:
                        margin = time_span * 0.05
                        ax.set_xlim(start_time - margin, end_time + margin)
                    else:
                        # 如果只有一个数据点，设置固定的边距
                        margin = timedelta(minutes=30)
                        ax.set_xlim(start_time - margin, start_time + margin)
            
            # 设置y轴格式，让数值更易读
            if exp_values:
                min_exp = min(exp_values)
                max_exp = max(exp_values)
                exp_range = max_exp - min_exp
                
                # 如果经验值变化不大，设置合适的y轴范围
                if exp_range > 0:
                    margin_y = exp_range * 0.1  # 10%的边距
                    ax.set_ylim(min_exp - margin_y, max_exp + margin_y)
                
                # 格式化y轴标签，使用千分位分隔符
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
            
            # 设置标题和标签
            level_text = f"等级{level_filter}" if level_filter else "全部等级"
            ax.set_title(f'经验增长趋势 - {level_text} (最近{hours_limit}小时)', fontsize=14, fontweight='bold')
            ax.set_xlabel('时间', fontsize=12)
            ax.set_ylabel('经验值', fontsize=12)
            ax.legend(loc='upper left')
            
            # 优化网格样式
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            ax.set_facecolor('#fafafa')  # 设置浅灰色背景
            
            # 旋转x轴标签并优化间距
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 调整布局，减少边距
            self.figure.tight_layout(pad=1.0)
            
            # 更新状态
            if exp_values:
                min_exp = min(exp_values)
                max_exp = max(exp_values)
                exp_gain = max_exp - min_exp
                self.chart_status_label.setText(
                    f"数据点: {len(exp_values)}, 经验增长: {exp_gain:,}, "
                    f"最低: {min_exp:,}, 最高: {max_exp:,}"
                )
            else:
                self.chart_status_label.setText("无有效数据")
            
            self.canvas.draw()
            
        except Exception as e:
            performance_logger.error(f"刷新图表失败: {e}")
            self.chart_status_label.setText(f"图表加载失败: {e}")
    
    def refresh_stats_table(self):
        """刷新经验增长统计表格"""
        try:
            self.stats_status_label.setText("正在加载统计数据...")
            
            # 获取指定等级的经验增长记录
            level_filter = self.get_selected_level()
            exp_growth_data = self._get_exp_growth_data(level_filter)
            
            # 设置表格行数
            self.stats_table.setRowCount(len(exp_growth_data))
            
            if not exp_growth_data:
                self.stats_status_label.setText("暂无经验增长数据")
                return
            
            # 填充数据
            for row, growth in enumerate(exp_growth_data):
                # 起始时间
                start_time = self._format_time_hms(growth['start_time'])
                self.stats_table.setItem(row, 0, QTableWidgetItem(start_time))
                
                # 结束时间
                end_time = self._format_time_hms(growth['end_time'])
                self.stats_table.setItem(row, 1, QTableWidgetItem(end_time))
                
                # 间隔时间
                interval = self._format_interval(growth['interval_seconds'])
                self.stats_table.setItem(row, 2, QTableWidgetItem(interval))
                
                # 经验增长
                exp_gain = f"{growth['exp_gain']:,}"
                self.stats_table.setItem(row, 3, QTableWidgetItem(exp_gain))
                
                # 等级
                level = f"{growth['level']}"
                self.stats_table.setItem(row, 4, QTableWidgetItem(level))
                
                # 预估十分钟
                avg_exp_per_minute = growth['exp_gain'] / (growth['interval_seconds'] / 60)
                estimated_ten_minutes_exp = avg_exp_per_minute * 10
                estimated_exp_value = f"{estimated_ten_minutes_exp:,.0f}"
                self.stats_table.setItem(row, 5, QTableWidgetItem(estimated_exp_value))
                
                # 结束经验值
                end_exp_value = f"{growth['end_exp_value']:,}"
                self.stats_table.setItem(row, 6, QTableWidgetItem(end_exp_value))
            
            # 自动调整列宽
            self.stats_table.resizeColumnsToContents()
            
            # 更新状态
            total_exp_gain = sum(growth['exp_gain'] for growth in exp_growth_data)
            avg_interval = sum(growth['interval_seconds'] for growth in exp_growth_data) / len(exp_growth_data)
            level_text = f"等级{level_filter}" if level_filter else "全等级"
            self.stats_status_label.setText(
                f"{level_text}增长记录: {len(exp_growth_data)}条, 总经验增长: {total_exp_gain:,}, "
                f"平均间隔: {self._format_interval(avg_interval)}"
            )
            
        except Exception as e:
            performance_logger.error(f"刷新统计表格失败: {e}")
            self.stats_status_label.setText(f"统计数据加载失败: {e}")
    
    def _get_exp_growth_data(self, level_filter=None):
        """获取经验增长数据"""
        try:
            # 从数据库获取数据
            data = game_db.get_data_history(1000)
            
            if not data:
                return []
            
            # 过滤数据：只保留有经验数据的记录
            valid_records = []
            for record in data:
                level = record.get('level')
                experience = record.get('experience')
                
                # 检查等级过滤
                if level_filter is not None and level != level_filter:
                    continue
                
                # 检查数据有效性
                if (level and isinstance(level, int) and level > 0 and 
                    experience and isinstance(experience, dict) and 
                    experience.get('value', 0) > 0):
                    valid_records.append(record)
            
            if not valid_records:
                return []
            
            # 按时间排序（最旧的在前）
            valid_records.sort(key=lambda x: x['created_at'])
            
            growth_records = []
            
            # 如果没有等级过滤器，按等级分组处理
            if level_filter is None:
                # 按等级分组
                level_groups = {}
                for record in valid_records:
                    level = record['level']
                    if level not in level_groups:
                        level_groups[level] = []
                    level_groups[level].append(record)
                
                # 对每个等级分组计算增长
                for level, records in level_groups.items():
                    records.sort(key=lambda x: x['created_at'])
                    growth_records.extend(self._calculate_growth_for_level(records, level))
            else:
                # 有等级过滤器，直接计算该等级的增长
                growth_records = self._calculate_growth_for_level(valid_records, level_filter)
            
            # 按结束时间排序，最新的在前面
            growth_records.sort(key=lambda x: x['end_time'], reverse=True)
            
            return growth_records[:50]  # 只返回最近50条记录
            
        except Exception as e:
            performance_logger.error(f"获取经验增长数据失败: {e}")
            return []
    
    def _calculate_growth_for_level(self, records, level):
        """计算单个等级的经验增长记录"""
        growth_records = []
        
        # 计算相邻两个记录之间的经验增长
        for i in range(1, len(records)):
            prev_record = records[i-1]
            curr_record = records[i]
            
            try:
                # 解析经验数据
                prev_exp = prev_record.get('experience', {})
                curr_exp = curr_record.get('experience', {})
                
                prev_value = prev_exp.get('value', 0)
                curr_value = curr_exp.get('value', 0)
                
                # 只有当经验值确实增加时才记录
                if curr_value > prev_value:
                    exp_gain = curr_value - prev_value
                    
                    # 计算时间间隔
                    start_time = self._convert_to_beijing_time(prev_record['created_at'])
                    end_time = self._convert_to_beijing_time(curr_record['created_at'])
                    interval_seconds = int((end_time - start_time).total_seconds())
                    
                    # 只记录合理的时间间隔（1秒到24小时之间）
                    if 1 <= interval_seconds <= 86400:
                        growth_record = {
                            'start_time': prev_record['created_at'],
                            'end_time': curr_record['created_at'],
                            'interval_seconds': interval_seconds,
                            'exp_gain': exp_gain,
                            'level': level,
                            'end_exp_value': curr_value
                        }
                        growth_records.append(growth_record)
                        
                        performance_logger.debug(f"记录经验增长: 等级{level}, 从{prev_value:,}增长到{curr_value:,}, 增长{exp_gain:,}, 间隔{interval_seconds}秒")
                
            except Exception as e:
                performance_logger.warning(f"处理经验增长记录失败: {e}")
                continue
        
        return growth_records
    
    def on_level_filter_changed(self):
        """等级过滤变更"""
        # 保存选择的等级
        selected_level = self.get_selected_level()
        self.save_selected_level(selected_level)
        
        # 刷新图表和统计
        self.refresh_chart()
        self.refresh_stats_table()
    
    def on_time_range_changed(self):
        """时间范围变更"""
        self.refresh_chart()
    
    def closeEvent(self, event):
        """关闭事件"""
        event.accept() 