from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QComboBox, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
from PyQt6.QtCore import QTimer, pyqtSignal, QSettings, QDateTime, Qt, QMargins
from PyQt6.QtGui import QFont, QPainter, QBrush, QColor
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pytz

from artalekey.core.database import game_db
from artalekey.core.logger import performance_logger

class QtVisualizationWidget(QWidget):
    """Qt原生图表的经验获取效率可视化组件"""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings('ArtaleKey', 'QtVisualizationWidget')
        # 设置北京时区
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 添加防重复刷新机制
        self._refreshing = False
        self._refresh_timer = QTimer()
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._delayed_refresh)
        
        self.init_ui()
        # 延迟刷新，让界面先显示
        QTimer.singleShot(1000, self.refresh_data)  # 1秒后刷新一次
    
    def _convert_to_beijing_time(self, time_str: str) -> datetime:
        """将数据库时间字符串转换为北京时间"""
        try:
            # 首先尝试解析timestamp格式：20250530_004227
            if '_' in time_str and len(time_str) == 15:
                dt = datetime.strptime(time_str, '%Y%m%d_%H%M%S')
                # timestamp格式通常是本地时间，直接作为北京时间
                return self.beijing_tz.localize(dt)
            
            # 然后尝试解析数据库created_at格式：2025-05-30 00:42:27
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            
            # 数据库存储的是UTC时间，需要转换为北京时间
            utc_tz = pytz.timezone('UTC')
            utc_dt = utc_tz.localize(dt)
            
            # 转换为北京时间
            beijing_dt = utc_dt.astimezone(self.beijing_tz)
            
            return beijing_dt
        except Exception as e:
            performance_logger.error(f"时间转换失败: {e}, 时间字符串: {time_str}")
            # 如果转换失败，尝试直接解析为本地时间
            try:
                if '_' in time_str:
                    dt = datetime.strptime(time_str, '%Y%m%d_%H%M%S')
                else:
                    dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                return self.beijing_tz.localize(dt)
            except:
                # 最后的回退：返回当前时间
                return datetime.now(self.beijing_tz)
    
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
        
        # 控制面板 - 固定高度
        control_group = self._create_control_panel()
        control_group.setMaximumHeight(80)  # 限制控制面板高度
        layout.addWidget(control_group, 0)  # stretch=0，不拉伸
         
        # 经验增长统计表 - 次要显示区域
        stats_group = self._create_stats_panel()
        layout.addWidget(stats_group, 2)  # stretch=2，次要拉伸区域
        # Qt Charts图表 - 主要显示区域
        chart_group = self._create_qt_chart_panel()
        layout.addWidget(chart_group, 3)  # stretch=3，主要拉伸区域
       
    
    def _create_control_panel(self) -> QGroupBox:
        """创建控制面板"""
        group = QGroupBox("控制面板")
        layout = QHBoxLayout(group)
        
        # 角色筛选
        layout.addWidget(QLabel("角色筛选:"))
        self.character_combo = QComboBox()
        self.character_combo.addItem("全部角色", None)
        self.character_combo.currentIndexChanged.connect(self.on_character_filter_changed)
        layout.addWidget(self.character_combo)
        
        # 等级过滤
        layout.addWidget(QLabel("等级过滤:"))
        self.level_combo = QComboBox()
        self.level_combo.addItem("全部等级", None)
        self.level_combo.currentIndexChanged.connect(self.on_level_filter_changed)
        layout.addWidget(self.level_combo)
        
        # 时间范围
        layout.addWidget(QLabel("时间范围:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["最近1小时", "最近6小时", "最近12小时", "最近24小时", "最近3天", "最近7天"])
        self.time_range_combo.setCurrentText("最近24小时")
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        layout.addWidget(self.time_range_combo)
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(self.refresh_btn)
        
        layout.addStretch()
        
        return group
    
    def _create_qt_chart_panel(self) -> QGroupBox:
        """创建Qt Charts图表面板"""
        group = QGroupBox("经验增长趋势 (Qt原生)")
        layout = QVBoxLayout(group)
        
        # 创建图表
        self.chart = QChart()
        self.chart.setTitle("经验增长趋势")
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # 设置图表样式 - 使用正确的API方法名
        self.chart.setBackgroundBrush(QBrush(QColor(255, 255, 255)))  # 白色背景
        self.chart.setPlotAreaBackgroundBrush(QBrush(QColor(250, 250, 250)))  # 浅灰色绘图区背景
        self.chart.setPlotAreaBackgroundVisible(True)
        
        # 创建图表视图
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 关键：设置图表视图的大小策略，确保能够正确拉伸
        self.chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 设置图表视图的最小高度，确保有足够显示空间
        self.chart_view.setMinimumHeight(300)  # 增加最小高度
        
        layout.addWidget(self.chart_view)
        
        # 状态标签 - 固定高度
        self.chart_status_label = QLabel("正在加载图表数据...")
        self.chart_status_label.setStyleSheet("color: gray; font-style: italic;")
        self.chart_status_label.setMaximumHeight(25)  # 限制状态标签高度
        self.chart_status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.chart_status_label)
        
        return group
    
    def _create_stats_panel(self) -> QGroupBox:
        """创建统计面板"""
        group = QGroupBox("经验增长记录")
        layout = QVBoxLayout(group)
        
        # 创建表格
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(7)
        self.stats_table.setHorizontalHeaderLabels([
            "起始时间", "结束时间", "间隔时间", "经验增长", "等级", "预估十分钟", "结束经验值"
        ])
        
        # 关键：设置表格的大小策略，让它能够正确拉伸
        self.stats_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 设置表格样式
        header = self.stats_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.stats_table.setAlternatingRowColors(True)
        
        # 设置表格的最小高度，确保能显示足够的数据行
        self.stats_table.setMinimumHeight(200)  # 增加最小高度
        
        # 设置垂直滚动条策略，确保内容可滚动
        self.stats_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.stats_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 设置行高调整模式
        self.stats_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.stats_table)
        
        # 统计状态标签 - 固定高度
        self.stats_status_label = QLabel("正在加载统计数据...")
        self.stats_status_label.setStyleSheet("color: gray; font-style: italic;")
        self.stats_status_label.setMaximumHeight(25)  # 限制状态标签高度，避免占用太多空间
        self.stats_status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
        elif "3天" in text:
            return 72
        elif "7天" in text:
            return 168
        return 24
    
    def get_selected_character(self):
        """获取选择的角色过滤"""
        return self.character_combo.currentData()
    
    def get_selected_level(self):
        """获取选择的等级过滤"""
        return self.level_combo.currentData()
    
    def refresh_data(self):
        """刷新数据"""
        if self._refreshing:
            performance_logger.debug("正在刷新中，跳过重复刷新请求")
            return
        
        self._refresh_timer.start(200)
    
    def _delayed_refresh(self):
        """延迟刷新执行"""
        if self._refreshing:
            return
        
        self._refreshing = True
        try:
            self._update_character_combo()
            self._update_level_combo()
            self.refresh_qt_chart()
            self.refresh_stats_table()
        finally:
            self._refreshing = False
    
    def _update_character_combo(self):
        """更新角色下拉框"""
        try:
            current_selection = self.get_selected_character()
            self.character_combo.clear()
            self.character_combo.addItem("全部角色", None)
            
            characters = game_db.get_unique_characters()
            for character in characters:
                self.character_combo.addItem(character, character)
            
            # 恢复之前的选择
            if current_selection:
                for i in range(self.character_combo.count()):
                    if self.character_combo.itemData(i) == current_selection:
                        self.character_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            performance_logger.error(f"更新角色下拉框失败: {e}")
    
    def _update_level_combo(self):
        """更新等级下拉框"""
        try:
            current_selection = self.get_selected_level()
            self.level_combo.clear()
            self.level_combo.addItem("全部等级", None)
            
            levels = game_db.get_unique_levels()
            for level in sorted(levels):
                self.level_combo.addItem(f"等级 {level}", level)
            
            # 恢复之前的选择
            if current_selection:
                for i in range(self.level_combo.count()):
                    if self.level_combo.itemData(i) == current_selection:
                        self.level_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            performance_logger.error(f"更新等级下拉框失败: {e}")
    
    def refresh_qt_chart(self):
        """刷新Qt Charts图表"""
        try:
            self.chart_status_label.setText("正在加载图表数据...")
            
            # 获取数据
            hours_limit = self.get_time_range_hours()
            level_filter = self.get_selected_level()
            character_filter = self.get_selected_character()
            
            data = self._get_filtered_visualization_data(
                character_filter=character_filter,
                level_filter=level_filter,
                hours_limit=hours_limit
            )
            
            performance_logger.debug(f"Qt图表获取到 {len(data)} 条数据")
            
            # 清空现有系列和坐标轴
            self.chart.removeAllSeries()
            # 移除所有坐标轴，防止出现重复的Y轴
            for axis in self.chart.axes():
                self.chart.removeAxis(axis)
            
            if not data:
                self.chart.setTitle("")  # 移除标题
                self.chart_status_label.setText("暂无数据显示")
                return
            
            # 创建数据系列
            series = QLineSeries()
            series.setName("经验值")
            
            # 设置线条样式
            pen = series.pen()
            pen.setWidth(3)  # 设置线条宽度
            series.setPen(pen)
            
            # 设置数据点样式
            series.setPointsVisible(True)  # 显示数据点
            series.setPointLabelsVisible(False)  # 不显示数据点标签，避免过于拥挤
            
            # 准备数据
            valid_data = []
            for record in data:
                try:
                    # 解析时间和经验值 - 使用created_at而不是timestamp进行图表绘制
                    created_at_str = record.get('created_at', '')
                    experience_data = record.get('experience', {})
                    
                    if isinstance(experience_data, str):
                        import json
                        experience_data = json.loads(experience_data)
                    
                    exp_value = experience_data.get('value')
                    if exp_value is not None and created_at_str:
                        # 转换时间为QDateTime
                        beijing_dt = self._convert_to_beijing_time(created_at_str)
                        qdatetime = QDateTime.fromString(beijing_dt.strftime('%Y-%m-%d %H:%M:%S'), 'yyyy-MM-dd hh:mm:ss')
                        
                        if qdatetime.isValid():
                            timestamp_ms = qdatetime.toMSecsSinceEpoch()
                            valid_data.append((timestamp_ms, exp_value))
                
                except Exception as e:
                    performance_logger.warning(f"解析数据点失败: {e}")
                    continue
            
            if not valid_data:
                self.chart.setTitle("")  # 移除标题
                self.chart_status_label.setText("数据解析失败")
                return
            
            # 按时间排序
            valid_data.sort(key=lambda x: x[0])
            
            # 添加数据点到系列
            for timestamp_ms, exp_value in valid_data:
                series.append(timestamp_ms, exp_value)
            
            # 添加系列到图表
            self.chart.addSeries(series)
            
            # 设置图表样式 - 移除标题，扩大绘图区域
            self.chart.setTitle("")  # 移除标题
            self.chart.legend().setVisible(False)  # 隐藏图例
            # 使用QMargins对象而不是set
            self.chart.setMargins(QMargins(0, 0, 0, 0))  # 移除边距
            
            # 设置坐标轴
            if len(valid_data) > 1:
                # X轴 - 时间轴（显示轴线但不显示标签）
                axis_x = QDateTimeAxis()
                axis_x.setLabelsVisible(False)  # 隐藏X轴标签
                axis_x.setTitleText("")  # 移除X轴标题
                
                min_time = min(valid_data, key=lambda x: x[0])[0]
                max_time = max(valid_data, key=lambda x: x[0])[0]
                
                axis_x.setMin(QDateTime.fromMSecsSinceEpoch(min_time))
                axis_x.setMax(QDateTime.fromMSecsSinceEpoch(max_time))
                
                self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                
                # Y轴 - 经验值轴（只显示最大值和最小值）
                axis_y = QValueAxis()
                axis_y.setTitleText("")  # 移除Y轴标题
                
                min_exp = min(valid_data, key=lambda x: x[1])[1]
                max_exp = max(valid_data, key=lambda x: x[1])[1]
                exp_range = max_exp - min_exp
                
                if exp_range > 0:
                    margin = exp_range * 0.05  # 减少边距
                    axis_y.setMin(min_exp - margin)
                    axis_y.setMax(max_exp + margin)
                else:
                    axis_y.setMin(min_exp - 1000)
                    axis_y.setMax(max_exp + 1000)
                
                # 设置Y轴只显示最大值和最小值
                axis_y.setTickCount(2)  # 只显示2个刻度：最大值和最小值
                axis_y.setLabelFormat("%.0f")  # 整数格式
                
                # 设置Y轴样式
                axis_y.setGridLineVisible(False)  # 隐藏网格线
                axis_y.setMinorTickCount(0)  # 不显示小刻度
                
                self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
            
            # 更新状态
            exp_values = [item[1] for item in valid_data]
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
                
            performance_logger.info("Qt图表刷新完成")
            
        except Exception as e:
            performance_logger.error(f"刷新Qt图表失败: {e}")
            self.chart_status_label.setText(f"图表加载失败: {e}")
            self.chart.setTitle("")
    
    def _get_filtered_visualization_data(self, character_filter=None, level_filter=None, hours_limit=24):
        """获取带角色和等级过滤的可视化数据"""
        try:
            # 获取原始数据
            data = game_db.get_data_history(1000)
            performance_logger.debug(f"📊 从数据库获取 {len(data)} 条原始数据")
            
            if not data:
                performance_logger.info("📊 数据库无数据")
                return []
            
            # 过滤数据
            filtered_data = []
            # 确保当前时间有时区信息，使用北京时区
            current_time = datetime.now(self.beijing_tz)
            
            for record in data:
                try:
                    # 时间过滤 - 使用created_at字段而不是timestamp字段
                    created_at_str = record.get('created_at', '')
                    if created_at_str:
                        record_time = self._convert_to_beijing_time(created_at_str)
                        # 确保record_time也有时区信息
                        if record_time.tzinfo is None:
                            record_time = self.beijing_tz.localize(record_time)
                        
                        time_diff = (current_time - record_time).total_seconds()
                        if time_diff > hours_limit * 3600:
                            continue
                    
                    # 角色过滤
                    if character_filter:
                        character_name = record.get('character_name', '')
                        if character_name != character_filter:
                            continue
                    
                    # 等级过滤
                    if level_filter:
                        level = record.get('level')
                        if level != level_filter:
                            continue
                    
                    # 经验值过滤
                    experience_data = record.get('experience', {})
                    if isinstance(experience_data, str):
                        import json
                        experience_data = json.loads(experience_data)
                    
                    exp_value = experience_data.get('value')
                    if exp_value is None or exp_value <= 0:
                        continue
                    
                    filtered_data.append(record)
                    
                except Exception as e:
                    performance_logger.warning(f"过滤数据记录失败: {e}")
                    continue
            
            performance_logger.info(f"📊 过滤后获得 {len(filtered_data)} 条有效数据")
            return filtered_data
            
        except Exception as e:
            performance_logger.error(f"获取可视化数据失败: {e}")
            return []
    
    def refresh_stats_table(self):
        """刷新经验增长统计表格"""
        try:
            self.stats_status_label.setText("正在加载统计数据...")
            
            # 获取指定角色和等级的经验增长记录
            character_filter = self.get_selected_character()
            level_filter = self.get_selected_level()
            exp_growth_data = self._get_exp_growth_data(character_filter, level_filter)
            
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
            character_text = character_filter if character_filter else "全角色"
            level_text = f"等级{level_filter}" if level_filter else "全等级"
            self.stats_status_label.setText(
                f"{character_text} {level_text}增长记录: {len(exp_growth_data)}条, 总经验增长: {total_exp_gain:,}, "
                f"平均间隔: {self._format_interval(avg_interval)}"
            )
            
        except Exception as e:
            performance_logger.error(f"刷新统计表格失败: {e}")
            self.stats_status_label.setText(f"统计数据加载失败: {e}")
    
    def _get_exp_growth_data(self, character_filter=None, level_filter=None):
        """获取经验增长数据"""
        try:
            # 从数据库获取数据
            data = game_db.get_data_history(1000)
            
            if not data:
                return []
            
            # 过滤数据：只保留有经验数据的记录
            valid_records = []
            for record in data:
                # 角色过滤
                if character_filter is not None:
                    character_name = record.get('character_name')
                    if character_name != character_filter:
                        continue
                
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
    
    def on_character_filter_changed(self):
        """角色筛选变更"""
        self.refresh_data()
    
    def on_level_filter_changed(self):
        """等级筛选变更"""
        self.refresh_data()
    
    def on_time_range_changed(self):
        """时间范围变更"""
        self.refresh_data() 