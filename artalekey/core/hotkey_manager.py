from typing import Optional, Callable
from pynput import keyboard
from pynput.keyboard import Key, Controller, KeyCode
from PyQt6.QtCore import QThread, pyqtSignal, QObject
import time
import threading
from enum import Enum

class KeyState(Enum):
    """按键状态枚举"""
    RELEASED = 0
    PRESSED = 1
    LONG_PRESSED = 2

class KeyboardManager:
    """键盘管理器单例 - 优化了资源管理"""
    _instance: Optional['KeyboardManager'] = None
    _controller: Optional[Controller] = None
    _lock = threading.RLock()  # 使用递归锁提高性能

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # 双重检查锁定
                    cls._instance = super().__new__(cls)
                    cls._controller = Controller()
        return cls._instance

    @property
    def controller(self) -> Controller:
        return self._controller

class KeySimulator(QThread):
    """优化的按键模拟器 - 减少锁竞争和CPU使用"""
    
    # 添加信号用于状态通知
    simulation_started = pyqtSignal()
    simulation_stopped = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.keyboard = KeyboardManager().controller
        self._running = False
        self._interval = 40  # 毫秒
        self._should_stop = threading.Event()
        self._lock = threading.RLock()
        # 预分配按键状态，避免重复创建
        self._keys_pressed = set()
        
    def set_interval(self, interval_ms: int):
        """设置按键间隔 - 优化了类型和范围检查"""
        interval_ms = max(10, min(1000, interval_ms))  # 限制范围
        with self._lock:
            self._interval = interval_ms

    def stop(self):
        """优化的停止方法 - 使用事件机制"""
        with self._lock:
            if self._running:
                self._should_stop.set()
                self._release_all_keys()

    def _release_all_keys(self):
        """安全释放所有按键"""
        try:
            for key in list(self._keys_pressed):
                self.keyboard.release(key)
            self._keys_pressed.clear()
        except Exception:
            pass  # 忽略释放过程中的异常

    def run(self):
        """优化的运行循环 - 减少CPU使用和提高响应性"""
        try:
            with self._lock:
                if self._running:
                    return
                self._running = True
                self._should_stop.clear()
            
            self.simulation_started.emit()
            
            # 按下空格键开始
            self.keyboard.press(Key.space)
            self._keys_pressed.add(Key.space)
            
            interval_sec = self._interval / 1000.0
            
            while not self._should_stop.is_set():
                start_time = time.perf_counter()
                
                # 左键循环
                if self._should_stop.wait(0):
                    break
                self.keyboard.press(Key.left)
                self._keys_pressed.add(Key.left)
                
                if self._should_stop.wait(interval_sec):
                    break
                self.keyboard.release(Key.left)
                self._keys_pressed.discard(Key.left)
                
                # 右键循环
                if self._should_stop.wait(0):
                    break
                self.keyboard.press(Key.right)
                self._keys_pressed.add(Key.right)
                
                if self._should_stop.wait(interval_sec):
                    break
                self.keyboard.release(Key.right)
                self._keys_pressed.discard(Key.right)
                
                # 动态调整睡眠时间以保持精确的间隔
                elapsed = time.perf_counter() - start_time
                remaining = interval_sec - elapsed
                if remaining > 0:
                    if self._should_stop.wait(remaining):
                        break
                        
        except Exception as e:
            print(f"KeySimulator error: {e}")
        finally:
            self._release_all_keys()
            with self._lock:
                self._running = False
            self.simulation_stopped.emit()

class HotkeyListener(QThread):
    """优化的全局热键监听器 - 使用事件驱动而非轮询"""
    
    # 添加信号用于按键事件
    key_combination_detected = pyqtSignal()
    key_combination_released = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._running = True
        self._key_states = {}  # 缓存按键状态
        self._hold_time = 500  # 毫秒
        self._lock = threading.RLock()
        
        # 使用threading.Timer来处理长按检测，避免Qt线程问题
        self._long_press_timer = None
        
        # 优化：预定义需要监听的按键
        self._monitored_keys = {'w', Key.up}
        
    def set_hold_time(self, time_ms: int):
        """设置长按触发时间"""
        time_ms = max(50, min(5000, time_ms))  # 限制范围
        with self._lock:
            self._hold_time = time_ms
    
    def _start_long_press_timer(self):
        """启动长按计时器"""
        self._cancel_long_press_timer()
        self._long_press_timer = threading.Timer(
            self._hold_time / 1000.0, 
            self._on_long_press_timeout
        )
        self._long_press_timer.start()
    
    def _cancel_long_press_timer(self):
        """取消长按计时器"""
        if self._long_press_timer and self._long_press_timer.is_alive():
            self._long_press_timer.cancel()
        self._long_press_timer = None
        
    def _on_long_press_timeout(self):
        """长按超时处理"""
        with self._lock:
            if self._is_combination_pressed() and self._running:
                self.key_combination_detected.emit()
                
    def _is_combination_pressed(self) -> bool:
        """检查组合键是否被按下"""
        w_state = self._key_states.get('w', KeyState.RELEASED)
        up_state = self._key_states.get(Key.up, KeyState.RELEASED)
        return w_state != KeyState.RELEASED and up_state != KeyState.RELEASED
        
    def run(self):
        """优化的监听循环"""
        try:
            with keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                suppress=False  # 不抑制按键，减少系统负担
            ) as listener:
                while self._running:
                    self.msleep(50)  # 使用Qt的msleep，更高效
                listener.stop()
        except Exception as e:
            print(f"HotkeyListener error: {e}")
            
    def _on_press(self, key):
        """优化的按键按下处理"""
        try:
            key_id = None
            if isinstance(key, KeyCode) and hasattr(key, 'char') and key.char:
                if key.char in {'w'}:  # 只处理我们关心的字符键
                    key_id = key.char
            elif key == Key.up:
                key_id = key
                
            if key_id is None:
                return
                
            with self._lock:
                current_state = self._key_states.get(key_id, KeyState.RELEASED)
                if current_state == KeyState.RELEASED:
                    self._key_states[key_id] = KeyState.PRESSED
                    
                    # 检查是否需要开始长按计时
                    if self._is_combination_pressed():
                        self._start_long_press_timer()
                        
        except (AttributeError, TypeError):
            pass  # 忽略特殊按键
            
    def _on_release(self, key):
        """优化的按键释放处理"""
        try:
            key_id = None
            if isinstance(key, KeyCode) and hasattr(key, 'char') and key.char:
                if key.char in {'w'}:
                    key_id = key.char
            elif key == Key.up:
                key_id = key
                
            if key_id is None:
                return
                
            with self._lock:
                if key_id in self._key_states:
                    self._key_states[key_id] = KeyState.RELEASED
                    
                    # 停止长按计时器
                    self._cancel_long_press_timer()
                    
                    # 发送释放信号
                    self.key_combination_released.emit()
                    
        except (AttributeError, TypeError):
            pass
            
    def stop(self):
        """安全停止监听器"""
        self._running = False
        self._cancel_long_press_timer()
        self.wait(1000)  # 最多等待1秒 