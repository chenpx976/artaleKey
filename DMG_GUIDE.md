
# DMG 自动创建说明

## 🚀 自动创建 DMG

构建脚本已自动创建 DMG 文件！无需手动操作。

## 📦 DMG 创建方式

### 方式1：create-dmg 工具（推荐）
如果系统安装了 `create-dmg` 工具，会自动使用高级方式创建：
```bash
brew install create-dmg
```

特点：
- ✅ 精美的图标布局
- ✅ 拖拽到 Applications 快捷方式
- ✅ 自定义窗口大小和背景

### 方式2：系统默认 hdiutil
如果没有 `create-dmg`，会使用系统自带的 `hdiutil` 创建：

特点：
- ✅ 无需额外工具
- ✅ 包含 Applications 符号链接
- ✅ 自动计算合适大小

## 📁 DMG 内容

- `ArtaleKey.app` - 应用程序（不带版本号）
- `Applications` - 应用程序文件夹快捷方式  
- `MACOS_USAGE_GUIDE.md` - 使用指南

## 🔢 文件命名

- DMG 文件：`ArtaleKey-{version}-macOS.dmg`（带版本号）
- 内部 APP：`ArtaleKey.app`（不带版本号）

## 💡 安装方式

用户只需：
1. 下载并打开 DMG 文件
2. 将 ArtaleKey.app 拖拽到 Applications 文件夹
3. 在启动台中找到并启动应用

## 🔐 分发注意事项

- 已签名应用：用户可直接运行
- 未签名应用：需要用户手动允许（右键 → 打开）
- 首次运行会请求必要的系统权限
