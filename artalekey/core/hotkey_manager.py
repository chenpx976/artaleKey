from typing import Optional
from pynput import keyboard
from pynput.keyboard import Key, Controller, KeyCode
from PyQt6.QtCore import QThread, pyqtSignal
import time
from .logger import logger

class KeyboardManager:
    """键盘管理器单例"""
    _instance: Optional['KeyboardManager'] = None
    _controller: Optional[Controller] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._controller = Controller()
            logger.debug("键盘控制器已初始化")
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
        
    def set_interval(self, interval_ms: float):
        """设置按键间隔"""
        self.interval = interval_ms / 1000.0
        logger.debug(f"设置按键间隔: {interval_ms}ms")

    def run(self):
        try:
            # 按下空格键
            self.keyboard.press(Key.space)
            logger.debug("开始按键模拟: 按下空格键")
            self.running = True
            
            while self.running:
                # 按下左键
                self.keyboard.press(Key.left)
                time.sleep(self.interval)
                self.keyboard.release(Key.left)
                
                if not self.running:
                    break
                    
                # 按下右键
                self.keyboard.press(Key.right)
                time.sleep(self.interval)
                self.keyboard.release(Key.right)
                
                time.sleep(self.interval)
        finally:
            # 确保释放所有按键
            self.keyboard.release(Key.space)
            self.keyboard.release(Key.left)
            self.keyboard.release(Key.right)
            self.running = False
            logger.debug("停止按键模拟: 释放所有按键")

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
        logger.debug("热键监听器已初始化")
        
    def set_hold_time(self, time_ms):
        """设置长按触发时间"""
        self.hold_time = time_ms / 1000.0  # 转换为秒
        logger.debug(f"设置长按时间: {time_ms}ms")
        
    def run(self):
        with keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        ) as listener:
            logger.info("热键监听器已启动")
            while self.running:
                # 检查按键长按
                if self.w_pressed and self.up_pressed and not self.parent.key_simulator.running:
                    current_time = time.time()
                    if current_time - self.key_press_time >= self.hold_time:
                        if self.parent.global_switch.isChecked():
                            logger.info("触发快速向上功能")
                            self.parent.key_simulator.running = True
                            self.parent.key_simulator.start()
                # 如果任一按键释放，立即停止功能
                elif self.parent.key_simulator.running:
                    self.parent.key_simulator.running = False
                time.sleep(0.01)  # 降低CPU使用率
            listener.stop()
            logger.info("热键监听器已停止")
            
    def on_press(self, key):
        """按键按下时的回调"""
        try:
            if isinstance(key, KeyCode):
                if key.char == 'w':
                    self.w_pressed = True
                    if not self.key_press_time:
                        self.key_press_time = time.time()
                        logger.debug("W键按下")
            else:
                if key == Key.up:
                    self.up_pressed = True
                    if not self.key_press_time:
                        self.key_press_time = time.time()
                        logger.debug("↑键按下")
        except AttributeError:
            pass
            
    def on_release(self, key):
        """按键释放时的回调"""
        try:
            if isinstance(key, KeyCode):
                if key.char == 'w':
                    self.w_pressed = False
                    self.key_press_time = 0
                    logger.debug("W键释放")
                    if self.parent.key_simulator.running:
                        self.parent.key_simulator.running = False
            else:
                if key == Key.up:
                    self.up_pressed = False
                    self.key_press_time = 0
                    logger.debug("↑键释放")
                    if self.parent.key_simulator.running:
                        self.parent.key_simulator.running = False
        except AttributeError:
            pass 