#!/usr/bin/env python3
"""
ArtaleKey 启动脚本 - 最简洁的启动方式
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """启动ArtaleKey"""
    try:
        from PyQt6.QtWidgets import QApplication
        from artalekey.ui.simple_main_window import SimpleMainWindow
        
        print("🚀 启动 ArtaleKey 快捷键管理器...")
        
        # 创建应用程序
        app = QApplication(sys.argv)
        app.setApplicationName("ArtaleKey")
        
        # 使用系统原生样式
        if sys.platform == "darwin":
            app.setStyle("macOS")
        else:
            app.setStyle("Fusion")
        
        # 创建主窗口
        window = SimpleMainWindow()
        window.show()
        
        print("✅ ArtaleKey 启动成功！")
        
        # 运行应用程序
        return app.exec()
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请检查PyQt6安装：pip install PyQt6")
        return 1
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 