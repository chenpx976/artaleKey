#!/usr/bin/env python3
"""
简化原生UI测试 - 支持字体自适应和原生外观
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """启动简化原生UI测试"""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from artalekey.ui.simple_main_window import SimpleMainWindow
        
        print("🚀 启动简化原生UI...")
        print("🎯 主要特性：")
        print("   • 原生Qt外观，无过度样式")
        print("   • 字体大小自适应窗口大小")
        print("   • 极简的界面设计")
        print("   • 默认目标应用：MapleStory Worlds")
        print("   • 一键快速设置")
        print()
        
        # 创建应用程序
        app = QApplication(sys.argv)
        app.setApplicationName("ArtaleKey")
        
        # 使用系统原生样式
        if sys.platform == "darwin":
            app.setStyle("macOS")  # 或者 "Fusion"
        
        # 创建主窗口
        window = SimpleMainWindow()
        window.show()
        
        print("✅ 简化UI启动成功！")
        print()
        print("🔍 主要改进：")
        print("1. 📏 字体自适应 - 调整窗口大小，字体会自动调整")
        print("2. 🎨 原生外观 - 使用系统原生Qt样式")
        print("3. 🎯 简化设置 - 默认目标应用已设为 MapleStory Worlds")
        print("4. ⚡ 快速操作 - 一键启用/设置功能")
        print("5. 📱 响应式布局 - 适配不同窗口大小")
        print()
        print("🎮 针对您的游戏优化：")
        print("• 默认目标应用：MapleStory Worlds")
        print("• 点击'使用默认应用'立即设置")
        print("• 启用窗口过滤即可开始使用")
        print()
        
        # 显示快速使用说明
        def show_quick_guide():
            msg = QMessageBox()
            msg.setWindowTitle("快速使用指南")
            msg.setText("简化UI已启动！")
            msg.setInformativeText(
                "🎮 为MapleStory Worlds优化的快捷设置：\n\n"
                "1️⃣ 启用快速向上功能 ✓\n"
                "2️⃣ 在'窗口过滤'中启用过滤 ✓\n"
                "3️⃣ 点击'使用默认应用'设置游戏 ✓\n"
                "4️⃣ 在游戏中使用W+↑键触发快速上移\n\n"
                "💡 提示：\n"
                "• 调整窗口大小查看字体自适应效果\n"
                "• 界面使用原生Qt样式，更简洁流畅\n"
                "• 所有设置都会自动保存"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        
        # 延迟显示说明
        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.singleShot(1500, show_quick_guide)
        
        print("🎉 开始体验简化原生UI！")
        
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