# OCR 测试指南

本指南介绍如何使用项目中的 OCR 测试脚本，包括 Tesseract 和 EasyOCR 两种技术的测试与对比。

## 概述

项目支持两种主要的 OCR 技术：

- **Tesseract**: 传统的开源 OCR 引擎，配置灵活，支持多种语言
- **EasyOCR**: 基于深度学习的 OCR 库，识别精度高，提供置信度信息

## 环境要求

### Tesseract 安装

1. 确保安装了 Homebrew：
```bash
/opt/homebrew/bin/brew install tesseract tesseract-lang
```

2. 验证安装：
```bash
/opt/homebrew/bin/tesseract --list-langs
```

应该看到支持的语言包括：
- `chi_sim` - 简体中文
- `chi_tra` - 繁体中文
- `eng` - 英文

### EasyOCR 依赖

项目已经安装了 EasyOCR 相关依赖：
- `easyocr`
- `torch`
- `numpy`
- `PIL`

## 测试脚本说明

### 1. Tesseract 基础测试 (`tests/test_tesseract.py`)

测试 Tesseract 的多语言识别能力：

```bash
cd tests
python test_tesseract.py
```

**功能特点：**
- 测试英文、简体中文、繁体中文识别
- 图片预处理（灰度化、对比度增强、锐化）
- 详细的统计信息输出

### 2. 中文优化测试 (`tests/chinese_ocr_test.py`)

专门针对中文优化的 Tesseract 测试：

```bash
cd tests
python chinese_ocr_test.py
```

**功能特点：**
- 使用最佳的中文识别配置
- PSM 模式优化（`--psm 6`）
- 中文字符统计
- 图片预处理优化

### 3. EasyOCR 测试 (`tests/easyocr_test.py`)

基于深度学习的 OCR 测试：

```bash
cd tests
python easyocr_test.py
```

**功能特点：**
- 支持简体中文、繁体中文、英文
- 置信度评估（只显示 >0.5 的结果）
- 文本块定位信息
- RGB 图片预处理

### 4. OCR 技术对比 (`tests/ocr_comparison.py`)

比较 Tesseract 和 EasyOCR 的性能：

```bash
cd tests
python ocr_comparison.py
```

**功能特点：**
- 同时测试两种技术
- 性能对比（处理时间、识别精度）
- 中文字符识别数量对比
- 综合建议输出

## 测试结果解读

### Tesseract 结果

- **处理速度**: 快（约 1-2 秒）
- **配置灵活性**: 高
- **中文识别**: 中等（需要良好的图片预处理）
- **输出格式**: 纯文本

### EasyOCR 结果

- **处理速度**: 较慢（约 10-15 秒，首次需要下载模型）
- **中文识别**: 优秀（识别出更多中文字符）
- **置信度**: 提供每个文本块的置信度
- **文本定位**: 提供精确的边界框坐标
- **输出格式**: 结构化数据

## 实际应用建议

### 游戏界面 OCR

对于类似 MapleStory 的游戏界面：

1. **推荐使用 EasyOCR + 繁体中文配置**
   - 更好的中文识别率
   - 置信度筛选功能

2. **Tesseract 适用场景**
   - 需要快速处理
   - 对识别精度要求不高
   - 批量处理场景

### 配置优化

1. **图片预处理**
   - 对比度增强
   - 锐化处理
   - 合适的色彩模式转换

2. **语言配置**
   - 游戏界面：`['ch_tra', 'en']`
   - 中文文档：`['ch_sim', 'en']`
   - 英文文档：`['en']`

3. **置信度阈值**
   - 高精度需求：>0.7
   - 平衡模式：>0.5
   - 最大召回：>0.3

## 性能优化建议

### 提升识别精度

1. **图片质量优化**
   - 确保足够的分辨率
   - 良好的对比度
   - 清晰的字体

2. **预处理参数调整**
   - 调整对比度增强系数
   - 尝试不同的锐化参数
   - 考虑图片缩放

3. **语言配置**
   - 根据实际内容选择语言包
   - 避免不必要的语言组合

### 提升处理速度

1. **Tesseract 优化**
   - 使用合适的 PSM 模式
   - 限制识别区域
   - 调整 OEM 参数

2. **EasyOCR 优化**
   - 使用 GPU 加速（如果可用）
   - 复用 Reader 实例
   - 合理设置置信度阈值

## 故障排除

### 常见问题

1. **Tesseract 找不到命令**
   ```bash
   export PATH="/opt/homebrew/bin:$PATH"
   ```

2. **中文字符显示乱码**
   - 确保终端支持 UTF-8
   - 检查语言包安装

3. **EasyOCR 初始化失败**
   - 检查网络连接（首次需要下载模型）
   - 确保有足够的磁盘空间

4. **内存不足**
   - 减少并发处理
   - 使用图片压缩

### 调试模式

可以在脚本中添加更详细的日志输出：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展使用

### 批量处理

可以修改脚本来处理整个目录的图片：

```python
import glob

image_files = glob.glob("./ocr_data/screenshots/*.png")
for image_file in image_files:
    # 处理每个图片文件
    pass
```

### 集成到主项目

这些测试脚本可以作为参考，集成到 `artalekey/core/` 模块中，为主项目提供 OCR 功能。

## 总结

- **EasyOCR** 适合对识别精度要求高的场景
- **Tesseract** 适合对速度要求高的场景
- 根据实际需求选择合适的技术栈
- 图片预处理是提升识别效果的关键 