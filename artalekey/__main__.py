import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from artalekey.ui.tabbed_main_window import TabbedMainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ArtaleKey")
    
    # 使用系统原生样式
    if sys.platform == "darwin":
        app.setStyle("macOS")  # macOS原生样式
    else:
        app.setStyle("Fusion")
    
    # 创建并显示带标签页的主窗口
    window = TabbedMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 