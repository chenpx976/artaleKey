#!/usr/bin/env python3
"""
OCR 技术对比脚本
比较 Tesseract 和 EasyOCR 在中文识别方面的效果
"""

import pytesseract
import easyocr
from PIL import Image, ImageEnhance, ImageFilter
import os
import sys
import numpy as np
import time

def preprocess_image_for_tesseract(image):
    """为 Tesseract 预处理图片"""
    if image.mode != 'L':
        image = image.convert('L')
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    image = image.filter(ImageFilter.SHARPEN)
    return image

def preprocess_image_for_easyocr(image):
    """为 EasyOCR 预处理图片"""
    if image.mode == 'RGBA':
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.3)
    return image

def test_tesseract(image_path):
    """测试 Tesseract OCR"""
    try:
        pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        
        image = Image.open(image_path)
        processed_image = preprocess_image_for_tesseract(image)
        
        start_time = time.time()
        text = pytesseract.image_to_string(processed_image, lang='chi_tra+eng', config=r'--oem 3 --psm 6')
        end_time = time.time()
        
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        
        return {
            'success': True,
            'text': text.strip(),
            'chinese_chars': chinese_chars,
            'total_chars': len(text),
            'time_taken': end_time - start_time,
            'method': 'Tesseract (繁体中文+英文)'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'method': 'Tesseract'
        }

def test_easyocr(image_path):
    """测试 EasyOCR"""
    try:
        image = Image.open(image_path)
        processed_image = preprocess_image_for_easyocr(image)
        image_array = np.array(processed_image)
        
        start_time = time.time()
        reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
        results = reader.readtext(image_array)
        end_time = time.time()
        
        # 提取高置信度文本
        high_conf_texts = [text for _, text, confidence in results if confidence > 0.5]
        all_texts = [text for _, text, _ in results]
        
        combined_text = ' '.join(high_conf_texts)
        chinese_chars = sum(sum(1 for char in text if '\u4e00' <= char <= '\u9fff') for text in all_texts)
        
        avg_confidence = sum(confidence for _, _, confidence in results) / len(results) if results else 0
        
        return {
            'success': True,
            'text': combined_text,
            'chinese_chars': chinese_chars,
            'total_chars': sum(len(text) for text in all_texts),
            'time_taken': end_time - start_time,
            'confidence': avg_confidence,
            'text_blocks': len(results),
            'high_conf_blocks': len(high_conf_texts),
            'method': 'EasyOCR (繁体中文+英文)'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'method': 'EasyOCR'
        }

def compare_ocr_methods():
    """比较两种 OCR 方法"""
    
    image_path = "../ocr_data/screenshots/screenshot_20250527_011821.png"
    
    print("=" * 80)
    print("🔍 OCR 技术对比测试")
    print("=" * 80)
    print(f"测试图片: {image_path}")
    
    if not os.path.exists(image_path):
        print("❌ 图片文件不存在")
        return False
    
    # 获取图片信息
    image = Image.open(image_path)
    print(f"图片尺寸: {image.size}")
    print(f"图片模式: {image.mode}")
    print()
    
    # 测试 Tesseract
    print("🔧 测试 Tesseract...")
    tesseract_result = test_tesseract(image_path)
    
    # 测试 EasyOCR
    print("🔧 测试 EasyOCR...")
    easyocr_result = test_easyocr(image_path)
    
    # 显示结果对比
    print("\n" + "=" * 80)
    print("📊 对比结果")
    print("=" * 80)
    
    methods = [tesseract_result, easyocr_result]
    
    for result in methods:
        print(f"\n【{result['method']}】")
        print("-" * 50)
        
        if result['success']:
            print(f"✅ 识别成功")
            print(f"⏱️  处理时间: {result['time_taken']:.2f} 秒")
            print(f"📝 总字符数: {result['total_chars']}")
            print(f"🈶 中文字符数: {result['chinese_chars']}")
            
            if 'confidence' in result:
                print(f"🎯 平均置信度: {result['confidence']:.3f}")
                print(f"📦 文本块总数: {result['text_blocks']}")
                print(f"🎯 高置信度块数: {result['high_conf_blocks']}")
            
            print(f"\n识别文本预览:")
            preview = result['text'][:200] + "..." if len(result['text']) > 200 else result['text']
            print(f"{preview}")
            
        else:
            print(f"❌ 识别失败: {result['error']}")
    
    # 总结建议
    print(f"\n" + "=" * 80)
    print("💡 总结建议")
    print("=" * 80)
    
    if tesseract_result['success'] and easyocr_result['success']:
        print("🔍 性能对比:")
        print(f"- Tesseract 处理时间: {tesseract_result['time_taken']:.2f}s")
        print(f"- EasyOCR 处理时间: {easyocr_result['time_taken']:.2f}s")
        
        print(f"\n📊 识别效果:")
        print(f"- Tesseract 中文字符: {tesseract_result['chinese_chars']}")
        print(f"- EasyOCR 中文字符: {easyocr_result['chinese_chars']}")
        
        print(f"\n🎯 推荐:")
        if easyocr_result['chinese_chars'] > tesseract_result['chinese_chars']:
            print("- EasyOCR 在中文识别方面表现更好")
        elif tesseract_result['chinese_chars'] > easyocr_result['chinese_chars']:
            print("- Tesseract 在中文识别方面表现更好")
        else:
            print("- 两种方法的中文识别效果相近")
            
        if tesseract_result['time_taken'] < easyocr_result['time_taken']:
            print("- Tesseract 处理速度更快")
        else:
            print("- EasyOCR 处理速度更快")
            
        print("- EasyOCR 提供置信度信息，便于结果筛选")
        print("- Tesseract 配置更灵活，支持更多语言组合")
    
    return True

if __name__ == "__main__":
    success = compare_ocr_methods()
    sys.exit(0 if success else 1) 