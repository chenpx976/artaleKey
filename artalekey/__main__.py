import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from .ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 