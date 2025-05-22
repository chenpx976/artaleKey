# ArtaleKey

ArtaleKey 是一个现代化的快捷键管理工具，使用 PyQt6 构建，提供了直观的用户界面和强大的快捷键管理功能。

## 特性

- 现代化的用户界面
- 支持全局快捷键监听
- 可自定义按键组合
- 灵活的按键模拟
- 配置保存和加载
- 多样化的按键操作模式

## 安装

1. 确保你已安装 Python 3.8 或更高版本
2. 安装 uv 包管理器：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. 克隆仓库：
```bash
git clone https://github.com/yourusername/artalekey.git
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

## 运行

```bash
python -m artalekey
```

## 使用说明

1. 启动应用程序后，点击"添加新快捷键"按钮创建新的快捷键配置
2. 在快捷键卡片中设置：
   - 触发键
   - 长按触发时间
   - 按键间隔时间
3. 使用全局开关控制所有快捷键的启用状态
4. 可以通过文件菜单保存和加载配置

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可

MIT License 