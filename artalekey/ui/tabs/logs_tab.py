"""
日志标签页 - 实时显示程序日志
"""

import logging
from datetime import datetime
from typing import Dict, Any
from collections import deque

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QLabel, QComboBox, QCheckBox, QSpinBox, QGroupBox,
    QSplitter, QFrame
)
from PyQt6.QtCore import QTimer, pyqtSignal, QThread, QMutex, QMutexLocker
from PyQt6.QtGui import QTextCursor, QFont, QColor, QTextCharFormat

from artalekey.ui.tabs.base_tab import BaseTab
from artalekey.core.logger import performance_logger


class LogHandler(logging.Handler):
    """自定义日志处理器，用于捕获日志并发送到UI"""
    
    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal
        self.mutex = QMutex()
        
    def emit(self, record):
        """发送日志记录"""
        try:
            with QMutexLocker(self.mutex):
                # 格式化日志消息
                msg = self.format(record)
                # 发送信号到UI线程
                self.log_signal.emit(record.levelno, msg, record.created)
        except Exception:
            # 避免日志处理器本身出错
            pass


class LogBuffer:
    """高性能日志缓冲区"""
    
    def __init__(self, max_size=10000):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.mutex = QMutex()
    
    def add_log(self, level, message, timestamp):
        """添加日志条目"""
        with QMutexLocker(self.mutex):
            self.buffer.append({
                'level': level,
                'message': message,
                'timestamp': timestamp,
                'formatted_time': datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]
            })
    
    def get_logs(self, count=None):
        """获取日志条目"""
        with QMutexLocker(self.mutex):
            if count is None:
                return list(self.buffer)
            else:
                return list(self.buffer)[-count:] if count > 0 else []
    
    def clear(self):
        """清空缓冲区"""
        with QMutexLocker(self.mutex):
            self.buffer.clear()
    
    def get_count(self):
        """获取日志数量"""
        with QMutexLocker(self.mutex):
            return len(self.buffer)


