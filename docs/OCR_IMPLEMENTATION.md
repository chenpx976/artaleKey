# OCR 实现说明

## 概述
ArtaleKey 使用 EasyOCR 进行文本识别，支持英语(en)和繁体中文(ch_tra)两种语言。

## 实现特点

### 语言支持
- **英语 (en)**: 识别英文文本
- **繁体中文 (ch_tra)**: 识别繁体中文文本
- **同时支持**: EasyOCR 同时加载两种语言，自动识别文本语言

### 核心功能
1. **自动截图**: 监控目标窗口，定时截图
2. **文本识别**: 使用 EasyOCR 识别截图中的文本
3. **数据提取**: 从识别结果中提取游戏数据（等级、经验、金钱等）
4. **结果可视化**: 生成带标注的图像，显示识别区域和文本

### 配置说明
```json
{
  "screenshot_ocr": {
    "enabled": false,
    "trigger_key": "s",
    "interval": 10,
    "target_window": "MapleStory Worlds",
    "output_folder": "ocr_data",
    "save_screenshots": true,
    "immediate_capture_on_start": true,
    "capture_window_only": true
  }
}
```

### 使用方法
1. 启用 OCR 功能
2. 设置快捷键（默认 's'）
3. 在目标窗口激活时按快捷键开始/停止监控
4. 查看 `ocr_data` 文件夹中的结果

### 输出文件
- `screenshots/`: 原始截图
- `ocr_results/`: JSON 格式的识别结果
- `annotated_images/`: 带标注的可视化图像
- `game_data_summary.json`: 汇总数据

## 测试方法
运行应用程序：
```bash
python -m artalekey
``` 