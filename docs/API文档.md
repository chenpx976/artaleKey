# ArtaleKey API 文档

## 概述

本文档详细描述了 ArtaleKey 项目中各个核心模块的 API 接口，包括类、方法、参数和返回值的详细说明。

## 核心模块 API

### 1. HotkeyManager (快捷键管理器)

**文件位置**: `artalekey/core/hotkey_manager.py`

#### 类定义

```python
class HotkeyManager:
    """全局快捷键管理器"""
    
    def __init__(self, config_manager=None):
        """
        初始化快捷键管理器
        
        Args:
            config_manager: 配置管理器实例
        """
```

#### 主要方法

##### register_hotkey()
```python
def register_hotkey(self, hotkey_combo: str, callback: callable, 
                   description: str = "") -> bool:
    """
    注册快捷键
    
    Args:
        hotkey_combo (str): 快捷键组合，如 'ctrl+alt+a'
        callback (callable): 回调函数
        description (str): 快捷键描述
        
    Returns:
        bool: 注册是否成功
        
    Example:
        manager.register_hotkey('w+up', self.handle_quick_up)
    """
```

##### unregister_hotkey()
```python
def unregister_hotkey(self, hotkey_combo: str) -> bool:
    """
    取消注册快捷键
    
    Args:
        hotkey_combo (str): 快捷键组合
        
    Returns:
        bool: 取消注册是否成功
    """
```

##### start_listening()
```python
def start_listening(self) -> None:
    """开始监听快捷键"""
```

##### stop_listening()
```python
def stop_listening(self) -> None:
    """停止监听快捷键"""
```

### 2. EnhancedOCR (OCR引擎)

**文件位置**: `artalekey/core/enhanced_ocr.py`

#### 类定义

```python
class EnhancedOCR:
    """增强型OCR识别引擎"""
    
    def __init__(self, use_gpu: bool = True, cache_size: int = 100):
        """
        初始化OCR引擎
        
        Args:
            use_gpu (bool): 是否使用GPU加速
            cache_size (int): 缓存大小
        """
```

#### 主要方法

##### recognize_text()
```python
def recognize_text(self, image_source, 
                  preprocess: bool = True,
                  language: str = 'en') -> OCRResult:
    """
    识别图像中的文字
    
    Args:
        image_source: 图像源（路径、PIL Image或numpy数组）
        preprocess (bool): 是否进行预处理
        language (str): 识别语言
        
    Returns:
        OCRResult: 识别结果对象
        
    Example:
        result = ocr.recognize_text('screenshot.png')
        print(result.text)
    """
```

##### batch_recognize()
```python
def batch_recognize(self, image_list: list, 
                   max_workers: int = 4) -> List[OCRResult]:
    """
    批量识别多个图像
    
    Args:
        image_list (list): 图像列表
        max_workers (int): 最大工作线程数
        
    Returns:
        List[OCRResult]: 识别结果列表
    """
```

##### preprocess_image()
```python
def preprocess_image(self, image, 
                    enhance_contrast: bool = True,
                    denoise: bool = True) -> np.ndarray:
    """
    图像预处理
    
    Args:
        image: 输入图像
        enhance_contrast (bool): 是否增强对比度
        denoise (bool): 是否降噪
        
    Returns:
        np.ndarray: 处理后的图像
    """
```

#### OCRResult 类

```python
class OCRResult:
    """OCR识别结果"""
    
    def __init__(self):
        self.text: str = ""           # 识别的文字
        self.confidence: float = 0.0  # 置信度
        self.boxes: List[Box] = []    # 文字框位置
        self.processing_time: float = 0.0  # 处理时间
        
    def to_dict(self) -> dict:
        """转换为字典格式"""
        
    def __str__(self) -> str:
        """字符串表示"""
```

### 3. LLMProcessor (LLM处理器)

**文件位置**: `artalekey/core/llm_processor.py`

#### 类定义

```python
class LLMProcessor:
    """LLM智能处理器"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo",
                 api_key: str = None):
        """
        初始化LLM处理器
        
        Args:
            model_name (str): 模型名称
            api_key (str): API密钥
        """
```

#### 主要方法

##### process_text()
```python
def process_text(self, text: str, 
                task_type: str = "analyze",
                context: dict = None) -> LLMResult:
    """
    处理文本
    
    Args:
        text (str): 输入文本
        task_type (str): 任务类型 ('analyze', 'summarize', 'extract')
        context (dict): 上下文信息
        
    Returns:
        LLMResult: 处理结果
        
    Example:
        result = processor.process_text("游戏界面文字", "analyze")
    """
```

