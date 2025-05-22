"""
UI样式管理模块 - 针对macOS优化的深色主题
"""

# 基础色彩定义
COLORS = {
    # 背景色
    'bg_primary': '#2d2d2d',
    'bg_secondary': '#3c3c3c',
    'bg_tertiary': '#303030',
    'bg_input': '#454545',
    'bg_hover': '#4a4a4a',
    'bg_disabled': '#383838',
    
    # 边框色
    'border_normal': '#606060',
    'border_focus': '#4CAF50',
    'border_hover': '#66BB6A',
    'border_disabled': '#4a4a4a',
    
    # 文字色
    'text_primary': '#ffffff',
    'text_secondary': '#cccccc',
    'text_hint': '#999999',
    'text_disabled': '#808080',
    
    # 强调色
    'accent_primary': '#4CAF50',
    'accent_secondary': '#66BB6A',
    'accent_light': '#81C784',
    
    # 状态色
    'status_success': '#4CAF50',
    'status_warning': '#FF9800',
    'status_error': '#f44336',
    'status_info': '#2196F3',
}

# 字体系统 - macOS优先
FONT_FAMILY = (
    '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", '
    '"Helvetica Neue", Helvetica, Arial, '
    '"PingFang SC", "Hiragino Sans GB", "Source Han Sans CN", '
    '"Microsoft YaHei", "WenQuanYi Micro Hei", sans-serif'
)

def get_main_window_style():
    """获取主窗口样式"""
    return f"""
        QMainWindow, QWidget {{
            background: {COLORS['bg_primary']};
            color: {COLORS['text_primary']};
            font-family: {FONT_FAMILY};
            font-size: 13px;
        }}
        
        QCheckBox {{
            color: {COLORS['text_primary']};
            font-size: 14px;
            font-weight: 500;
            padding: 6px;
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            background: {COLORS['bg_input']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 4px;
        }}
        
        QCheckBox::indicator:hover {{
            background: {COLORS['bg_hover']};
            border-color: {COLORS['border_hover']};
        }}
        
        QCheckBox::indicator:checked {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 {COLORS['accent_secondary']}, 
                                       stop: 1 {COLORS['accent_primary']});
            border-color: {COLORS['accent_primary']};
        }}
        
        QLabel {{
            color: {COLORS['text_primary']};
            font-family: {FONT_FAMILY};
        }}
    """

def get_card_style():
    """获取卡片组件样式"""
    return f"""
        QFrame {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 {COLORS['bg_secondary']}, 
                                       stop: 1 {COLORS['bg_tertiary']});
            border: 1px solid {COLORS['border_normal']};
            border-radius: 8px;
            padding: 16px;
            margin: 6px;
        }}
        
        QLabel {{
            color: {COLORS['text_primary']};
            font-weight: 500;
            font-family: {FONT_FAMILY};
        }}
        
        QComboBox, QSpinBox {{
            background: {COLORS['bg_input']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 6px;
            padding: 8px 12px;
            color: {COLORS['text_primary']};
            font-size: 14px;
            font-family: {FONT_FAMILY};
            min-width: 100px;
            min-height: 20px;
        }}
        
        QComboBox:hover, QSpinBox:hover {{
            border-color: {COLORS['border_hover']};
            background: {COLORS['bg_hover']};
        }}
        
        QComboBox:focus, QSpinBox:focus {{
            border-color: {COLORS['border_focus']};
            background: {COLORS['bg_hover']};
            outline: none;
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
            padding-right: 4px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {COLORS['text_primary']};
            margin-right: 6px;
        }}
        
        QComboBox QAbstractItemView {{
            background: {COLORS['bg_input']};
            border: 1px solid {COLORS['border_normal']};
            selection-background-color: {COLORS['accent_primary']};
            color: {COLORS['text_primary']};
            outline: none;
        }}
        
        QSpinBox::up-button, QSpinBox::down-button {{
            background: {COLORS['bg_secondary']};
            border: 1px solid {COLORS['border_normal']};
            border-radius: 3px;
            width: 18px;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background: {COLORS['bg_hover']};
        }}
        
        QCheckBox {{
            color: {COLORS['text_primary']};
            font-size: 15px;
            font-weight: 500;
            spacing: 12px;
            font-family: {FONT_FAMILY};
        }}
        
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            background: {COLORS['bg_input']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 4px;
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {COLORS['border_hover']};
            background: {COLORS['bg_hover']};
        }}
        
        QCheckBox::indicator:checked {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 {COLORS['accent_secondary']}, 
                                       stop: 1 {COLORS['accent_primary']});
            border-color: {COLORS['accent_primary']};
        }}
        
        QSlider::groove:horizontal {{
            border: 1px solid {COLORS['border_normal']};
            height: 8px;
            background: {COLORS['bg_input']};
            border-radius: 4px;
        }}
        
        QSlider::handle:horizontal {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 {COLORS['accent_secondary']}, 
                                       stop: 1 {COLORS['accent_primary']});
            border: 1px solid {COLORS['accent_primary']};
            width: 22px;
            margin: -7px 0;
            border-radius: 11px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 {COLORS['accent_light']}, 
                                       stop: 1 {COLORS['accent_secondary']});
        }}
    """

