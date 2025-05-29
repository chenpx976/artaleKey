#!/usr/bin/env python3
"""
简单的 Tesseract OCR 测试脚本
测试读取 screenshot_20250527_011821.png 图片并进行 OCR 识别
支持中文识别
"""

import pytesseract
from PIL import Image
import os
import sys

def test_tesseract_ocr():
    """测试 tesseract OCR 功能"""
    
    # 设置 tesseract 可执行文件路径（for macOS with Homebrew）
    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
    
    # 图片文件路径
    image_path = "../ocr_data/screenshots/screenshot_20250527_011821.png"
    
    print("=== Tesseract OCR 测试 ===")
    print(f"正在处理图片: {image_path}")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"错误: 图片文件不存在: {image_path}")
        return False
    
    try:
        # 加载图片
        print("加载图片中...")
        image = Image.open(image_path)
        print(f"图片尺寸: {image.size}")
        print(f"图片模式: {image.mode}")
        
        # 测试不同的语言配置
        language_configs = [
            ('eng', '英文'),
            ('chi_sim+eng', '简体中文+英文'),
            ('chi_tra+eng', '繁体中文+英文'),
            ('chi_sim+chi_tra+eng', '简体+繁体+英文'),
        ]
        
        for lang_code, lang_name in language_configs:
            print(f"\n=== 使用 {lang_name} 进行 OCR 识别 ===")
            try:
                # 执行 OCR
                text = pytesseract.image_to_string(image, lang=lang_code)
                
                # 输出结果
                print(f"识别结果 ({lang_name}):")
                print("-" * 50)
                print(text)
                print("-" * 50)
                
                # 输出统计信息
                lines = text.strip().split('\n')
                non_empty_lines = [line for line in lines if line.strip()]
                
                print(f"总行数: {len(lines)}")
                print(f"非空行数: {len(non_empty_lines)}")
                print(f"总字符数: {len(text)}")
                
            except Exception as e:
                print(f"语言 {lang_name} 识别出错: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"OCR 处理出错: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_tesseract_ocr()
    sys.exit(0 if success else 1) 