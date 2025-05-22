#!/usr/bin/env python3
"""
UI测试启动脚本 - 用于测试修复后的界面
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """启动UI测试"""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from artalekey.ui.main_window import MainWindow
        
        # 创建应用程序
        app = QApplication(sys.argv)
        
        # 设置应用程序属性
        app.setApplicationName("ArtaleKey")
        app.setApplicationDisplayName("ArtaleKey - 快捷键管理器")
        app.setApplicationVersion("1.0.0")
        
        # 针对macOS的特殊设置
        if sys.platform == "darwin":
            # PyQt6中的高DPI支持设置
            try:
                # 在PyQt6中，高DPI缩放是默认启用的，但我们可以明确设置
                app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
                # 设置样式
                app.setStyle("Fusion")
            except AttributeError:
                # 如果属性不存在，继续执行
                print("💡 注意：某些高DPI属性在此PyQt6版本中不可用，但不影响使用")
        
        print("🚀 正在启动ArtaleKey UI...")
        print("📱 检查界面显示是否正常...")
        print("🎨 新的UI修复包括：")
        print("   - macOS优化的字体系统")
        print("   - 改善的颜色对比度")
        print("   - 统一的样式管理")
        print("   - 中文字体支持优化")
        print()
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        print("✅ UI启动成功！")
        print("📝 请检查以下内容：")
        print("   1. 字体显示是否清晰")
        print("   2. 按钮是否响应正常")
        print("   3. 颜色对比度是否足够")
        print("   4. 中文文字是否正常显示")
        print("   5. 滑块和输入框是否工作正常")
        print()
        
        # 运行应用程序
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请确保安装了所有必要的依赖：")
        print("   pip install PyQt6")
        print("   pip install psutil")
        return 1
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 