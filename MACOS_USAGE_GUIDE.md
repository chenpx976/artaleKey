
# ArtaleKey macOS 应用使用指南

## 必需权限设置 ⚠️
ArtaleKey 需要以下三个关键权限才能正常工作：

### 1. 🔧 辅助功能权限（必需）
**用途**: 模拟按键操作和监听全局快捷键
**设置路径**: 
- 系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能
- 点击 🔒 解锁，然后添加 ArtaleKey.app

### 2. ⌨️ 输入监控权限（必需，macOS 10.15+）
**用途**: 检测全局快捷键组合
**设置路径**: 
- 系统偏好设置 → 安全性与隐私 → 隐私 → 输入监控
- 点击 🔒 解锁，然后添加 ArtaleKey.app

### 3. 📺 屏幕录制权限（必需）
**用途**: 截图和OCR文字识别功能
**设置路径**: 
- 系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制
- 点击 🔒 解锁，然后添加 ArtaleKey.app

## 🚀 启动方式
1. 双击 ArtaleKey.app 启动
2. 如果提示"无法打开"，右键点击 → 打开
3. 首次运行时会自动弹出权限请求对话框

## 🔧 故障排除
如果快捷键不工作：
1. ✅ 确认已授予上述三个权限
2. 🔄 重启应用程序
3. 🔄 重启系统（权限更改后可能需要）
4. 🔍 检查快捷键是否与系统快捷键冲突

## 📋 权限检查清单
- [ ] 辅助功能权限已授予
- [ ] 输入监控权限已授予  
- [ ] 屏幕录制权限已授予
- [ ] 应用已重启
- [ ] 快捷键测试正常

## 🔐 代码签名状态
- 如果应用已签名，将更稳定可靠
- 未签名的应用仍可使用，但需要手动授权

## 💻 命令行验证
验证应用权限：
```bash
spctl --assess --type execute -vvv "dist/ArtaleKey.app"
```

查看签名信息：
```bash
codesign -dv "dist/ArtaleKey.app"
```

检查权限状态：
```bash
# 检查辅助功能权限
sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "SELECT * FROM access WHERE service='kTCCServiceAccessibility';"

# 检查输入监控权限  
sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "SELECT * FROM access WHERE service='kTCCServiceListenEvent';"

# 检查屏幕录制权限
sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "SELECT * FROM access WHERE service='kTCCServiceScreenCapture';"
```
