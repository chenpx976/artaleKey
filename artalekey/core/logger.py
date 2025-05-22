import logging
import os
import time
from functools import wraps
from typing import Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal

class PerformanceLogger:
    """性能监控日志器"""
    
    def __init__(self, name: str = "ArtaleKey"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 文件处理器 - 仅记录重要信息
            log_dir = os.path.expanduser("~/.artalekey")
            os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(
                os.path.join(log_dir, "performance.log"),
                encoding='utf-8'
            )
            file_handler.setLevel(logging.WARNING)
            
            # 格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)
    
    def measure_time(self, func_name: str = None):
        """性能测量装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    self.logger.error(f"Error in {func_name or func.__name__}: {e}")
                    raise
                finally:
                    end_time = time.perf_counter()
                    duration = (end_time - start_time) * 1000  # 转为毫秒
                    
                    # 只记录超过阈值的慢操作
                    if duration > 50:  # 50ms阈值
                        self.logger.warning(
                            f"Slow operation: {func_name or func.__name__} took {duration:.2f}ms"
                        )
                    elif duration > 10:  # 10ms以上记录为信息
                        self.logger.info(
                            f"{func_name or func.__name__} took {duration:.2f}ms"
                        )
            return wrapper
        return decorator
    
    def log_memory_usage(self, context: str = ""):
        """记录内存使用情况"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > 100:  # 超过100MB记录警告
                self.logger.warning(f"High memory usage {context}: {memory_mb:.1f}MB")
            else:
                self.logger.info(f"Memory usage {context}: {memory_mb:.1f}MB")
        except ImportError:
            self.logger.debug("psutil not available for memory monitoring")
    
    def info(self, message: str):
        """信息日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """警告日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """错误日志"""
        self.logger.error(message)

# 全局日志实例
performance_logger = PerformanceLogger() 