##### batch_process()
```python
def batch_process(self, text_list: List[str],
                 task_type: str = "analyze") -> List[LLMResult]:
    """
    批量处理文本
    
    Args:
        text_list (List[str]): 文本列表
        task_type (str): 任务类型
        
    Returns:
        List[LLMResult]: 处理结果列表
    """
```

### 4. WindowDetector (窗口检测器)

**文件位置**: `artalekey/core/window_detector.py`

#### 类定义

```python
class WindowDetector:
    """窗口检测和过滤器"""
    
    def __init__(self, target_apps: List[str] = None):
        """
        初始化窗口检测器
        
        Args:
            target_apps (List[str]): 目标应用程序列表
        """
```

#### 主要方法

##### get_active_window()
```python
def get_active_window(self) -> WindowInfo:
    """
    获取当前活跃窗口信息
    
    Returns:
        WindowInfo: 窗口信息对象
    """
```

##### is_target_window()
```python
def is_target_window(self, window_info: WindowInfo) -> bool:
    """
    检查是否为目标窗口
    
    Args:
        window_info (WindowInfo): 窗口信息
        
    Returns:
        bool: 是否为目标窗口
    """
```

##### monitor_windows()
```python
def monitor_windows(self, callback: callable, 
                   interval: float = 1.0) -> None:
    """
    监控窗口变化
    
    Args:
        callback (callable): 回调函数
        interval (float): 检查间隔（秒）
    """
```

#### WindowInfo 类

```python
class WindowInfo:
    """窗口信息"""
    
    def __init__(self):
        self.title: str = ""          # 窗口标题
        self.app_name: str = ""       # 应用程序名称
        self.pid: int = 0             # 进程ID
        self.bounds: Rect = None      # 窗口边界
        self.is_active: bool = False  # 是否活跃
        
    def to_dict(self) -> dict:
        """转换为字典格式"""
```

### 5. Database (数据库管理)

**文件位置**: `artalekey/core/database.py`

#### 类定义

```python
class Database:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "artalekey.db"):
        """
        初始化数据库
        
        Args:
            db_path (str): 数据库文件路径
        """
```

#### 主要方法

##### save_ocr_result()
```python
def save_ocr_result(self, result: OCRResult, 
                   metadata: dict = None) -> int:
    """
    保存OCR结果
    
    Args:
        result (OCRResult): OCR结果
        metadata (dict): 元数据
        
    Returns:
        int: 记录ID
    """
```

##### get_ocr_history()
```python
def get_ocr_history(self, limit: int = 100,
                   start_date: datetime = None,
                   end_date: datetime = None) -> List[dict]:
    """
    获取OCR历史记录
    
    Args:
        limit (int): 返回记录数限制
        start_date (datetime): 开始日期
        end_date (datetime): 结束日期
        
    Returns:
        List[dict]: 历史记录列表
    """
```

##### save_performance_log()
```python
def save_performance_log(self, operation: str, 
                        duration: float,
                        metadata: dict = None) -> None:
    """
    保存性能日志
    
    Args:
        operation (str): 操作名称
        duration (float): 执行时间
        metadata (dict): 元数据
    """
```

### 6. Config (配置管理)

**文件位置**: `artalekey/core/config.py`

#### 类定义

```python
class Config:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_file (str): 配置文件路径
        """
```

#### 主要方法

##### get()
```python
def get(self, key: str, default=None):
    """
    获取配置值
    
    Args:
        key (str): 配置键，支持点号分隔的嵌套键
        default: 默认值
        
    Returns:
        配置值
        
    Example:
        ocr_engine = config.get('ocr.engine', 'easyocr')
    """
```

##### set()
```python
def set(self, key: str, value) -> None:
    """
    设置配置值
    
    Args:
        key (str): 配置键
        value: 配置值
    """
```

##### save()
```python
def save(self) -> None:
    """保存配置到文件"""
```

##### reload()
```python
def reload(self) -> None:
    """重新加载配置文件"""
```

## UI 模块 API

### 1. TabbedMainWindow (主窗口)

**文件位置**: `artalekey/ui/tabbed_main_window.py`

#### 类定义

```python
class TabbedMainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
```

#### 主要方法

##### add_tab()
```python
def add_tab(self, widget: QWidget, title: str, 
           icon: QIcon = None) -> int:
    """
    添加标签页
    
    Args:
        widget (QWidget): 标签页内容组件
        title (str): 标签页标题
        icon (QIcon): 标签页图标
        
    Returns:
        int: 标签页索引
    """
```

##### remove_tab()
```python
def remove_tab(self, index: int) -> None:
    """
    移除标签页
    
    Args:
        index (int): 标签页索引
    """
```

