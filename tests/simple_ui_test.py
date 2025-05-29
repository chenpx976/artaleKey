#!/usr/bin/env python3
"""
简化UI测试启动脚本 - 避免复杂的PyQt6属性设置
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """启动UI测试 - 简化版本"""
    try:
        from PyQt6.QtWidgets import QApplication
        from artalekey.ui.tabbed_main_window import TabbedMainWindow
        
        print("🚀 启动ArtaleKey UI测试...")
        print("🎨 使用修复后的样式系统")
        print()
        
        # 创建应用程序 - 使用最基本的设置
        app = QApplication(sys.argv)
        app.setApplicationName("ArtaleKey")
        
        # 在macOS上设置Fusion样式
        if sys.platform == "darwin":
            app.setStyle("Fusion")
        
        # 创建主窗口
        window = TabbedMainWindow()
        window.show()
        
        print("✅ UI启动成功！请检查界面显示效果")
        print("🔍 主要检查项目：")
        print("   • 字体是否清晰（特别是中文）")
        print("   • 按钮和控件是否响应正常")
        print("   • 颜色对比度是否足够")
        print("   • 滑块操作是否流畅")
        print()
        
        # 运行应用程序
        return app.exec()
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请检查是否安装了PyQt6：pip install PyQt6")
        return 1
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 