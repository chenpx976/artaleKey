# -*- mode: python ; coding: utf-8 -*-

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
