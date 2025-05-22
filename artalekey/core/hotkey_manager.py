from typing import Optional
from pynput import keyboard
from pynput.keyboard import Key, Controller, KeyCode
from PyQt6.QtCore import QThread
import time
import threading

class KeyboardManager:
    """键盘管理器单例"""
    _instance: Optional['KeyboardManager'] = None
    _controller: Optional[Controller] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._controller = Controller()
        return cls._instance

    @property
    def controller(self) -> Controller:
        return self._controller

class KeySimulator(QThread):
    """按键模拟器"""
    def __init__(self):
        super().__init__()
        self.keyboard = KeyboardManager().controller
        self.running = False
        self.interval = 0.04  # 默认40ms
        self._lock = threading.Lock()
        
    def set_interval(self, interval_ms: float):
        """设置按键间隔"""
        with self._lock:
            self.interval = interval_ms / 1000.0

    def stop(self):
        """安全停止模拟器"""
        with self._lock:
            if self.running:
                self.running = False
                # 确保释放所有按键
                self.keyboard.release(Key.space)
                self.keyboard.release(Key.left)
                self.keyboard.release(Key.right)

    def run(self):
        try:
            with self._lock:
                if self.running:  # 防止重复启动
                    return
                self.running = True
                self.keyboard.press(Key.space)
            
            while self.running:
                with self._lock:
                    if not self.running:
                        break
                    # 左键按下-释放
                    self.keyboard.press(Key.left)
                    time.sleep(self.interval)
                    self.keyboard.release(Key.left)
                    
                    if not self.running:
                        break
                    
                    # 右键按下-释放
                    self.keyboard.press(Key.right)
                    time.sleep(self.interval)
                    self.keyboard.release(Key.right)
                    
                    # 等待下一个循环
                    time.sleep(self.interval)
        finally:
            self.stop()

class HotkeyListener(QThread):
    """全局热键监听器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.running = True
        self.key_press_time = 0
        self.w_pressed = False
        self.up_pressed = False
        self.hold_time = 0.5  # 默认长按时间 500ms
        self._lock = threading.Lock()
        
    def set_hold_time(self, time_ms):
        """设置长按触发时间"""
        with self._lock:
            self.hold_time = time_ms / 1000.0
        
    def run(self):
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            while self.running:
                with self._lock:
                    if (self.w_pressed and self.up_pressed and 
                        not self.parent.key_simulator.running):
                        current_time = time.time()
                        if current_time - self.key_press_time >= self.hold_time:
                            if self.parent.global_switch.isChecked():
                                self.parent.key_simulator.start()
                time.sleep(0.01)  # 降低CPU使用率
            listener.stop()
            
    def on_press(self, key):
        try:
            with self._lock:
                if isinstance(key, KeyCode):
                    if key.char == 'w':
                        if not self.w_pressed:  # 防止重复按下
                            self.w_pressed = True
                            if not self.key_press_time:
                                self.key_press_time = time.time()
                elif key == Key.up:
                    if not self.up_pressed:  # 防止重复按下
                        self.up_pressed = True
                        if not self.key_press_time:
                            self.key_press_time = time.time()
        except AttributeError:
            pass
            
    def on_release(self, key):
        try:
            with self._lock:
                if isinstance(key, KeyCode):
                    if key.char == 'w':
                        self.w_pressed = False
                        self.key_press_time = 0
                        self.parent.key_simulator.stop()
                elif key == Key.up:
                    self.up_pressed = False
                    self.key_press_time = 0
                    self.parent.key_simulator.stop()
        except AttributeError:
            pass 