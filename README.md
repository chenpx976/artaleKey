# ArtaleKey - 快捷键管理器

MacOS 游戏快捷键辅助工具，专为 MapleStory Worlds 等游戏优化。

## 🚀 快速启动

### 推荐启动方式
```bash
python -m artalekey
```

### 备选启动方式
```bash
python run_artalekey.py
```

## ⚙️ 快速设置

1. **启用快速向上功能** ✓
2. **启用窗口过滤** ✓  
3. **点击"使用默认应用"** ✓
4. **在游戏中使用 W+↑ 快捷键** 🎮

## 📁 项目结构

```
artalekey/
├── artalekey/              # 核心代码
│   ├── ui/                 # 用户界面
│   ├── core/               # 核心功能
│   └── __main__.py         # 主入口
├── docs/                   # 文档
│   ├── 启动说明.md
│   ├── UI_IMPROVEMENT_COMPARISON.md
│   └── ...
├── tests/                  # 测试脚本
│   ├── simple_native_ui_test.py
│   ├── test_performance.py
│   └── ...
├── scripts/                # 实用脚本
│   ├── simple_ui_summary.py
│   └── ...
├── run_artalekey.py        # 简洁启动脚本
├── requirements.txt        # 依赖
└── README.md              # 本文件
```

## 📚 文档

详细文档请查看 `docs/` 目录：
- **[macOS打包指南](docs/macOS打包指南.md)** - 完整的App打包说明
- **[项目结构整理说明](docs/项目结构整理说明.md)** - 项目结构说明
- **[性能优化报告](docs/PERFORMANCE_OPTIMIZATION_REPORT.md)** - 性能优化详情

## 🧪 测试

测试脚本位于 `tests/` 目录：
```bash
# UI测试
python tests/simple_native_ui_test.py

# 性能测试  
python tests/test_performance.py

# 窗口检测测试
python tests/test_window_detection.py
```

## 🔧 开发

实用脚本位于 `scripts/` 目录：
```bash
# UI改进总结
python scripts/simple_ui_summary.py

# 修复验证
python scripts/apply_ui_fixes.py
```

## 📦 打包为macOS App

### 快速打包
```bash
# 1. 安装打包依赖
pip install -r requirements-build.txt

# 2. 运行打包脚本
python build_macos_app.py

# 3. 查看结果
# 应用程序: dist/ArtaleKey.app
```

### 详细说明
- **[macOS打包指南](docs/macOS打包指南.md)** - 完整的打包教程
- **[MACOS_BUILD_SUMMARY.md](MACOS_BUILD_SUMMARY.md)** - 打包方案总结
- **[APP_FIX_SOLUTION.md](APP_FIX_SOLUTION.md)** - App启动问题解决方案

包括：
- 🎨 自定义应用图标
- 📦 创建DMG安装包  
- 🔐 代码签名和公证
- 🐛 常见问题解决

## 📋 依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- PyQt6 - GUI框架
- psutil - 系统进程监控

## 安装

1. 确保你已安装 Python 3.8 或更高版本
2. 安装 uv 包管理器：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. 克隆仓库：
```bash
git clone https://github.com/chenpx976/artaleKey
cd artalekey
```

4. 使用 uv 安装依赖：
```bash
uv venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
uv pip install -r requirements.txt
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可

MIT License 