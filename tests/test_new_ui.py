#!/usr/bin/env python3
"""
测试新UI设计 - 重点测试最近使用应用程序功能
"""

import sys
import os
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """测试新UI设计"""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from artalekey.ui.tabbed_main_window import TabbedMainWindow
        from artalekey.core.window_detector import window_monitor
        
        print("🚀 启动新UI设计测试...")
        print("🎯 主要测试功能：")
        print("   • 最近使用的应用程序显示")
        print("   • 窗口历史记录功能")
        print("   • 双击快速添加功能")
        print()
        
        # 创建应用程序
        app = QApplication(sys.argv)
        app.setApplicationName("ArtaleKey")
        
        if sys.platform == "darwin":
            app.setStyle("Fusion")
        
        # 创建主窗口
        window = TabbedMainWindow()
        window.show()
        
        print("✅ UI启动成功！")
        print()
        print("🔍 测试步骤：")
        print("1. 观察'最近使用的应用程序'区域")
        print("2. 切换到其他应用程序（如浏览器、编辑器等）")
        print("3. 切换回ArtaleKey，查看最近应用列表是否更新")
        print("4. 双击最近应用列表中的应用名称，应该能快速添加到目标列表")
        print("5. 测试窗口过滤功能是否正常工作")
        print()
        
        # 显示提示消息框
        def show_test_instructions():
            msg = QMessageBox()
            msg.setWindowTitle("UI测试说明")
            msg.setText("新的UI设计已启动！")
            msg.setInformativeText(
                "主要改进：\n"
                "• 移除了无意义的'当前活动窗口'显示\n"
                "• 新增'最近使用的应用程序'功能\n"
                "• 双击最近应用可快速添加到目标列表\n"
                "• 更合理的界面布局\n\n"
                "测试方法：\n"
                "1. 切换到其他应用程序\n"
                "2. 返回查看最近应用列表\n"
                "3. 双击应用名称快速添加"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        
        # 延迟显示说明
        from PyQt6.QtCore import QTimer
        timer = QTimer()
        timer.singleShot(1000, show_test_instructions)
        
        print("🎉 开始测试新UI功能！")
        
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