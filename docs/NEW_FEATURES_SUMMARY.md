# ArtaleKey 新功能总结

## 概述

根据用户需求，我们对 ArtaleKey 进行了重大升级，实现了以下三个主要功能：

## 1. SQLite 数据库存储 OCR 数据

### 功能描述
- 将 OCR 识别的游戏数据（等级、经验、金钱）自动保存到 SQLite 数据库
- 提供数据历史记录查询和统计功能
- 支持数据清理和导出功能

### 实现文件
- `artalekey/core/database.py` - 数据库管理器
- `artalekey/core/enhanced_ocr.py` - 修改了 OCR 管理器以支持数据库保存

### 主要功能
- **数据存储**: 自动保存每次 OCR 识别的结果
- **数据查询**: 获取最新数据、历史数据、按日期范围查询
- **数据统计**: 总记录数、最高等级、时间范围等统计信息
- **数据管理**: 清理旧数据（默认30天前）、导出数据到 JSON

### 数据库结构
```sql
CREATE TABLE game_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level INTEGER,
    experience TEXT,
    money TEXT,
    raw_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 2. 标签页界面设计

### 功能描述
- 将不同的快捷键功能分到独立的标签页中
- 提供更清晰的功能分类和用户体验

### 实现文件
- `artalekey/ui/tabbed_main_window.py` - 新的标签页主窗口
- `artalekey/__main__.py` - 修改入口文件使用新窗口

### 标签页结构
1. **快速向上** - 快速向上功能的热键配置和控制
2. **OCR识别** - OCR 功能的配置和状态显示
3. **设置** - 目标应用设置和数据管理功能

### 特点
- 每个功能模块独立管理
- 清晰的功能分类
- 更好的用户体验

## 3. MapleStory Worlds 窗口状态监控

### 功能描述
- 实时监控 MapleStory Worlds 窗口的运行和激活状态
- 在应用程序顶部显示窗口状态信息
- 提供窗口激活功能

### 实现文件
- `artalekey/core/window_status.py` - 窗口状态监控器
- `artalekey/ui/window_status_widget.py` - 窗口状态显示组件

### 主要功能
- **状态监控**: 
  - ✅ 已激活 - MapleStory Worlds 窗口当前处于激活状态
  - ⚠️ 未激活 - 游戏正在运行但窗口未激活
  - ❌ 未运行 - 游戏未运行
- **窗口激活**: 点击按钮可以激活 MapleStory Worlds 窗口
- **游戏数据显示**: 显示最新的游戏数据（等级、经验、金钱）
- **数据库统计**: 显示数据库中的记录统计信息

### 状态显示
- 窗口状态实时更新（1秒检查间隔）
- 彩色状态指示器（绿色=激活，橙色=未激活，红色=未运行）
- 详细状态描述文本

## 技术实现亮点

### 1. 数据库设计
- 使用 SQLite 轻量级数据库
- 自动创建索引优化查询性能
- JSON 序列化存储复杂数据结构
- 支持数据清理和维护

### 2. 窗口状态监控
- 使用 QTimer 实现定时检查
- 基于信号槽机制的状态更新
- 跨平台窗口检测（重点支持 macOS）
- 高效的窗口状态缓存

### 3. 用户界面优化
- 标签页设计提供更好的功能组织
- 实时状态显示和数据更新
- 响应式布局和自适应样式
- 原生系统样式集成

## 使用方法

### 启动应用
```bash
python -m artalekey
```

### 功能使用
1. **窗口状态监控**: 应用启动后自动开始监控，显示在界面顶部
2. **快速向上功能**: 在"快速向上"标签页中配置和启用
3. **OCR识别**: 在"OCR识别"标签页中配置，数据自动保存到数据库
4. **数据管理**: 在"设置"标签页中进行数据清理和导出

### 数据查看
- 窗口状态组件显示最新游戏数据
- 数据库统计信息实时更新
- 支持导出历史数据到 JSON 文件

## 配置文件

所有配置自动保存，包括：
- 热键配置
- OCR 设置
- 窗口过滤配置
- UI 状态（窗口大小、位置等）

## 文件结构

```
artalekey/
├── core/
│   ├── database.py          # 数据库管理
│   ├── window_status.py     # 窗口状态监控
│   ├── enhanced_ocr.py      # OCR管理（已修改）
│   └── ...
├── ui/
│   ├── tabbed_main_window.py    # 标签页主窗口
│   ├── window_status_widget.py  # 窗口状态组件
│   └── ...
└── __main__.py              # 入口文件（已修改）
```

## 数据存储

```
ocr_data/
├── game_data.db            # SQLite 数据库
├── screenshots/            # 截图文件
├── ocr_results/           # OCR 结果 JSON
└── annotated_images/      # 标注图像
```

这次升级大大提升了 ArtaleKey 的功能性和用户体验，提供了完整的游戏数据管理解决方案。 