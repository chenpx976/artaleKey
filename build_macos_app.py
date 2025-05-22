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
        
    return True

def create_spec_file():
    """创建PyInstaller规格文件"""
    print("📝 创建打包配置文件...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

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
        'psutil',
        'pynput',
        'AppKit',
        'Cocoa',
        'Foundation',
        'Quartz',
        'objc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# 过滤掉不需要的文件
a.datas = [x for x in a.datas if not x[0].startswith('matplotlib')]
a.datas = [x for x in a.datas if not x[0].startswith('numpy')]

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
    entitlements_file=None,
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
    info_plist={
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
        # 请求必要的权限
        'NSAccessibilityUsageDescription': 'ArtaleKey需要辅助功能权限来模拟按键',
        'NSAppleEventsUsageDescription': 'ArtaleKey需要AppleScript权限来检测窗口状态',
    },
)
'''
    
    with open('ArtaleKey.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ 配置文件已创建: ArtaleKey.spec")

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

def post_build_setup():
    """构建后设置"""
    print("⚙️ 进行构建后设置...")
    
    app_path = Path('dist/ArtaleKey.app')
    if not app_path.exists():
        print("❌ 应用程序未找到")
        return False
    
    print(f"✅ 应用程序已创建: {app_path.absolute()}")
    
    # 创建DMG指南
    dmg_guide = '''
# 创建DMG安装包

如果您想创建DMG安装包，可以：

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

或者手动创建：
1. 打开"磁盘工具"
2. 文件 -> 新建映像 -> 空白映像
3. 将ArtaleKey.app拖入
4. 创建应用程序链接
5. 保存为DMG文件
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
    
    # 创建配置文件
    create_spec_file()
    
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
    print("💡 使用说明:")
    print("   1. 双击运行应用程序")
    print("   2. 首次运行需要授予辅助功能权限")
    print("   3. 系统偏好设置 -> 安全性与隐私 -> 辅助功能")
    print("   4. 添加ArtaleKey到允许列表")
    print("\n📋 其他文件:")
    print("   • ArtaleKey.spec - 打包配置")
    print("   • assets/icon_guide.md - 图标制作指南")  
    print("   • DMG_GUIDE.md - DMG制作指南")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 