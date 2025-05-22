import os
import sys
import time
import threading
from typing import Optional, Dict, List, Callable
from collections import deque
from PyQt6.QtCore import QThread, pyqtSignal
from .logger import performance_logger

class WindowInfo:
    """窗口信息类"""
    def __init__(self, window_id: int, title: str, process_name: str, process_id: int):
        self.window_id = window_id
        self.title = title
        self.process_name = process_name
        self.process_id = process_id
        self.last_active_time = time.time()  # 添加最后活跃时间
    
    def __str__(self):
        return f"{self.process_name} - {self.title}"
    
    def __repr__(self):
        return f"WindowInfo(id={self.window_id}, title='{self.title}', process='{self.process_name}', pid={self.process_id})"
    
    def __eq__(self, other):
        """比较两个窗口信息是否相同（基于进程名）"""
        if not isinstance(other, WindowInfo):
            return False
        return self.process_name.lower() == other.process_name.lower()
    
    def __hash__(self):
        """用于在集合中使用"""
        return hash(self.process_name.lower())

class WindowDetector:
    """跨平台窗口检测器"""
    
    def __init__(self):
        self.platform = sys.platform
        self._setup_platform_specific()
    
    def _setup_platform_specific(self):
        """根据平台设置特定的检测方法"""
        if self.platform == "darwin":
            self._setup_macos()
        elif self.platform == "win32":
            self._setup_windows()
        else:
            self._setup_linux()
    
    def _setup_macos(self):
        """设置macOS检测"""
        try:
            from AppKit import NSWorkspace, NSApplication
            from Cocoa import NSRunningApplication
            self._has_appkit = True
            performance_logger.info("macOS AppKit available for window detection")
        except ImportError:
            self._has_appkit = False
            performance_logger.warning("AppKit not available, using fallback method")
    
    def _setup_windows(self):
        """设置Windows检测"""
        try:
            import win32gui
            import win32process
            self._has_win32 = True
            performance_logger.info("Windows win32 API available for window detection")
        except ImportError:
            self._has_win32 = False
            performance_logger.warning("win32 API not available")
    
    def _setup_linux(self):
        """设置Linux检测"""
        try:
            import Xlib
            from Xlib import display
            self._has_xlib = True
            performance_logger.info("Linux Xlib available for window detection")
        except ImportError:
            self._has_xlib = False
            performance_logger.warning("Xlib not available")
    
    @performance_logger.measure_time("get_active_window")
    def get_active_window(self) -> Optional[WindowInfo]:
        """获取当前活动窗口信息"""
        try:
            if self.platform == "darwin":
                return self._get_active_window_macos()
            elif self.platform == "win32":
                return self._get_active_window_windows()
            else:
                return self._get_active_window_linux()
        except Exception as e:
            performance_logger.error(f"Failed to get active window: {e}")
            return None
    
    def _get_active_window_macos(self) -> Optional[WindowInfo]:
        """macOS活动窗口检测"""
        if not self._has_appkit:
            return self._get_active_window_macos_fallback()
        
        try:
            from AppKit import NSWorkspace
            from Cocoa import NSRunningApplication
            
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            
            if active_app:
                process_name = active_app.get('NSApplicationName', 'Unknown')
                process_id = active_app.get('NSApplicationProcessIdentifier', 0)
                
                # 尝试获取窗口标题（简化实现）
                window_title = process_name  # 在macOS上获取具体窗口标题比较复杂
                
                return WindowInfo(
                    window_id=0,  # macOS窗口ID获取复杂，暂时使用0
                    title=window_title,
                    process_name=process_name,
                    process_id=process_id
                )
        except Exception as e:
            performance_logger.error(f"macOS window detection error: {e}")
            return self._get_active_window_macos_fallback()
    
    def _get_active_window_macos_fallback(self) -> Optional[WindowInfo]:
        """macOS备用检测方法"""
        try:
            import subprocess
            # 使用 AppleScript 获取前台应用
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                return frontApp
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], 
                                  capture_output=True, text=True, timeout=1)
            
            if result.returncode == 0:
                process_name = result.stdout.strip()
                return WindowInfo(
                    window_id=0,
                    title=process_name,
                    process_name=process_name,
                    process_id=0
                )
        except Exception as e:
            performance_logger.error(f"macOS fallback detection error: {e}")
        
        return None
    
    def _get_active_window_windows(self) -> Optional[WindowInfo]:
        """Windows活动窗口检测"""
        if not self._has_win32:
            return None
        
        try:
            import win32gui
            import win32process
            
            # 获取前台窗口
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                # 获取窗口标题
                window_title = win32gui.GetWindowText(hwnd)
                
                # 获取进程ID
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                
                # 获取进程名称
                import psutil
                try:
                    process = psutil.Process(process_id)
                    process_name = process.name()
                except:
                    process_name = "Unknown"
                
                return WindowInfo(
                    window_id=hwnd,
                    title=window_title,
                    process_name=process_name,
                    process_id=process_id
                )
        except Exception as e:
            performance_logger.error(f"Windows window detection error: {e}")
        
        return None
    
    def _get_active_window_linux(self) -> Optional[WindowInfo]:
        """Linux活动窗口检测"""
        if not self._has_xlib:
            return None
        
        try:
            from Xlib import display, X
            
            d = display.Display()
            root = d.screen().root
            
            # 获取活动窗口
            active_window = root.get_full_property(
                d.intern_atom('_NET_ACTIVE_WINDOW'), X.AnyPropertyType
            )
            
            if active_window and active_window.value:
                window_id = active_window.value[0]
                window = d.create_resource_object('window', window_id)
                
                # 获取窗口标题
                window_title = window.get_full_property(
                    d.intern_atom('_NET_WM_NAME'), X.AnyPropertyType
                )
                title = window_title.value.decode('utf-8') if window_title else "Unknown"
                
                # 获取进程ID
                pid_property = window.get_full_property(
                    d.intern_atom('_NET_WM_PID'), X.AnyPropertyType
                )
                
                if pid_property:
                    process_id = pid_property.value[0]
                    
                    # 获取进程名称
                    import psutil
                    try:
                        process = psutil.Process(process_id)
                        process_name = process.name()
                    except:
                        process_name = "Unknown"
                    
                    return WindowInfo(
                        window_id=window_id,
                        title=title,
                        process_name=process_name,
                        process_id=process_id
                    )
        except Exception as e:
            performance_logger.error(f"Linux window detection error: {e}")
        
        return None
    
    def get_running_applications(self) -> List[str]:
        """获取当前运行的应用程序列表"""
        try:
            import psutil
            processes = []
            
            for proc in psutil.process_iter(['name']):
                try:
                    process_name = proc.info['name']
                    if process_name and process_name not in processes:
                        processes.append(process_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return sorted(processes)
        except Exception as e:
            performance_logger.error(f"Failed to get running applications: {e}")
            return []

class ActiveWindowMonitor(QThread):
    """活动窗口监控器 - 增强版本，支持历史记录"""
    
    # 信号
    active_window_changed = pyqtSignal(object)  # WindowInfo
    target_window_activated = pyqtSignal()     # 目标窗口激活
    target_window_deactivated = pyqtSignal()   # 目标窗口失活
    window_history_updated = pyqtSignal(list)  # 窗口历史记录更新
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.detector = WindowDetector()
        self._running = False
        self._target_processes = set()  # 目标进程名称集合
        self._current_window = None
        self._is_target_active = False
        self._check_interval = 0.5  # 检查间隔（秒）
        self._lock = threading.RLock()
        
        # 新增：窗口历史记录
        self._window_history = deque(maxlen=20)  # 最多保存20个历史记录
        self._history_dict = {}  # 用于快速查找和更新
        self._excluded_apps = {  # 排除的应用（通常是系统应用或当前应用）
            'artalekey', 'python', 'python3', 'terminal', 'iterm2', 
            'finder', 'dock', 'spotlight', 'systemuiserver'
        }
    
    def set_target_processes(self, process_names: List[str]):
        """设置目标进程名称列表"""
        with self._lock:
            self._target_processes = {name.lower() for name in process_names}
            performance_logger.info(f"Target processes set: {self._target_processes}")
    
    def add_target_process(self, process_name: str):
        """添加目标进程"""
        with self._lock:
            self._target_processes.add(process_name.lower())
            performance_logger.info(f"Added target process: {process_name}")
    
    def remove_target_process(self, process_name: str):
        """移除目标进程"""
        with self._lock:
            self._target_processes.discard(process_name.lower())
            performance_logger.info(f"Removed target process: {process_name}")
    
    def get_target_processes(self) -> List[str]:
        """获取目标进程列表"""
        with self._lock:
            return list(self._target_processes)
    
    def set_check_interval(self, interval: float):
        """设置检查间隔"""
        self._check_interval = max(0.1, min(5.0, interval))
    
    def is_target_window_active(self) -> bool:
        """检查目标窗口是否处于活动状态"""
        with self._lock:
            return self._is_target_active
    
    def get_current_window(self) -> Optional[WindowInfo]:
        """获取当前窗口信息"""
        with self._lock:
            return self._current_window
    
    def get_window_history(self) -> List[WindowInfo]:
        """获取窗口历史记录（按时间倒序）"""
        with self._lock:
            # 返回按最后活跃时间排序的历史记录
            return sorted(
                list(self._window_history), 
                key=lambda w: w.last_active_time, 
                reverse=True
            )
    
    def get_recent_apps(self, limit: int = 10) -> List[str]:
        """获取最近使用的应用程序名称列表"""
        history = self.get_window_history()
        recent_apps = []
        seen = set()
        
        for window in history:
            app_name = window.process_name
            if app_name.lower() not in seen and app_name.lower() not in self._excluded_apps:
                recent_apps.append(app_name)
                seen.add(app_name.lower())
                if len(recent_apps) >= limit:
                    break
        
        return recent_apps
    
    def add_to_excluded_apps(self, app_name: str):
        """添加要排除的应用"""
        with self._lock:
            self._excluded_apps.add(app_name.lower())
    
    def _add_to_history(self, window: WindowInfo):
        """添加窗口到历史记录"""
        if not window or window.process_name.lower() in self._excluded_apps:
            return
        
        with self._lock:
            # 更新时间戳
            window.last_active_time = time.time()
            
            # 如果已存在，更新时间并移到前面
            if window.process_name.lower() in self._history_dict:
                # 移除旧记录
                old_window = self._history_dict[window.process_name.lower()]
                try:
                    self._window_history.remove(old_window)
                except ValueError:
                    pass
            
            # 添加新记录
            self._history_dict[window.process_name.lower()] = window
            self._window_history.append(window)
            
            # 发送历史更新信号
            self.window_history_updated.emit(self.get_recent_apps())
    
    def run(self):
        """监控线程主循环"""
        self._running = True
        performance_logger.info("Active window monitor started")
        
        while self._running:
            try:
                # 获取当前活动窗口
                current_window = self.detector.get_active_window()
                
                if current_window:
                    # 检查窗口是否发生变化
                    window_changed = False
                    with self._lock:
                        if (not self._current_window or 
                            self._current_window.process_name != current_window.process_name or
                            self._current_window.title != current_window.title):
                            window_changed = True
                            self._current_window = current_window
                            
                            # 添加到历史记录
                            self._add_to_history(current_window)
                    
                    if window_changed:
                        self.active_window_changed.emit(current_window)
                        performance_logger.info(f"Active window changed: {current_window}")
                    
                    # 检查是否为目标窗口
                    is_target = self._is_target_window(current_window)
                    
                    with self._lock:
                        if is_target != self._is_target_active:
                            self._is_target_active = is_target
                            if is_target:
                                self.target_window_activated.emit()
                                performance_logger.info(f"Target window activated: {current_window.process_name}")
                            else:
                                self.target_window_deactivated.emit()
                                performance_logger.info(f"Target window deactivated, current: {current_window.process_name}")
                
                # 等待下一次检查
                time.sleep(self._check_interval)
                
            except Exception as e:
                performance_logger.error(f"Window monitor error: {e}")
                time.sleep(1)  # 发生错误时延长等待时间
        
        performance_logger.info("Active window monitor stopped")
    
    def _is_target_window(self, window: WindowInfo) -> bool:
        """检查窗口是否为目标窗口"""
        if not window or not self._target_processes:
            return False
        
        process_name_lower = window.process_name.lower()
        
        # 检查完全匹配
        if process_name_lower in self._target_processes:
            return True
        
        # 检查部分匹配（去掉扩展名）
        process_base = process_name_lower.replace('.exe', '').replace('.app', '')
        for target in self._target_processes:
            target_base = target.replace('.exe', '').replace('.app', '')
            if process_base == target_base:
                return True
        
        return False
    
    def stop(self):
        """停止监控"""
        self._running = False
        self.wait(2000)  # 等待最多2秒

# 全局窗口监控器实例
window_monitor = ActiveWindowMonitor() 