#!/usr/bin/env python3
"""
中文优化的 Tesseract OCR 测试脚本
支持简体中文、繁体中文识别
"""

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import os
import sys

def preprocess_image(image):
    """预处理图片以提高 OCR 识别率"""
    # 转换为灰度图
    if image.mode != 'L':
        image = image.convert('L')
    
    # 增强对比度
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # 锐化
    image = image.filter(ImageFilter.SHARPEN)
    
    return image

def chinese_ocr_test():
    """中文 OCR 测试函数"""
    
    # 设置 tesseract 可执行文件路径
    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
    
    # 图片文件路径
    image_path = "../ocr_data/screenshots/screenshot_20250527_011821.png"
    
    print("=== 中文 OCR 识别测试 ===")
    print(f"图片路径: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"错误: 图片文件不存在")
        return False
    
    try:
        # 加载并预处理图片
        print("加载和预处理图片...")
        original_image = Image.open(image_path)
        processed_image = preprocess_image(original_image)
        
        print(f"原始图片尺寸: {original_image.size}")
        print(f"图片模式: {original_image.mode}")
        
        # 推荐的中文识别配置
        configs = [
            {
                'lang': 'chi_sim+eng', 
                'name': '简体中文+英文',
                'config': r'--oem 3 --psm 6'
            },
            {
                'lang': 'chi_tra+eng', 
                'name': '繁体中文+英文',
                'config': r'--oem 3 --psm 6'
            },
            {
                'lang': 'chi_sim+chi_tra+eng', 
                'name': '简繁体混合+英文',
                'config': r'--oem 3 --psm 6'
            }
        ]
        
        print("\n" + "="*60)
        
        for config in configs:
            print(f"\n【{config['name']}】识别结果:")
            print("-" * 40)
            
            try:
                # 对预处理后的图片进行 OCR
                text = pytesseract.image_to_string(
                    processed_image, 
                    lang=config['lang'],
                    config=config['config']
                )
                
                if text.strip():
                    print(text)
                    
                    # 统计信息
                    lines = [line for line in text.split('\n') if line.strip()]
                    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
                    
                    print(f"\n统计: {len(lines)}行, {len(text)}字符, {chinese_chars}个中文字符")
                else:
                    print("(未识别到文字)")
                    
            except Exception as e:
                print(f"识别失败: {e}")
        
        print("\n" + "="*60)
        print("测试完成！")
        return True
        
    except Exception as e:
        print(f"处理出错: {e}")
        return False

if __name__ == "__main__":
    success = chinese_ocr_test()
    sys.exit(0 if success else 1) 