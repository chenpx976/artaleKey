"""
简化的原生样式系统 - 支持字体自适应和原生外观
"""

def get_native_style():
    """获取原生样式 - 简洁且自适应"""
    return """
        QMainWindow, QWidget {
            font-size: 13px;
        }
        
        QLabel {
            font-size: 13px;
        }
        
        QCheckBox {
            font-size: 14px;
            spacing: 8px;
        }
        
        QPushButton {
            font-size: 13px;
            padding: 6px 12px;
            min-height: 24px;
        }
        
        QComboBox, QLineEdit {
            font-size: 13px;
            padding: 4px 8px;
            min-height: 20px;
        }
        
        QListWidget {
            font-size: 13px;
        }
        
        QSlider {
            min-height: 20px;
        }
        
        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            padding-top: 10px;
            margin-top: 6px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
    """

def get_responsive_font_size(window_width, base_size=13):
    """根据窗口宽度计算自适应字体大小"""
    if window_width < 400:
        return max(10, base_size - 2)
    elif window_width < 600:
        return base_size
    elif window_width < 800:
        return base_size + 1
    else:
        return base_size + 2

def get_adaptive_style(window_width, window_height):
    """获取自适应样式"""
    font_size = get_responsive_font_size(window_width)
    label_size = font_size
    button_size = font_size
    input_size = font_size
    
    return f"""
        QMainWindow, QWidget {{
            font-size: {font_size}px;
        }}
        
        QLabel {{
            font-size: {label_size}px;
        }}
        
        QCheckBox {{
            font-size: {button_size}px;
            spacing: 8px;
        }}
        
        QPushButton {{
            font-size: {button_size}px;
            padding: {max(4, font_size//3)}px {max(8, font_size//2)}px;
            min-height: {font_size + 8}px;
        }}
        
        QComboBox, QLineEdit {{
            font-size: {input_size}px;
            padding: {max(2, font_size//4)}px {max(6, font_size//3)}px;
            min-height: {font_size + 4}px;
        }}
        
        QListWidget {{
            font-size: {input_size}px;
        }}
        
        QGroupBox {{
            font-size: {label_size + 1}px;
            font-weight: bold;
            padding-top: {font_size}px;
            margin-top: {font_size//2}px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
        
        QSlider {{
            min-height: {font_size + 6}px;
        }}
        
        QSlider::handle:horizontal {{
            width: {font_size + 4}px;
            margin: -{font_size//3}px 0;
        }}
    """ 