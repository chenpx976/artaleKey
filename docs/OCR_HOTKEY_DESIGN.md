# OCR快捷键设计说明

## 设计概述

OCR快捷键设计参考了主要的`HotkeyCard`组件设计模式，创建了专门的`OCRHotkeyCard`组件，提供了统一、直观的OCR功能配置界面。

## 设计特点

### 1. 组件化设计
- **独立组件**: `OCRHotkeyCard`作为独立的UI组件
- **信号机制**: 使用PyQt6的信号槽机制进行通信
- **防抖处理**: 150ms防抖机制，避免频繁配置更新

### 2. 参考HotkeyCard的设计模式
- **布局结构**: 采用相同的垂直布局和分组设计
- **控件样式**: 统一的标签、滑块、复选框样式
- **配置管理**: 相同的`get_config()`和`set_config()`方法
- **信号处理**: 相同的防抖和配置变更信号机制

## 功能特性

### 1. 基础配置
- **启用开关**: 控制OCR功能的总开关
- **触发键设置**: 下拉选择框，支持字母和数字键
- **目标窗口**: 可配置的目标窗口名称
- **截图间隔**: 5-60秒可调节的截图间隔

### 2. 高级选项
- **保存截图**: 控制是否保存原始截图文件
- **启动截图**: 控制启动时是否立即截图
- **窗口截图**: 控制是否只截取目标窗口

### 3. 快捷键选项
```python
# OCR常用快捷键（优先显示）
ocr_keys = ['s', 'o', 'c', 'r', 'p', 'i', 'u', 'y']

# 其他字母键
other_letters = [a-z] - ocr_keys

# 数字键
number_keys = ['0'-'9']
```

## 界面布局

```
┌─ OCR快捷键设置 ─────────────────────────┐
│ ☐ 启用OCR功能                          │
│                                        │
│ OCR触发键: [s ▼] （仅在目标窗口激活时有效）│
│                                        │
│ 截图间隔: 10秒                         │
│ ├─────────●─────────┤ [5-60秒]        │
│                                        │
│ 目标窗口: [MapleStory Worlds]          │
│                                        │
│ ┌─ 高级选项 ─────────────────────────┐  │
│ │ ☑ 保存截图文件                     │  │
│ │ ☑ 启动时立即截图                   │  │
│ │ ☑ 仅截取目标窗口                   │  │
│ └────────────────────────────────────┘  │
└────────────────────────────────────────┘
```

## 配置数据结构

```python
{
    'enabled': bool,                    # 是否启用OCR功能
    'trigger_key': str,                 # 触发键（默认's'）
    'interval': int,                    # 截图间隔（秒，默认10）
    'target_window': str,               # 目标窗口（默认'MapleStory Worlds'）
    'save_screenshots': bool,           # 是否保存截图（默认True）
    'immediate_capture_on_start': bool, # 启动时立即截图（默认True）
    'capture_window_only': bool,        # 仅截取目标窗口（默认True）
    'output_folder': str                # 输出文件夹（默认'ocr_data'）
}
```

## 集成方式

### 1. 主窗口集成
```python
# 替换原有的简单输入框
self.ocr_card = OCRHotkeyCard()
control_layout.addWidget(self.ocr_card)

# 信号连接
self.ocr_card.config_changed.connect(self.on_ocr_config_changed)
```

### 2. 配置管理
```python
# 加载配置
ocr_config = config_manager.get('screenshot_ocr', {})
self.ocr_card.set_config(ocr_config)

# 保存配置
ocr_config = self.ocr_card.get_config()
config_manager.set('screenshot_ocr', ocr_config)
```

### 3. 热键监听器更新
```python
def on_ocr_config_changed(self, config):
    # 更新热键监听器
    self.hotkey_listener.set_ocr_trigger_key(config.get('trigger_key', 's'))
    self.hotkey_listener.set_target_window_name(config.get('target_window', 'MapleStory Worlds'))
```

## 优势对比

### 原有设计 vs 新设计

| 特性 | 原有设计 | 新设计 |
|------|----------|--------|
| 界面复杂度 | 简单输入框 | 完整配置面板 |
| 配置选项 | 基础（开关+快捷键） | 全面（8个配置项） |
| 用户体验 | 基础 | 专业 |
| 维护性 | 分散的控件 | 组件化管理 |
| 扩展性 | 有限 | 良好 |
| 一致性 | 独立设计 | 与HotkeyCard一致 |

## 技术实现

### 1. 组件继承
```python
class OCRHotkeyCard(QGroupBox):
    config_changed = pyqtSignal(dict)
```

### 2. 防抖机制
```python
self._debounce_timer = QTimer()
self._debounce_timer.setSingleShot(True)
self._debounce_timer.timeout.connect(self._emit_config_changed)
```

### 3. 信号阻塞
```python
def set_config(self, config: dict):
    # 阻塞信号避免循环触发
    self.enabled_check.blockSignals(True)
    # ... 设置配置
    self.enabled_check.blockSignals(False)
```

## 使用说明

### 1. 基础使用
1. 勾选"启用OCR功能"
2. 选择合适的触发键（默认's'）
3. 设置截图间隔（默认10秒）
4. 确认目标窗口名称

### 2. 高级配置
- **保存截图**: 用于调试和分析
- **启动截图**: 立即验证OCR功能
- **窗口截图**: 提高识别精度

### 3. 快捷键选择建议
- **'s'**: 默认选择，代表Screenshot
- **'o'**: OCR的首字母
- **'c'**: Capture的首字母
- **数字键**: 避免与游戏快捷键冲突

## 故障排除

### 1. 配置不生效
- 检查是否勾选"启用OCR功能"
- 确认目标窗口名称正确
- 验证快捷键是否与其他功能冲突

### 2. 界面显示问题
- 确保导入了`OCRHotkeyCard`组件
- 检查PyQt6版本兼容性
- 验证信号连接是否正确

### 3. 配置丢失
- 检查配置文件权限
- 确认`config_manager`正常工作
- 验证配置保存时机

---

**设计日期**: 2025-05-26  
**参考组件**: HotkeyCard  
**技术栈**: PyQt6, Python 3.11+  
**兼容性**: 向后兼容现有配置 