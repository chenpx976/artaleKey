# ArtaleKey macOS App 打包指南

## 📋 前提条件

### 系统要求
- macOS 10.15+ (Catalina或更高版本)
- Python 3.8+ 
- Xcode Command Line Tools

### 检查Python版本
```bash
python3 --version  # 应该显示3.8+
```

### 安装Xcode Command Line Tools（如果没有）
```bash
xcode-select --install
```

## 🚀 快速打包步骤

### 1. 安装打包依赖
```bash
# 安装打包所需的依赖
pip install -r requirements-build.txt
```

### 2. 运行打包脚本
```bash
# 在项目根目录运行
python build_macos_app.py
```

### 3. 查看结果
打包成功后，您会在以下位置找到：
- **应用程序**: `dist/ArtaleKey.app`
- **打包配置**: `ArtaleKey.spec`
- **图标指南**: `assets/icon_guide.md`
- **DMG指南**: `DMG_GUIDE.md`

## 📱 使用打包后的应用

### 首次运行
1. 双击 `dist/ArtaleKey.app` 启动应用
2. 如果提示"无法打开，因为无法验证开发者"：
   - 右键点击应用 -> 打开
   - 或在终端运行：`xattr -dr com.apple.quarantine dist/ArtaleKey.app`

### 授予权限
应用首次运行时需要以下权限：

#### 辅助功能权限
1. 打开 **系统偏好设置** -> **安全性与隐私** -> **隐私**
2. 选择 **辅助功能**
3. 点击锁图标解锁设置
4. 点击 **+** 添加 ArtaleKey.app
5. 确保 ArtaleKey 被勾选

#### 输入监控权限（如果需要）
1. 在 **安全性与隐私** -> **隐私** 中
2. 选择 **输入监控**
3. 添加并启用 ArtaleKey.app

## 🎨 自定义应用图标

### 1. 准备图标文件
- 创建 1024x1024 像素的PNG图像
- 保存为 `icon.png`

### 2. 转换为icns格式
```bash
# 创建iconset目录
mkdir ArtaleKey.iconset

# 生成各种尺寸
sips -z 16 16     icon.png --out ArtaleKey.iconset/icon_16x16.png
sips -z 32 32     icon.png --out ArtaleKey.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out ArtaleKey.iconset/icon_32x32.png
sips -z 64 64     icon.png --out ArtaleKey.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out ArtaleKey.iconset/icon_128x128.png
sips -z 256 256   icon.png --out ArtaleKey.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out ArtaleKey.iconset/icon_256x256.png
sips -z 512 512   icon.png --out ArtaleKey.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out ArtaleKey.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out ArtaleKey.iconset/icon_512x512@2x.png

# 生成icns文件
iconutil -c icns ArtaleKey.iconset

# 移动到正确位置
mkdir -p assets
mv ArtaleKey.icns assets/icon.icns

# 重新打包
python build_macos_app.py
```

## 📦 创建DMG安装包

### 方法1：使用create-dmg（推荐）
```bash
# 安装工具
brew install create-dmg

# 创建DMG
create-dmg \
  --volname "ArtaleKey" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "ArtaleKey.app" 200 190 \
  --hide-extension "ArtaleKey.app" \
  --app-drop-link 600 185 \
  "ArtaleKey-1.0.0.dmg" \
  "dist/"
```

### 方法2：手动创建
1. 打开 **磁盘工具**
2. **文件** -> **新建映像** -> **空白映像**
3. 设置映像名称和大小（100MB足够）
4. 挂载映像后，将 `ArtaleKey.app` 拖入
5. 创建 **应用程序** 文件夹的别名拖入
6. 调整图标位置和窗口大小
7. **文件** -> **新建映像** -> **从文件夹创建**

## 🔧 高级配置

### 自定义Info.plist
编辑 `ArtaleKey.spec` 文件中的 `info_plist` 部分：

```python
info_plist={
    'CFBundleName': 'ArtaleKey',
    'CFBundleDisplayName': 'ArtaleKey',
    'CFBundleVersion': "1.0.0",
    'CFBundleShortVersionString': "1.0.0",
    # 添加更多自定义设置...
}
```

### 代码签名（分发时推荐）
```bash
# 签名应用（需要开发者证书）
codesign --force --sign "Developer ID Application: Your Name" \
  --options runtime dist/ArtaleKey.app

# 验证签名
codesign --verify --verbose dist/ArtaleKey.app
```

### 公证（App Store外分发必需）
```bash
# 创建zip包
ditto -c -k --keepParent dist/ArtaleKey.app ArtaleKey.zip

# 提交公证
xcrun altool --notarize-app \
  --primary-bundle-id "com.chenpx976.artalekey" \
  --username "your-apple-id@example.com" \
  --password "@keychain:AC_PASSWORD" \
  --file ArtaleKey.zip
```

## 🐛 常见问题

### Q: 打包失败，提示缺少模块
**A**: 检查 `hiddenimports` 列表，添加缺少的模块：
```python
hiddenimports=[
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    # 添加其他缺少的模块
]
```

### Q: 应用启动时闪退
**A**: 在终端运行应用查看错误信息：
```bash
./dist/ArtaleKey.app/Contents/MacOS/ArtaleKey
```

### Q: 应用体积太大
**A**: 优化打包配置：
1. 添加更多 `excludes`
2. 使用 `--onefile` 选项
3. 排除不必要的库

### Q: 权限问题
**A**: 确保：
1. 已添加辅助功能权限
2. 应用签名正确
3. 使用 `xattr -dr com.apple.quarantine` 移除隔离属性

## 📋 打包清单

打包前检查：
- [ ] Python虚拟环境已激活
- [ ] 所有依赖已安装
- [ ] 代码功能测试正常
- [ ] 图标文件已准备（可选）

打包后验证：
- [ ] 应用可以正常启动
- [ ] 所有功能正常工作
- [ ] 权限请求正常显示
- [ ] 应用图标显示正确

分发前：
- [ ] 代码签名（如果需要）
- [ ] 公证处理（如果需要）
- [ ] DMG安装包创建
- [ ] 在其他Mac上测试

## 🎯 最佳实践

1. **测试环境**：在干净的macOS环境中测试打包后的应用
2. **版本管理**：每次打包前更新版本号
3. **依赖管理**：定期更新 `requirements.txt`
4. **错误日志**：保留打包过程的日志用于问题诊断
5. **用户反馈**：收集用户使用反馈，持续改进

---

🎉 **恭喜！现在您可以将ArtaleKey打包为专业的macOS应用程序了！** 