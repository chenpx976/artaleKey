from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from typing import Optional
from artalekey.core.window_detector import WindowDetector
from artalekey.core.logger import performance_logger

class WindowStatusMonitor(QThread):
    """MapleStory Worlds窗口状态监控器"""
    
    # 信号定义
    window_status_changed = pyqtSignal(bool)  # 窗口状态变化 (True=激活, False=未激活)
    window_found_changed = pyqtSignal(bool)   # 窗口是否存在 (True=存在, False=不存在)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window_detector = WindowDetector()
        self._running = False
        self._check_interval = 1000  # 1秒检查一次
        self._timer = None
        
        # 状态追踪
        self._is_window_active = False
        self._is_window_found = False
        self._target_window_name = "MapleStory Worlds"
        
    def set_target_window(self, window_name: str):
        """设置目标窗口名称"""
        self._target_window_name = window_name
        performance_logger.info(f"设置目标窗口: {window_name}")
    
    def set_check_interval(self, interval_ms: int):
        """设置检查间隔（毫秒）"""
        self._check_interval = interval_ms
        if self._timer and self._timer.isActive():
            self._timer.setInterval(interval_ms)
    
    def start_monitoring(self):
        """开始监控"""
        if self._running:
            return
            
        self._running = True
        
        # 立即检查一次
        self._check_window_status()
        
        # 设置定时器
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_window_status)
        self._timer.start(self._check_interval)
        
        performance_logger.info(f"窗口状态监控已启动，检查间隔: {self._check_interval}ms")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self._running:
            return
            
        self._running = False
        
        if self._timer:
            self._timer.stop()
            self._timer = None
            
        performance_logger.info("窗口状态监控已停止")
    
    def _check_window_status(self):
        """检查窗口状态"""
        try:
            # 检查窗口是否存在
            is_found = self._is_target_window_running()
            
            # 检查窗口是否激活
            is_active = False
            if is_found:
                is_active = self._is_target_window_active()
            
            # 发送状态变化信号
            if is_found != self._is_window_found:
                self._is_window_found = is_found
                self.window_found_changed.emit(is_found)
                performance_logger.info(f"窗口存在状态变化: {is_found}")
            
            if is_active != self._is_window_active:
                self._is_window_active = is_active
                self.window_status_changed.emit(is_active)
                performance_logger.info(f"窗口激活状态变化: {is_active}")
                
        except Exception as e:
            performance_logger.error(f"检查窗口状态失败: {e}")
    
    def _is_target_window_running(self) -> bool:
        """检查目标窗口是否正在运行"""
        try:
            # 使用窗口检测器的方法
            if hasattr(self.window_detector, 'is_game_running'):
                return self.window_detector.is_game_running(self._target_window_name)
            
            # 备用方案：检查游戏窗口区域
            if hasattr(self.window_detector, 'get_game_window_region'):
                bounds = self.window_detector.get_game_window_region(self._target_window_name)
                return bounds is not None
            
            return False
            
        except Exception as e:
            performance_logger.error(f"检查窗口运行状态失败: {e}")
            return False
    
    def _is_target_window_active(self) -> bool:
        """检查目标窗口是否激活"""
        try:
            # 获取当前活动窗口
            active_window = self.window_detector.get_active_window()
            if active_window:
                # 检查进程名或窗口标题是否包含目标窗口名称
                window_text = f"{active_window.process_name} {active_window.title}".lower()
                if self._target_window_name.lower() in window_text:
                    return True
            return False
            
        except Exception as e:
            performance_logger.error(f"检查窗口激活状态失败: {e}")
            return False
    
    def get_current_status(self) -> dict:
        """获取当前状态"""
        return {
            'is_running': self._is_window_found,
            'is_active': self._is_window_active,
            'target_window': self._target_window_name
        }
    
    def is_window_active(self) -> bool:
        """获取窗口是否激活"""
        return self._is_window_active
    
    def is_window_found(self) -> bool:
        """获取窗口是否存在"""
        return self._is_window_found
    
    def activate_target_window(self):
        """激活目标窗口"""
        try:
            if hasattr(self.window_detector, 'activate_game_window'):
                self.window_detector.activate_game_window(self._target_window_name)
                performance_logger.info(f"尝试激活窗口: {self._target_window_name}")
            else:
                performance_logger.warning("窗口激活功能不可用")
        except Exception as e:
            performance_logger.error(f"激活窗口失败: {e}")

# 全局窗口状态监控器实例
window_status_monitor = WindowStatusMonitor() 