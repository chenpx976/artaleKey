# macOS 快捷键问题解决方案

## 问题描述

在 macOS 上，使用 PyInstaller 打包的 ArtaleKey 应用在双击启动后，快捷键监听功能不工作，但命令行启动时正常。

## 问题原因

macOS 的安全机制要求应用程序必须：
1. **进行代码签名** - 未签名的应用无法获得敏感权限
2. **正确声明权限** - 在 Info.plist 中声明所需权限
3. **使用 entitlements** - 通过权限文件申请必要的系统访问权限

## 解决方案

### 1. 权限配置文件已自动创建

项目现在包含以下关键文件：

- `entitlements.plist` - 系统权限申请文件
- 更新的 `ArtaleKey.spec` - 包含完整的权限声明
- 更新的 `build_macos_app.py` - 支持自动代码签名

### 2. 重新打包应用

运行更新后的打包脚本：

```bash
python build_macos_app.py
```

### 3. 系统权限设置

应用首次启动时，需要在系统偏好设置中授予以下权限：

#### 辅助功能权限
- 打开：系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能
- 点击左下角锁图标解锁
- 点击 "+" 按钮，添加 `ArtaleKey.app`
- 确保复选框已勾选

#### 输入监控权限（macOS 10.15+）
- 打开：系统偏好设置 → 安全性与隐私 → 隐私 → 输入监控
- 点击左下角锁图标解锁
- 点击 "+" 按钮，添加 `ArtaleKey.app`
- 确保复选框已勾选

#### 屏幕录制权限（如果使用OCR功能）
- 打开：系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制
- 点击左下角锁图标解锁
- 点击 "+" 按钮，添加 `ArtaleKey.app`
- 确保复选框已勾选

### 4. 启动应用

1. **首次启动**：右键点击 `ArtaleKey.app` → 打开
2. **后续启动**：可以直接双击启动

### 5. 验证解决方案

#### 命令行验证
```bash
# 验证应用权限
spctl --assess --type execute -vvv "dist/ArtaleKey.app"

# 查看签名信息
codesign -dv "dist/ArtaleKey.app"

# 检查权限声明
plutil -p "dist/ArtaleKey.app/Contents/Info.plist" | grep Usage
```

#### 功能测试
1. 启动应用
2. 测试快捷键监听功能
3. 确认全局快捷键响应正常

## 技术细节

### entitlements.plist 内容
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
</dict>
</plist>
```

### 新增的 Info.plist 权限声明
- `NSAccessibilityUsageDescription` - 辅助功能权限
- `NSInputMonitoringUsageDescription` - 输入监控权限
- `NSScreenCaptureUsageDescription` - 屏幕录制权限

### 代码签名
应用现在会自动进行代码签名：
- 如果有开发者证书，使用开发者证书签名
- 否则使用临时签名（ad-hoc signing）

## 故障排除

### 如果快捷键仍不工作

1. **确认权限设置**
   - 检查所有权限是否已授予
   - 尝试移除并重新添加应用权限

2. **重启应用**
   - 完全关闭应用
   - 重新启动应用

3. **重启系统**
   - 权限更改后可能需要重启系统才能生效

4. **检查应用签名**
   ```bash
   codesign -dv dist/ArtaleKey.app
   ```

5. **查看系统日志**
   ```bash
   log show --predicate 'process == "ArtaleKey"' --last 1h
   ```

### 常见错误

#### "应用程序无法打开"
- **原因**：应用未签名或签名验证失败
- **解决**：右键点击 → 打开，或重新签名应用

#### "权限被拒绝"
- **原因**：未授予必要的系统权限
- **解决**：在系统偏好设置中正确授予权限

#### "快捷键监听不响应"
- **原因**：缺少输入监控权限
- **解决**：添加输入监控权限并重启应用

## 开发者证书签名（可选）

如果有 Apple 开发者账户，可以使用开发者证书进行签名：

```bash
# 使用开发者证书签名
codesign -s "Developer ID Application: Your Name" \
  --deep --force --options runtime \
  --entitlements entitlements.plist \
  "dist/ArtaleKey.app"
```

开发者证书签名的应用：
- 更高的系统信任级别
- 用户体验更好
- 可以进行公证（notarization）

## 总结

通过以下改进，已解决 macOS 快捷键监听问题：

1. ✅ 添加了 `entitlements.plist` 权限文件
2. ✅ 更新了 Info.plist 权限声明
3. ✅ 实现了自动代码签名
4. ✅ 提供了完整的权限配置指南

现在打包的应用应该能够正常进行全局快捷键监听了！ 