class LogsTab(BaseTab):
    """日志标签页"""
    
    # 日志信号
    log_received = pyqtSignal(int, str, float)  # level, message, timestamp
    
    def __init__(self, parent=None):
        # 初始化组件
        self._log_display = None
        self._level_filter = None
        self._auto_scroll_cb = None
        self._max_lines_spin = None
        self._clear_btn = None
        self._save_btn = None
        self._pause_btn = None
        self._stats_label = None
        
        # 日志相关
        self._log_buffer = LogBuffer(max_size=10000)
        self._log_handler = None
        self._update_timer = None
        self._is_paused = False
        self._pending_updates = 0
        
        # 日志级别颜色映射
        self._level_colors = {
            logging.DEBUG: QColor(128, 128, 128),      # 灰色
            logging.INFO: QColor(199, 199, 199),       # 浅灰色 (#C7C7C7)
            logging.WARNING: QColor(255, 165, 0),      # 橙色
            logging.ERROR: QColor(255, 100, 100),      # 浅红色
            logging.CRITICAL: QColor(255, 50, 50),     # 亮红色
        }
        
        # 日志级别名称映射
        self._level_names = {
            logging.DEBUG: 'DEBUG',
            logging.INFO: 'INFO',
            logging.WARNING: 'WARNING',
            logging.ERROR: 'ERROR',
            logging.CRITICAL: 'CRITICAL'
        }
        
        super().__init__("logs", parent)
        
        # 设置日志处理器
        self._setup_log_handler()
        
    def init_ui(self):
        """初始化UI"""
        # 创建控制面板
        self._create_control_panel()
        
        # 创建日志显示区域
        self._create_log_display()
        
        # 创建状态栏
        self._create_status_bar()
        
        # 设置更新定时器
        self._setup_update_timer()
        
        # 连接信号
        self._connect_signals()
    
    def _create_control_panel(self):
        """创建控制面板"""
        control_group = QGroupBox("日志控制")
        control_layout = QHBoxLayout(control_group)
        
        # 日志级别过滤
        control_layout.addWidget(QLabel("级别过滤:"))
        self._level_filter = QComboBox()
        self._level_filter.addItems(['全部', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self._level_filter.setCurrentText('全部')
        control_layout.addWidget(self._level_filter)
        
        # 分隔符
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.VLine)
        control_layout.addWidget(line1)
        
        # 自动滚动
        self._auto_scroll_cb = QCheckBox("自动滚动")
        self._auto_scroll_cb.setChecked(True)
        control_layout.addWidget(self._auto_scroll_cb)
        
        # 最大行数
        control_layout.addWidget(QLabel("最大行数:"))
        self._max_lines_spin = QSpinBox()
        self._max_lines_spin.setRange(100, 50000)
        self._max_lines_spin.setValue(5000)
        self._max_lines_spin.setSuffix(" 行")
        control_layout.addWidget(self._max_lines_spin)
        
        # 分隔符
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.VLine)
        control_layout.addWidget(line2)
        
        # 控制按钮
        self._pause_btn = QPushButton("暂停")
        self._pause_btn.setCheckable(True)
        control_layout.addWidget(self._pause_btn)
        
        self._clear_btn = QPushButton("清空")
        control_layout.addWidget(self._clear_btn)
        
        self._save_btn = QPushButton("保存日志")
        control_layout.addWidget(self._save_btn)
        
        # 测试按钮（仅在调试模式下显示）
        self._test_btn = QPushButton("生成测试日志")
        self._test_btn.clicked.connect(self._generate_test_logs)
        control_layout.addWidget(self._test_btn)
        
        control_layout.addStretch()
        
        self.main_layout.addWidget(control_group)
    
    def _create_log_display(self):
        """创建日志显示区域"""
        # 日志显示文本框
        self._log_display = QTextEdit()
        self._log_display.setReadOnly(True)
        self._log_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        
        # 设置等宽字体
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Monaco", 9)  # macOS 备用字体
        if not font.exactMatch():
            font = QFont("Courier New", 9)  # 通用备用字体
        self._log_display.setFont(font)
        
        # 设置样式
        self._log_display.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #C7C7C7;
                border: 1px solid #3e3e3e;
                selection-background-color: #264f78;
            }
        """)
        
        self.main_layout.addWidget(self._log_display)
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_layout = QHBoxLayout()
        
        self._stats_label = QLabel("日志统计: 0 条")
        self._stats_label.setStyleSheet("color: #666; font-size: 11px;")
        status_layout.addWidget(self._stats_label)
        
        status_layout.addStretch()
        
        # 性能指示器
        self._perf_label = QLabel("更新: 0 ms")
        self._perf_label.setStyleSheet("color: #666; font-size: 11px;")
        status_layout.addWidget(self._perf_label)
        
        self.main_layout.addLayout(status_layout)
    
    def _setup_update_timer(self):
        """设置更新定时器"""
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.start(100)  # 100ms 更新一次
    
    def _connect_signals(self):
        """连接信号"""
        self.log_received.connect(self._on_log_received)
        self._level_filter.currentTextChanged.connect(self._on_filter_changed)
        self._auto_scroll_cb.toggled.connect(self._on_auto_scroll_changed)
        self._max_lines_spin.valueChanged.connect(self._on_max_lines_changed)
        self._pause_btn.toggled.connect(self._on_pause_toggled)
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        self._save_btn.clicked.connect(self._on_save_clicked)
        # 测试按钮的连接已在创建时完成
    
    def _setup_log_handler(self):
        """设置日志处理器"""
        # 创建自定义日志处理器
        self._log_handler = LogHandler(self.log_received)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self._log_handler.setFormatter(formatter)
        
        # 添加到根日志记录器
        root_logger = logging.getLogger()
        root_logger.addHandler(self._log_handler)
        
        # 确保日志级别足够低以捕获所有日志
        if root_logger.level > logging.DEBUG:
            root_logger.setLevel(logging.DEBUG)
    
    def _on_log_received(self, level, message, timestamp):
        """处理接收到的日志"""
        if not self._is_paused:
            self._log_buffer.add_log(level, message, timestamp)
            self._pending_updates += 1
    
    def _update_display(self):
        """更新显示"""
        if self._pending_updates == 0 or self._is_paused:
            return
        
        start_time = datetime.now()
        
        try:
            # 获取当前过滤级别
            filter_level = self._get_filter_level()
            
            # 获取需要显示的日志
            logs = self._log_buffer.get_logs()
            
            # 过滤日志
            if filter_level is not None:
                logs = [log for log in logs if log['level'] >= filter_level]
            
            # 限制显示行数
            max_lines = self._max_lines_spin.value()
            if len(logs) > max_lines:
                logs = logs[-max_lines:]
            
            # 更新显示
            self._refresh_display(logs)
            
            # 更新统计信息
            total_count = self._log_buffer.get_count()
            filtered_count = len(logs)
            self._stats_label.setText(f"日志统计: {total_count} 条 (显示: {filtered_count} 条)")
            
            # 重置待更新计数
            self._pending_updates = 0
            
            # 更新性能指示器
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            self._perf_label.setText(f"更新: {elapsed:.1f} ms")
            
        except Exception as e:
            performance_logger.error(f"更新日志显示失败: {e}")
    
    def _refresh_display(self, logs):
        """刷新显示内容"""
        # 保存当前滚动位置
        scrollbar = self._log_display.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
        
        # 清空并重新填充
        self._log_display.clear()
        
        cursor = self._log_display.textCursor()
        
        for log in logs:
            # 设置文本颜色
            format = QTextCharFormat()
            format.setForeground(self._level_colors.get(log['level'], QColor(0, 0, 0)))
            
            cursor.setCharFormat(format)
            cursor.insertText(log['message'] + '\n')
        
        # 自动滚动到底部
        if self._auto_scroll_cb.isChecked() and (was_at_bottom or len(logs) < 100):
            scrollbar.setValue(scrollbar.maximum())
    
    def _get_filter_level(self):
        """获取过滤级别"""
        filter_text = self._level_filter.currentText()
        if filter_text == '全部':
            return None
        
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(filter_text, None)
    
    def _on_filter_changed(self):
        """过滤器变更处理"""
        self._pending_updates = 1  # 触发更新
    
    def _on_auto_scroll_changed(self, checked):
        """自动滚动变更处理"""
        self.emit_config_changed()
    
    def _on_max_lines_changed(self, value):
        """最大行数变更处理"""
        self._pending_updates = 1  # 触发更新
        self.emit_config_changed()
    
    def _on_pause_toggled(self, checked):
        """暂停切换处理"""
        self._is_paused = checked
        self._pause_btn.setText("继续" if checked else "暂停")
        
        if not checked:
            self._pending_updates = 1  # 恢复时触发更新
    
    def _on_clear_clicked(self):
        """清空按钮点击处理"""
        self._log_buffer.clear()
        self._log_display.clear()
        self._stats_label.setText("日志统计: 0 条")
        self.emit_status_changed("日志已清空")
    
    def _on_save_clicked(self):
        """保存按钮点击处理"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            # 选择保存文件
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "保存日志文件",
                f"artalekey_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;所有文件 (*)"
            )
            
            if filename:
                # 获取所有日志
                logs = self._log_buffer.get_logs()
                
                # 写入文件
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"ArtaleKey 日志导出\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"总计: {len(logs)} 条日志\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for log in logs:
                        f.write(log['message'] + '\n')
                
                self.emit_status_changed(f"日志已保存到: {filename}")
                
        except Exception as e:
            performance_logger.error(f"保存日志失败: {e}")
            self.emit_status_changed(f"保存日志失败: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return {
            'level_filter': self._level_filter.currentText() if self._level_filter else '全部',
            'auto_scroll': self._auto_scroll_cb.isChecked() if self._auto_scroll_cb else True,
            'max_lines': self._max_lines_spin.value() if self._max_lines_spin else 5000,
        }
    
    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        if self._level_filter and 'level_filter' in config:
            self._level_filter.setCurrentText(config['level_filter'])
        
        if self._auto_scroll_cb and 'auto_scroll' in config:
            self._auto_scroll_cb.setChecked(config['auto_scroll'])
        
        if self._max_lines_spin and 'max_lines' in config:
            self._max_lines_spin.setValue(config['max_lines'])
    
    def cleanup(self):
        """清理资源"""
        # 停止定时器
        if self._update_timer:
            self._update_timer.stop()
        
        # 移除日志处理器
        if self._log_handler:
            root_logger = logging.getLogger()
            root_logger.removeHandler(self._log_handler)
        
        # 调用父类清理
        super().cleanup()
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return True  # 日志标签页始终启用
    
    def get_log_count(self) -> int:
        """获取日志数量"""
        return self._log_buffer.get_count()
    
    def _generate_test_logs(self):
        """生成测试日志"""
        try:
            performance_logger.debug("这是一条调试日志 - 测试DEBUG级别")
            performance_logger.info("应用程序启动完成 - 测试INFO级别")
            performance_logger.warning("检测到潜在问题 - 测试WARNING级别")
            performance_logger.error("发生错误，但程序可以继续运行 - 测试ERROR级别")
            
            # 生成一些模拟的应用日志
            performance_logger.info("用户操作: 点击了快速向上按钮")
            performance_logger.info("权限检查: 所有权限已授予")
            performance_logger.info("OCR处理: 识别到文字内容")
            performance_logger.warning("热键监听: 检测到按键冲突")
            performance_logger.error("网络请求: API调用失败，正在重试")
            
            self.emit_status_changed("已生成测试日志")
            
        except Exception as e:
            performance_logger.error(f"生成测试日志失败: {e}")
    
    def add_test_logs(self):
        """添加测试日志（用于调试）"""
        import time
        
        test_logs = [
            (logging.DEBUG, "这是一条调试日志"),
            (logging.INFO, "应用程序启动完成"),
            (logging.WARNING, "检测到潜在问题"),
            (logging.ERROR, "发生错误，但程序可以继续运行"),
            (logging.CRITICAL, "严重错误，程序可能无法继续"),
        ]
        
        for level, message in test_logs:
            timestamp = time.time()
            formatted_msg = f"{datetime.now().strftime('%H:%M:%S')} - TestLogger - {logging.getLevelName(level)} - {message}"
            self.log_received.emit(level, formatted_msg, timestamp)
            time.sleep(0.1) 