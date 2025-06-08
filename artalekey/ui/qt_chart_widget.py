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
        
        # 延迟初始化：先获取最新数据设置过滤条件，再刷新数据
        QTimer.singleShot(500, self._init_with_latest_data)  # 0.5秒后初始化
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
        
        # 地图过滤 (新增)
        layout.addWidget(QLabel("地图过滤:"))
        self.map_combo = QComboBox()
        self.map_combo.addItem("全部地图", None)
        self.map_combo.currentIndexChanged.connect(self.on_map_filter_changed)
        layout.addWidget(self.map_combo)
        
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
        
        # 创建表格 - 增加更多有用的列
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(11)  # 从10列增加到11列
        self.stats_table.setHorizontalHeaderLabels([
            "起始时间", "结束时间", "间隔时间", "经验增长", "等级", 
            "地图地点", "预估十分钟", "时段", "结束经验值", "十分钟HP药水用量", "十分钟MP药水用量"
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
    
    def get_selected_map(self):
        """获取选择的地图过滤"""
        return self.map_combo.currentData()
    
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
            self._update_map_combo()
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
    
    def _update_map_combo(self):
        """更新地图下拉框"""
        try:
            current_selection = self.get_selected_map()
            self.map_combo.clear()
            self.map_combo.addItem("全部地图", None)
            
            maps = game_db.get_unique_maps()
            for map_name in maps:
                if map_name and map_name.strip():  # 过滤空地图名
                    self.map_combo.addItem(map_name, map_name)
            
            # 恢复之前的选择
            if current_selection:
                for i in range(self.map_combo.count()):
                    if self.map_combo.itemData(i) == current_selection:
                        self.map_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            performance_logger.error(f"更新地图下拉框失败: {e}")
    
    def refresh_qt_chart(self):
        """刷新Qt Charts图表"""
        try:
            self.chart_status_label.setText("正在加载图表数据...")
            
            # 获取数据
            hours_limit = self.get_time_range_hours()
            level_filter = self.get_selected_level()
            character_filter = self.get_selected_character()
            map_filter = self.get_selected_map()
            
            data = self._get_filtered_visualization_data(
                character_filter=character_filter,
                level_filter=level_filter,
                map_filter=map_filter,
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
    
    def _get_filtered_visualization_data(self, character_filter=None, level_filter=None, map_filter=None, hours_limit=24):
        """获取带角色、等级和地图过滤的可视化数据"""
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
                    
                    # 地图过滤 (新增)
                    if map_filter:
                        map_name = record.get('map_name', '')
                        if map_name != map_filter:
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
            
            # 获取指定角色、等级和地图的经验增长记录
            character_filter = self.get_selected_character()
            level_filter = self.get_selected_level()
            map_filter = self.get_selected_map()
            exp_growth_data = self._get_exp_growth_data(character_filter, level_filter, map_filter)
            
            # 设置表格行数
            self.stats_table.setRowCount(len(exp_growth_data))
            
            if not exp_growth_data:
                self.stats_status_label.setText("暂无经验增长数据")
                return
            
            # 填充数据
            for row, growth in enumerate(exp_growth_data):
                is_completed = growth.get('is_completed', True)
                
                # 起始时间
                start_time = self._format_time_hms(growth['start_time'])
                start_item = QTableWidgetItem(start_time)
                start_item.setToolTip(f"起始时间: {start_time}")
                self.stats_table.setItem(row, 0, start_item)
                
                # 结束时间
                if is_completed and growth['end_time']:
                    end_time = self._format_time_hms(growth['end_time'])
                    end_item = QTableWidgetItem(end_time)
                    end_item.setToolTip(f"结束时间: {end_time}")
                else:
                    end_item = QTableWidgetItem("进行中...")
                    end_item.setToolTip("当前正在进行的记录")
                    end_item.setBackground(QColor(173, 216, 230))  # 浅蓝色
                self.stats_table.setItem(row, 1, end_item)
                
                # 间隔时间
                if is_completed and growth['interval_seconds']:
                    interval = self._format_interval(growth['interval_seconds'])
                    interval_item = QTableWidgetItem(interval)
                    interval_item.setToolTip(f"间隔: {interval} ({growth['interval_seconds']}秒)")
                else:
                    interval_item = QTableWidgetItem("-")
                    interval_item.setToolTip("进行中，暂无间隔时间")
                self.stats_table.setItem(row, 2, interval_item)
                
                # 经验增长
                if is_completed and growth['exp_gain']:
                    exp_gain = f"{growth['exp_gain']:,}"
                    exp_gain_item = QTableWidgetItem(exp_gain)
                    # 根据经验增长量设置颜色
                    if growth['exp_gain'] >= 5000:
                        exp_gain_item.setBackground(QColor(144, 238, 144))  # 浅绿色
                    elif growth['exp_gain'] >= 2000:
                        exp_gain_item.setBackground(QColor(255, 255, 224))  # 浅黄色
                else:
                    exp_gain_item = QTableWidgetItem("-")
                    exp_gain_item.setToolTip("进行中，暂无经验增长数据")
                self.stats_table.setItem(row, 3, exp_gain_item)
                
                # 等级
                level = f"{growth['level']}"
                self.stats_table.setItem(row, 4, QTableWidgetItem(level))
                
                # 地图地点
                map_name = growth.get('map_name', '未知地图')
                map_item = QTableWidgetItem(map_name)
                map_item.setToolTip(f"地图: {map_name}")
                self.stats_table.setItem(row, 5, map_item)
                
                # 预估十分钟
                if is_completed and growth['exp_gain'] and growth['interval_seconds']:
                    avg_exp_per_minute = growth['exp_gain'] / (growth['interval_seconds'] / 60)
                    estimated_ten_minutes_exp = avg_exp_per_minute * 10
                    estimated_exp_value = f"{estimated_ten_minutes_exp:,.0f}"
                    estimated_item = QTableWidgetItem(estimated_exp_value)
                else:
                    estimated_item = QTableWidgetItem("-")
                    estimated_item.setToolTip("进行中，暂无预估数据")
                self.stats_table.setItem(row, 6, estimated_item)
                
                # 时段标识
                if is_completed and growth['end_time']:
                    time_period = self._get_time_period(growth['end_time'])
                    time_period_item = QTableWidgetItem(time_period)
                    time_period_item.setToolTip(f"时间段: {time_period}")
                else:
                    start_time_period = self._get_time_period(growth['start_time'])
                    time_period_item = QTableWidgetItem(f"{start_time_period} (进行中)")
                    time_period_item.setToolTip("当前时段")
                self.stats_table.setItem(row, 7, time_period_item)
                
                # 结束经验值
                if is_completed and growth['end_exp_value']:
                    end_exp_value = f"{growth['end_exp_value']:,}"
                    end_exp_item = QTableWidgetItem(end_exp_value)
                else:
                    end_exp_item = QTableWidgetItem("-")
                    end_exp_item.setToolTip("进行中，暂无结束经验值")
                self.stats_table.setItem(row, 8, end_exp_item)
                
                # 十分钟HP药水用量
                if is_completed:
                    hp_potion_usage = self._calculate_potion_usage(growth, 'hp_potion_count')
                    hp_potion_item = QTableWidgetItem(hp_potion_usage)
                    hp_potion_item.setToolTip(f"十分钟HP药水用量: {hp_potion_usage}")
                else:
                    hp_potion_item = QTableWidgetItem("-")
                    hp_potion_item.setToolTip("进行中，暂无药水用量数据")
                self.stats_table.setItem(row, 9, hp_potion_item)
                
                # 十分钟MP药水用量
                if is_completed:
                    mp_potion_usage = self._calculate_potion_usage(growth, 'mp_potion_count')
                    mp_potion_item = QTableWidgetItem(mp_potion_usage)
                    mp_potion_item.setToolTip(f"十分钟MP药水用量: {mp_potion_usage}")
                else:
                    mp_potion_item = QTableWidgetItem("-")
                    mp_potion_item.setToolTip("进行中，暂无药水用量数据")
                self.stats_table.setItem(row, 10, mp_potion_item)
            
            # 自动调整列宽
            self.stats_table.resizeColumnsToContents()
            
            # 更新状态 - 只统计已完成的记录
            completed_records = [growth for growth in exp_growth_data if growth.get('is_completed', True)]
            in_progress_count = len(exp_growth_data) - len(completed_records)
            
            if completed_records:
                total_exp_gain = sum(growth['exp_gain'] for growth in completed_records)
                avg_interval = sum(growth['interval_seconds'] for growth in completed_records) / len(completed_records)
                
                # 计算药水用量统计
                total_hp_potion_usage = sum(self._parse_potion_usage(self._calculate_potion_usage(growth, 'hp_potion_count')) for growth in completed_records)
                total_mp_potion_usage = sum(self._parse_potion_usage(self._calculate_potion_usage(growth, 'mp_potion_count')) for growth in completed_records)
            else:
                total_exp_gain = 0
                avg_interval = 0
                total_hp_potion_usage = 0
                total_mp_potion_usage = 0
            
            character_text = character_filter if character_filter else "全角色"
            level_text = f"等级{level_filter}" if level_filter else "全等级"
            
            status_text = f"{character_text} {level_text}增长记录: {len(completed_records)}条已完成"
            if in_progress_count > 0:
                status_text += f", {in_progress_count}条进行中"
            
            if completed_records:
                status_text += f", 总经验增长: {total_exp_gain:,}, 平均间隔: {self._format_interval(avg_interval)}, 总HP药水用量: {total_hp_potion_usage:.0f}, 总MP药水用量: {total_mp_potion_usage:.0f}"
            
            self.stats_status_label.setText(status_text)
            
        except Exception as e:
            performance_logger.error(f"刷新统计表格失败: {e}")
            self.stats_status_label.setText(f"统计数据加载失败: {e}")
    
    def _calculate_potion_usage(self, growth_data: dict, potion_type: str) -> str:
        """计算十分钟药水用量"""
        try:
            start_count = growth_data.get(f'start_{potion_type}')
            end_count = growth_data.get(f'end_{potion_type}')
            interval_seconds = growth_data.get('interval_seconds', 0)
            
            performance_logger.debug(f"计算{potion_type}用量: start={start_count}, end={end_count}, interval={interval_seconds}秒")
            
            if interval_seconds <= 0:
                performance_logger.debug(f"{potion_type}用量计算失败: 时间间隔无效")
                return "N/A"
            
            # 如果药水数量数据不可用，返回N/A
            if start_count is None or end_count is None:
                performance_logger.debug(f"{potion_type}用量计算失败: 药水数量数据缺失")
                return "N/A"
            
            # 确保药水数量是数字类型
            try:
                start_count = int(start_count)
                end_count = int(end_count)
            except (ValueError, TypeError):
                performance_logger.debug(f"{potion_type}用量计算失败: 药水数量不是数字类型")
                return "N/A"
            
            # 计算药水消耗量（开始数量 - 结束数量）
            potion_used = start_count - end_count
            
            # 如果消耗量为负数（可能是补充了药水），设为0
            if potion_used < 0:
                performance_logger.debug(f"{potion_type}用量为负数({potion_used})，可能补充了药水，设为0")
                potion_used = 0
            
            # 计算十分钟用量
            minutes = interval_seconds / 60
            if minutes <= 0:
                return "N/A"
            
            ten_minute_usage = (potion_used / minutes) * 10
            
            # 向上取整
            import math
            ten_minute_usage_ceil = math.ceil(ten_minute_usage)
            
            performance_logger.debug(f"{potion_type}十分钟用量: {ten_minute_usage:.1f} -> {ten_minute_usage_ceil} (消耗{potion_used}个，用时{minutes:.1f}分钟)")
            return str(ten_minute_usage_ceil)
        
        except Exception as e:
            performance_logger.debug(f"计算药水用量失败: {e}")
            return "N/A"
    
    def _parse_potion_usage(self, usage_str: str) -> float:
        """解析药水用量字符串为数字"""
        try:
            if usage_str == "N/A":
                return 0.0
            return float(usage_str)
        except:
            return 0.0

    def _get_time_period(self, time_str: str) -> str:
        """获取时间段标识"""
        try:
            beijing_dt = self._convert_to_beijing_time(time_str)
            hour = beijing_dt.hour
            
            if 6 <= hour < 12:
                return "🌅 上午"
            elif 12 <= hour < 18:
                return "☀️ 下午"
            elif 18 <= hour < 24:
                return "🌙 晚上"
            else:
                return "🌃 深夜"
        
        except Exception:
            return "❓ 未知"
    
    def _get_exp_growth_data(self, character_filter=None, level_filter=None, map_filter=None):
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
                
                # 检查地图过滤 (新增)
                if map_filter is not None:
                    map_name = record.get('map_name')
                    if map_name != map_filter:
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
            # 处理 end_time 为 None 的情况（进行中的记录）
            def sort_key(x):
                end_time = x['end_time']
                if end_time is None:
                    # 进行中的记录使用 start_time，并且排在最前面
                    return ('9999-12-31 23:59:59', True)  # 使用一个很大的时间值确保排在前面
                else:
                    return (end_time, False)
            
            growth_records.sort(key=sort_key, reverse=True)
            
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
                    
                    # 只记录合理的时间间隔（1秒到15分钟之间）
                    if 1 <= interval_seconds <= 900:  # 15分钟 = 900秒
                        # 获取地图信息（优先使用结束时的地图）
                        map_name = curr_record.get('map_name') or prev_record.get('map_name') or '未知地图'
                        
                        # 获取药水数量
                        start_hp = prev_record.get('hp_potion_count')
                        end_hp = curr_record.get('hp_potion_count')
                        start_mp = prev_record.get('mp_potion_count')
                        end_mp = curr_record.get('mp_potion_count')
                        
                        growth_record = {
                            'start_time': prev_record['created_at'],
                            'end_time': curr_record['created_at'],
                            'interval_seconds': interval_seconds,
                            'exp_gain': exp_gain,
                            'level': level,
                            'end_exp_value': curr_value,
                            'map_name': map_name,  # 新增地图信息
                            'start_hp_potion_count': start_hp,
                            'end_hp_potion_count': end_hp,
                            'start_mp_potion_count': start_mp,
                            'end_mp_potion_count': end_mp,
                            'is_completed': True,  # 标记为已完成的记录
                        }
                        growth_records.append(growth_record)
                        
                        performance_logger.debug(f"记录经验增长: 等级{level}, 地图{map_name}, 从{prev_value:,}增长到{curr_value:,}, 增长{exp_gain:,}, 间隔{interval_seconds}秒, HP药水:{start_hp}->{end_hp}, MP药水:{start_mp}->{end_mp}")
                
            except Exception as e:
                performance_logger.warning(f"处理经验增长记录失败: {e}")
                continue
        
        # 添加最新的"进行中"记录（只有在30分钟以内的才显示）
        if records:
            latest_record = records[-1]
            latest_exp = latest_record.get('experience', {})
            latest_value = latest_exp.get('value', 0)
            
            if latest_value > 0:  # 确保有有效的经验数据
                # 检查起始时间是否在30分钟以内
                try:
                    start_time = self._convert_to_beijing_time(latest_record['created_at'])
                    current_time = datetime.now(self.beijing_tz)
                    
                    # 确保时间都有时区信息
                    if start_time.tzinfo is None:
                        start_time = self.beijing_tz.localize(start_time)
                    
                    time_diff_seconds = (current_time - start_time).total_seconds()
                    
                    # 只有在30分钟（1800秒）以内的记录才显示为进行中
                    if time_diff_seconds <= 1800:  # 30分钟 = 1800秒
                        map_name = latest_record.get('map_name', '未知地图')
                        
                        current_record = {
                            'start_time': latest_record['created_at'],
                            'end_time': None,  # 没有结束时间
                            'interval_seconds': None,  # 没有间隔时间
                            'exp_gain': None,  # 没有经验增长
                            'level': level,
                            'end_exp_value': None,  # 没有结束经验值
                            'map_name': map_name,
                            'start_hp_potion_count': latest_record.get('hp_potion_count'),
                            'end_hp_potion_count': None,
                            'start_mp_potion_count': latest_record.get('mp_potion_count'),
                            'end_mp_potion_count': None,
                            'is_completed': False,  # 标记为进行中的记录
                        }
                        growth_records.append(current_record)
                        
                        performance_logger.debug(f"添加进行中记录: 等级{level}, 地图{map_name}, 当前经验{latest_value:,}, 距离现在{time_diff_seconds:.0f}秒")
                    else:
                        performance_logger.debug(f"跳过过期的进行中记录: 等级{level}, 距离现在{time_diff_seconds:.0f}秒 (超过30分钟)")
                        
                except Exception as e:
                    performance_logger.warning(f"检查进行中记录时间失败: {e}")
                    # 如果时间检查失败，不添加进行中记录
        
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
    
    def on_map_filter_changed(self):
        """地图筛选变更"""
        self.refresh_data()
    
    def _init_with_latest_data(self):
        """使用最新数据初始化过滤条件"""
        try:
            # 获取最新游戏数据
            latest_data = game_db.get_latest_data()
            if latest_data:
                character_name = latest_data.get('character_name')
                level = latest_data.get('level')
                
                performance_logger.info(f"🎯 使用最新数据初始化过滤条件: 角色={character_name}, 等级={level}")
                
                # 更新下拉框选项
                self._update_character_combo()
                self._update_level_combo()
                
                # 自动设置角色过滤
                if character_name:
                    for i in range(self.character_combo.count()):
                        if self.character_combo.itemData(i) == character_name:
                            self.character_combo.setCurrentIndex(i)
                            performance_logger.info(f"✅ 自动设置角色过滤为: {character_name}")
                            break
                
                # 自动设置等级过滤
                if level and isinstance(level, int) and level > 0:
                    for i in range(self.level_combo.count()):
                        if self.level_combo.itemData(i) == level:
                            self.level_combo.setCurrentIndex(i)
                            performance_logger.info(f"✅ 自动设置等级过滤为: {level}")
                            break
                
                # 自动设置地图过滤（优先显示最新地图）
                map_name = latest_data.get('map_name')
                if map_name:
                    # 更新地图下拉框
                    self._update_map_combo()
                    for i in range(self.map_combo.count()):
                        if self.map_combo.itemData(i) == map_name:
                            self.map_combo.setCurrentIndex(i)
                            performance_logger.info(f"✅ 自动设置地图过滤为: {map_name}")
                            break
        
        except Exception as e:
            performance_logger.error(f"使用最新数据初始化过滤条件失败: {e}") 