def get_selector_style():
    """获取选择器组件样式"""
    return f"""
        QFrame {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 {COLORS['bg_secondary']}, 
                                       stop: 1 {COLORS['bg_tertiary']});
            border: 1px solid {COLORS['border_normal']};
            border-radius: 8px;
            padding: 16px;
            margin: 6px;
        }}
        
        QLabel {{
            color: {COLORS['text_primary']};
            font-weight: 500;
            font-family: {FONT_FAMILY};
        }}
        
        QCheckBox {{
            color: {COLORS['text_primary']};
            font-size: 14px;
            font-weight: 500;
            spacing: 12px;
            font-family: {FONT_FAMILY};
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            background: {COLORS['bg_input']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 4px;
        }}
        
        QCheckBox::indicator:hover {{
            background: {COLORS['bg_hover']};
            border-color: {COLORS['border_hover']};
        }}
        
        QCheckBox::indicator:checked {{
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                       stop: 0 {COLORS['accent_secondary']}, 
                                       stop: 1 {COLORS['accent_primary']});
            border-color: {COLORS['accent_primary']};
        }}
        
        QListWidget {{
            background: {COLORS['bg_input']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 6px;
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-family: {FONT_FAMILY};
            selection-background-color: {COLORS['accent_primary']};
            outline: none;
        }}
        
        QListWidget::item {{
            padding: 10px;
            margin: 2px;
            border-radius: 4px;
        }}
        
        QListWidget::item:hover {{
            background: {COLORS['bg_hover']};
        }}
        
        QListWidget::item:selected {{
            background: {COLORS['accent_primary']};
            color: {COLORS['text_primary']};
        }}
        
        QPushButton {{
            background: {COLORS['bg_secondary']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 6px;
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-weight: 500;
            font-family: {FONT_FAMILY};
            padding: 10px 16px;
            min-width: 80px;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background: {COLORS['bg_hover']};
            border-color: {COLORS['border_hover']};
        }}
        
        QPushButton:pressed {{
            background: {COLORS['accent_primary']};
        }}
        
        QPushButton:disabled {{
            background: {COLORS['bg_disabled']};
            border-color: {COLORS['border_disabled']};
            color: {COLORS['text_disabled']};
        }}
        
        QLineEdit {{
            background: {COLORS['bg_input']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 6px;
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-family: {FONT_FAMILY};
            padding: 8px 12px;
            min-height: 20px;
        }}
        
        QLineEdit:focus {{
            border-color: {COLORS['border_focus']};
            background: {COLORS['bg_hover']};
        }}
        
        QComboBox {{
            background: {COLORS['bg_input']};
            border: 2px solid {COLORS['border_normal']};
            border-radius: 6px;
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-family: {FONT_FAMILY};
            padding: 8px 12px;
            min-width: 150px;
            min-height: 20px;
        }}
        
        QComboBox:hover {{
            border-color: {COLORS['border_hover']};
            background: {COLORS['bg_hover']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
            padding-right: 4px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {COLORS['text_primary']};
            margin-right: 6px;
        }}
        
        QComboBox QAbstractItemView {{
            background: {COLORS['bg_input']};
            border: 1px solid {COLORS['border_normal']};
            selection-background-color: {COLORS['accent_primary']};
            color: {COLORS['text_primary']};
        }}
    """

def get_status_style(status_type='info'):
    """获取状态标签样式"""
    status_colors = {
        'success': COLORS['status_success'],
        'warning': COLORS['status_warning'],
        'error': COLORS['status_error'],
        'info': COLORS['status_info']
    }
    
    color = status_colors.get(status_type, COLORS['status_info'])
    
    return f"""
        QLabel {{
            background: {COLORS['bg_secondary']};
            color: {COLORS['text_primary']};
            padding: 10px;
            border-radius: 6px;
            border-left: 4px solid {color};
            font-size: 12px;
            font-family: {FONT_FAMILY};
            font-weight: 500;
        }}
    """

def get_scrollarea_style():
    """获取滚动区域样式"""
    return f"""
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: rgba(45, 45, 45, 0.8);
            width: 14px;
            margin: 0px;
            border-radius: 7px;
        }}
        
        QScrollBar::handle:vertical {{
            background: rgba(76, 175, 80, 0.8);
            min-height: 30px;
            border-radius: 7px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: rgba(102, 187, 106, 0.9);
        }}
        
        QScrollBar::handle:vertical:pressed {{
            background: rgba(56, 142, 60, 1.0);
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
    """ 