### 2. QtChartWidget (图表组件)

**文件位置**: `artalekey/ui/qt_chart_widget.py`

#### 类定义

```python
class QtChartWidget(QWidget):
    """图表显示组件"""
    
    def __init__(self, chart_type: str = "line"):
        """
        初始化图表组件
        
        Args:
            chart_type (str): 图表类型 ('line', 'bar', 'pie')
        """
```

#### 主要方法

##### update_data()
```python
def update_data(self, data: List[dict], 
               x_field: str = "x",
               y_field: str = "y") -> None:
    """
    更新图表数据
    
    Args:
        data (List[dict]): 数据列表
        x_field (str): X轴字段名
        y_field (str): Y轴字段名
    """
```

##### set_title()
```python
def set_title(self, title: str) -> None:
    """
    设置图表标题
    
    Args:
        title (str): 标题文本
    """
```

## 事件和回调

### 事件类型

```python
class EventType:
    """事件类型常量"""
    HOTKEY_PRESSED = "hotkey_pressed"
    WINDOW_CHANGED = "window_changed"
    OCR_COMPLETED = "ocr_completed"
    CONFIG_CHANGED = "config_changed"
```

### 回调函数签名

```python
# 快捷键回调
def hotkey_callback(hotkey_combo: str, event_data: dict) -> None:
    """快捷键按下回调"""

# 窗口变化回调
def window_callback(old_window: WindowInfo, 
                   new_window: WindowInfo) -> None:
    """窗口变化回调"""

# OCR完成回调
def ocr_callback(result: OCRResult, metadata: dict) -> None:
    """OCR识别完成回调"""
```

## 异常处理

### 自定义异常

```python
class ArtaleKeyException(Exception):
    """基础异常类"""

class HotkeyRegistrationError(ArtaleKeyException):
    """快捷键注册异常"""

class OCRProcessingError(ArtaleKeyException):
    """OCR处理异常"""

class WindowDetectionError(ArtaleKeyException):
    """窗口检测异常"""

class DatabaseError(ArtaleKeyException):
    """数据库异常"""
```

### 异常处理示例

```python
try:
    result = ocr.recognize_text(image_path)
except OCRProcessingError as e:
    logger.error(f"OCR处理失败: {e}")
    # 处理异常
except Exception as e:
    logger.error(f"未知错误: {e}")
    # 通用异常处理
```

## 配置文件格式

### config.yaml 示例

```yaml
# 应用程序配置
app:
  name: "ArtaleKey"
  version: "1.0.0"
  debug: false

# 快捷键配置
hotkeys:
  quick_up: "w+up"
  quick_down: "s+down"
  screenshot: "ctrl+shift+s"

# OCR配置
ocr:
  engine: "easyocr"
  languages: ["en", "ch_sim"]
  use_gpu: true
  cache_size: 100
  preprocessing:
    enhance_contrast: true
    denoise: true

# 窗口检测配置
window_detection:
  target_apps:
    - "MapleStory Worlds"
    - "Game.exe"
  monitor_interval: 1.0

# LLM配置
llm:
  model: "gpt-3.5-turbo"
  api_key: "your-api-key"
  max_tokens: 1000

# 数据库配置
database:
  path: "artalekey.db"
  backup_interval: 3600

# UI配置
ui:
  theme: "dark"
  window_size: [1200, 800]
  auto_save: true
```

## 使用示例

### 完整使用示例

```python
from artalekey.core.hotkey_manager import HotkeyManager
from artalekey.core.enhanced_ocr import EnhancedOCR
from artalekey.core.window_detector import WindowDetector
from artalekey.core.config import Config

# 初始化组件
config = Config()
hotkey_manager = HotkeyManager(config)
ocr = EnhancedOCR(use_gpu=True)
window_detector = WindowDetector(["MapleStory Worlds"])

# 定义回调函数
def handle_quick_up():
    """处理快速向上快捷键"""
    if window_detector.is_target_window(window_detector.get_active_window()):
        # 执行游戏操作
        print("执行快速向上操作")

def handle_screenshot():
    """处理截图快捷键"""
    # 截图并OCR识别
    screenshot_path = take_screenshot()
    result = ocr.recognize_text(screenshot_path)
    print(f"识别结果: {result.text}")

# 注册快捷键
hotkey_manager.register_hotkey("w+up", handle_quick_up)
hotkey_manager.register_hotkey("ctrl+shift+s", handle_screenshot)

# 开始监听
hotkey_manager.start_listening()

# 应用程序主循环
try:
    app.exec()
finally:
    hotkey_manager.stop_listening()
```

---

*最后更新: 2024年12月* 