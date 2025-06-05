#!/usr/bin/env python3
"""
ArtaleKey macOS App 打包脚本
使用PyInstaller创建独立的macOS应用程序
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """检查打包依赖"""
    print("🔍 检查打包依赖...")
    
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller 未安装")
        print("💡 安装命令: pip install pyinstaller")
        return False
        
    try:
        import PyQt6
        print(f"✅ PyQt6 已安装")
    except ImportError:
        print("❌ PyQt6 未安装")
        return False
        
    try:
        from PyQt6 import QtCharts
        print(f"✅ PyQt6-Charts 已安装")
    except ImportError:
        print("❌ PyQt6-Charts 未安装")
        print("💡 安装命令: pip install PyQt6-Charts")
        return False
        
    return True

def create_spec_file():
    """创建PyInstaller规格文件"""
    print("📝 创建打包配置文件...")
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 项目根目录
project_root = Path.cwd()

a = Analysis(
    ['artalekey/__main__.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # 包含配置和资源文件
        ('artalekey/core', 'artalekey/core'),
        ('artalekey/ui', 'artalekey/ui'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtCharts',
        'psutil',
        'pynput',
        'AppKit',
        'Cocoa',
        'Foundation',
        'Quartz',
        'objc',
        # Qt Charts相关
        'PyQt6.QtCharts',
        'numpy',
        # LLM相关依赖 - 使用requests
        'requests',
        'yaml',
        'json',
        're',
        'base64',
        'typing',
        'concurrent.futures',
        'threading',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ArtaleKey',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements.plist',
    icon='assets/icon.icns' if Path('assets/icon.icns').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ArtaleKey',
)

app = BUNDLE(
    coll,
    name='ArtaleKey.app',
    icon='assets/icon.icns' if Path('assets/icon.icns').exists() else None,
    bundle_identifier='com.chenpx976.artalekey',
    version='1.0.0',
    info_plist={{
        'CFBundleName': 'ArtaleKey',
        'CFBundleDisplayName': 'ArtaleKey',
        'CFBundleGetInfoString': "ArtaleKey - 快捷键管理器",
        'CFBundleIdentifier': "com.chenpx976.artalekey",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.utilities',
        'NSRequiresAquaSystemAppearance': False,
        # 必要的权限声明
        'NSAccessibilityUsageDescription': 'ArtaleKey需要辅助功能权限来模拟按键和监听全局快捷键',
        'NSAppleEventsUsageDescription': 'ArtaleKey需要AppleScript权限来检测窗口状态',
        # 新增：输入监听权限（macOS 10.15+）
        'NSInputMonitoringUsageDescription': 'ArtaleKey需要输入监听权限来检测全局快捷键组合',
        # 文件访问权限（如果需要）
        'NSDesktopFolderUsageDescription': 'ArtaleKey需要访问桌面以进行截图和OCR功能',
        'NSDocumentsFolderUsageDescription': 'ArtaleKey需要访问文档文件夹以保存配置和日志',
        # 摄像头访问权限（如果使用截图功能）
        'NSCameraUsageDescription': 'ArtaleKey需要屏幕录制权限来进行截图和OCR功能',
        # 屏幕录制权限（macOS 10.15+）
        'NSScreenCaptureUsageDescription': 'ArtaleKey需要屏幕录制权限来进行截图和OCR功能',
    }},
)
'''
    
    with open('ArtaleKey.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ 配置文件已创建: ArtaleKey.spec")
    return True

def create_app_icon():
    """创建应用图标"""
    print("🎨 创建应用图标...")
    
    # 创建assets目录
    assets_dir = Path('assets')
    assets_dir.mkdir(exist_ok=True)
    
    # 如果有图标文件，复制到assets目录
    # 这里我们创建一个简单的图标说明
    icon_info = '''
# ArtaleKey 应用图标

如果您想为应用添加自定义图标，请：

1. 准备一个1024x1024像素的PNG图标文件
2. 使用以下命令转换为.icns格式：

```bash
# 创建iconset目录
mkdir ArtaleKey.iconset

# 生成不同尺寸的图标
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

# 生成.icns文件
iconutil -c icns ArtaleKey.iconset

# 移动到assets目录
mv ArtaleKey.icns assets/icon.icns
```

3. 重新运行打包脚本
'''
    
    with open(assets_dir / 'icon_guide.md', 'w', encoding='utf-8') as f:
        f.write(icon_info)
    
    print("✅ 图标指南已创建: assets/icon_guide.md")

def build_app():
    """构建应用程序"""
    print("🔨 开始构建macOS应用...")
    
    # 清理之前的构建
    for path in ['build', 'dist']:
        if os.path.exists(path):
            print(f"🧹 清理 {path} 目录...")
            shutil.rmtree(path)
    
    # 运行PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm', 
        'ArtaleKey.spec'
    ]
    
    print(f"🚀 执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 构建成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败:")
        print(f"错误输出: {e.stderr}")
        return False

def check_developer_id():
    """检查是否有开发者证书"""
    try:
        result = subprocess.run([
            'security', 'find-identity', '-v', '-p', 'codesigning'
        ], capture_output=True, text=True)
        
        if 'Developer ID Application' in result.stdout:
            # 提取证书名称
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'Developer ID Application' in line:
                    cert_name = line.split('"')[1]
                    return cert_name
        return None
    except:
        return None

def sign_app(app_path: Path, cert_name: str = None):
    """代码签名应用程序"""
    print("🔏 开始代码签名...")
    
    if not cert_name:
        cert_name = check_developer_id()
        if not cert_name:
            print("⚠️  未找到开发者证书，使用临时签名")
            cert_name = "-"  # 使用临时签名
    
    try:
        # 签名命令
        cmd = [
            'codesign',
            '-s', cert_name,
            '--deep',
            '--force',
            '--options', 'runtime',
            '--entitlements', 'entitlements.plist',
            str(app_path)
        ]
        
        print(f"🔐 执行签名: codesign -s '{cert_name}' --deep --force --options runtime --entitlements entitlements.plist '{app_path}'")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 代码签名成功！")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 代码签名失败: {e.stderr}")
        return False

def verify_app(app_path: Path):
    """验证应用程序"""
    print("🔍 验证应用程序...")
    
    try:
        # 验证签名
        result = subprocess.run([
            'codesign', '-dv', str(app_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 代码签名验证通过")
        
        # 验证 Gatekeeper
        result = subprocess.run([
            'spctl', '--assess', '--type', 'execute', '-vvv', str(app_path)
        ], capture_output=True, text=True)
        
        if 'accepted' in result.stdout:
            print("✅ Gatekeeper 验证通过")
        else:
            print("⚠️  Gatekeeper 验证失败，但应用仍可运行")
            print(f"详细信息: {result.stdout}")
        
        return True
        
    except Exception as e:
        print(f"⚠️  验证过程中出现错误: {e}")
        return False

def post_build_setup():
    """构建后设置"""
    print("⚙️ 进行构建后设置...")
    
    app_path = Path('dist/ArtaleKey.app')
    if not app_path.exists():
        print("❌ 应用程序未找到")
        return False
    
    print(f"✅ 应用程序已创建: {app_path.absolute()}")
    
    # 确保二进制文件有执行权限
    binary_path = app_path / 'Contents/MacOS/ArtaleKey'
    if binary_path.exists():
        os.chmod(binary_path, 0o755)
        print("✅ 已设置二进制文件执行权限")
    
    # 尝试代码签名
    if Path('entitlements.plist').exists():
        if sign_app(app_path):
            verify_app(app_path)
    else:
        print("⚠️  未找到 entitlements.plist，跳过代码签名")
    
    # 创建使用指南
    usage_guide = '''
# ArtaleKey macOS 应用使用指南

## 权限设置
应用首次运行时，需要授予以下权限：

1. **辅助功能权限**
   - 系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能
   - 添加 ArtaleKey.app 到允许列表

2. **输入监控权限**（macOS 10.15+）
   - 系统偏好设置 → 安全性与隐私 → 隐私 → 输入监控
   - 添加 ArtaleKey.app 到允许列表

3. **屏幕录制权限**（如果使用OCR功能）
   - 系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制
   - 添加 ArtaleKey.app 到允许列表

## 启动方式
1. 双击 ArtaleKey.app 启动
2. 如果提示"无法打开"，右键点击 → 打开

## 故障排除
如果快捷键不工作：
1. 确认已授予所有必要权限
2. 重启应用程序
3. 重启系统（权限更改后可能需要）

## 代码签名状态
- 如果应用已签名，将更稳定可靠
- 未签名的应用仍可使用，但需要手动授权

## 命令行验证
验证应用权限：
```bash
spctl --assess --type execute -vvv "dist/ArtaleKey.app"
```

查看签名信息：
```bash
codesign -dv "dist/ArtaleKey.app"
```
'''
    
    with open('MACOS_USAGE_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(usage_guide)
    
    print("✅ 使用指南已创建: MACOS_USAGE_GUIDE.md")
    
    # 创建DMG指南
    dmg_guide = '''
# 创建DMG安装包

## 方法一：使用 create-dmg（推荐）

1. 安装create-dmg工具：
```bash
brew install create-dmg
```

2. 创建DMG：
```bash
create-dmg \\
  --volname "ArtaleKey" \\
  --window-pos 200 120 \\
  --window-size 800 400 \\
  --icon-size 100 \\
  --icon "ArtaleKey.app" 200 190 \\
  --hide-extension "ArtaleKey.app" \\
  --app-drop-link 600 185 \\
  "ArtaleKey-1.0.0.dmg" \\
  "dist/"
```

## 方法二：手动创建

1. 打开"磁盘工具"
2. 文件 → 新建映像 → 空白映像
3. 将ArtaleKey.app拖入
4. 创建应用程序链接
5. 保存为DMG文件

## 分发注意事项

- 如果应用已签名和公证，用户可以直接运行
- 未签名的应用需要用户手动允许运行
- 建议在DMG中包含使用说明
'''
    
    with open('DMG_GUIDE.md', 'w', encoding='utf-8') as f:
        f.write(dmg_guide)
    
    print("✅ DMG创建指南已生成: DMG_GUIDE.md")
    return True

def main():
    """主函数"""
    print("🍎 ArtaleKey macOS App 打包工具")
    print("=" * 50)
    
    # 检查是否在正确的目录
    if not Path('artalekey').exists():
        print("❌ 请在项目根目录运行此脚本")
        return 1
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    print("\n📦 开始打包流程...")
    
    # 检查entitlements.plist文件
    if not Path('entitlements.plist').exists():
        print("⚠️  未找到 entitlements.plist，将影响权限申请")
        print("💡 建议创建此文件以解决快捷键监听问题")
    
    # 创建配置文件
    if not create_spec_file():
        return 1
    
    # 创建图标指南
    create_app_icon()
    
    # 构建应用
    if not build_app():
        return 1
    
    # 构建后设置
    if not post_build_setup():
        return 1
    
    print("\n🎉 打包完成！")
    print("📱 应用程序位置: dist/ArtaleKey.app")
    print("\n💡 重要提示:")
    print("   📋 快捷键问题解决方案:")
    print("   1. 确保应用已进行代码签名")
    print("   2. 在系统偏好设置中授予必要权限")
    print("   3. 重启应用以使权限生效")
    print("   4. 查看 MACOS_USAGE_GUIDE.md 获取详细说明")
    print("\n📋 其他文件:")
    print("   • ArtaleKey.spec - 打包配置")
    print("   • entitlements.plist - 权限配置")
    print("   • MACOS_USAGE_GUIDE.md - 使用指南")
    print("   • DMG_GUIDE.md - DMG制作指南")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 