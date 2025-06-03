#!/usr/bin/env python3
"""
EasyOCR 测试脚本
基于深度学习的 OCR 识别，支持中文识别
"""

import easyocr
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import os
import sys
import numpy as np
import random

def preprocess_image(image):
    """预处理图片以提高 OCR 识别率"""
    # 转换为 RGB 模式（EasyOCR 需要）
    if image.mode == 'RGBA':
        # 创建白色背景
        background = Image.new('RGB', image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])  # 使用 alpha 通道作为 mask
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # 增强对比度
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)
    
    # 增强清晰度
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.3)
    
    return image

def draw_ocr_results(image, results, config_name, min_confidence=0.4):
    """在图片上绘制 OCR 识别结果"""
    # 创建图片副本用于绘制
    draw_image = image.copy()
    draw = ImageDraw.Draw(draw_image)
    
    # 尝试加载字体，如果失败则使用默认字体
    try:
        # 在 macOS 上尝试使用系统字体
        font_size = max(12, min(image.width, image.height) // 50)
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", font_size)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None
    
    colors = [
        (255, 0, 0),    # 红色
        (0, 255, 0),    # 绿色
        (0, 0, 255),    # 蓝色
        (255, 255, 0),  # 黄色
        (255, 0, 255),  # 紫色
        (0, 255, 255),  # 青色
        (255, 128, 0),  # 橙色
        (128, 255, 0),  # 黄绿色
    ]
    
    high_confidence_count = 0
    total_count = 0
    
    for i, (bbox, text, confidence) in enumerate(results):
        total_count += 1
        
        # 只绘制高置信度的结果
        if confidence >= min_confidence:
            high_confidence_count += 1
            
            # 获取边界框坐标
            top_left = tuple([int(val) for val in bbox[0]])
            top_right = tuple([int(val) for val in bbox[1]])
            bottom_right = tuple([int(val) for val in bbox[2]])
            bottom_left = tuple([int(val) for val in bbox[3]])
            
            # 选择颜色
            color = colors[i % len(colors)]
            
            # 绘制边界框
            box_points = [top_left, top_right, bottom_right, bottom_left, top_left]
            draw.line(box_points, fill=color, width=2)
            
            # 绘制文本和置信度
            text_with_conf = f"{text} ({confidence:.2f})"
            
            # 计算文本位置（在框的上方）
            text_x = top_left[0]
            text_y = max(0, top_left[1] - 25)
            
            # 绘制文本背景
            if font:
                bbox_text = draw.textbbox((text_x, text_y), text_with_conf, font=font)
                draw.rectangle(bbox_text, fill=(0, 0, 0, 128))
                draw.text((text_x, text_y), text_with_conf, fill=(255, 255, 255), font=font)
            else:
                # 使用默认字体
                draw.text((text_x, text_y), text_with_conf, fill=color)
    
    return draw_image, high_confidence_count, total_count

def easyocr_test():
    """EasyOCR 测试函数"""
    
    # 图片文件路径
    image_path = "../ocr_data/CleanShot 2025-06-01 at 02.19.47@2x.png"
    
    print("=== EasyOCR 识别测试 ===")
    print(f"图片路径: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"错误: 图片文件不存在")
        return False
    
    try:
        # 创建输出目录
        output_dir = "../ocr_data/annotated_images"
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载并预处理图片
        print("加载和预处理图片...")
        original_image = Image.open(image_path)
        processed_image = preprocess_image(original_image)
        
        print(f"原始图片尺寸: {original_image.size}")
        print(f"图片模式: {original_image.mode}")
        
        # 修正后的语言配置
        language_configs = [
            {
                'languages': ['en'], 
                'name': '英文',
                'description': '仅英文识别',
                'filename': 'easyocr_result_en.png'
            }
        ]
        
        print("\n" + "="*80)
        
        best_config = None
        best_score = 0
        
        for config in language_configs:
            print(f"\n【{config['name']}】识别结果:")
            print(f"配置: {config['description']}")
            print("-" * 50)
            
            try:
                # 初始化 EasyOCR 读取器
                print(f"初始化 EasyOCR 读取器 (语言: {config['languages']})...")
                reader = easyocr.Reader(config['languages'], gpu=False)
                
                # 将 PIL 图片转换为 numpy 数组
                image_array = np.array(processed_image)
                
                # 执行 OCR
                print("开始识别...")
                results = reader.readtext(image_array)
                
                if results:
                    print("识别的文本内容:")
                    print("=" * 40)
                    
                    all_text = []
                    high_confidence_text = []
                    
                    for (bbox, text, confidence) in results:
                        if confidence > 0.5:  # 只显示高置信度的文本
                            print(f"✓ {text} (置信度: {confidence:.3f})")
                            high_confidence_text.append(text)
                        all_text.append(text)
                    
                    print(f"\n高置信度文本 (>0.5):")
                    if high_confidence_text:
                        combined_high_confidence = ' '.join(high_confidence_text)
                        print(f"{combined_high_confidence}")
                    else:
                        print("(无高置信度文本)")
                    
                    # 统计信息
                    total_chars = sum(len(text) for text in all_text)
                    chinese_chars = sum(sum(1 for char in text if '\u4e00' <= char <= '\u9fff') for text in all_text)
                    avg_confidence = sum(confidence for _, _, confidence in results) / len(results)
                    high_conf_count = sum(1 for _, _, confidence in results if confidence > 0.5)
                    
                    print(f"\n统计信息:")
                    print(f"- 识别到 {len(results)} 个文本块")
                    print(f"- 高置信度文本块: {high_conf_count}")
                    print(f"- 总字符数: {total_chars}")
                    print(f"- 中文字符数: {chinese_chars}")
                    print(f"- 平均置信度: {avg_confidence:.3f}")
                    
                    # 绘制识别结果
                    print("绘制识别结果...")
                    annotated_image, drawn_high_conf, drawn_total = draw_ocr_results(
                        original_image, results, config['name']
                    )
                    
                    # 保存带标注的图片
                    output_path = os.path.join(output_dir, config['filename'])
                    annotated_image.save(output_path)
                    print(f"✅ 标注结果已保存: {output_path}")
                    print(f"   绘制了 {drawn_high_conf}/{drawn_total} 个高置信度文本框")
                    
                    # 计算评分（用于找到最佳配置）
                    score = high_conf_count * avg_confidence + chinese_chars * 0.1
                    if score > best_score:
                        best_score = score
                        best_config = config
                    
                else:
                    print("(未识别到任何文字)")
                    
            except Exception as e:
                print(f"识别失败: {e}")
        
        print("\n" + "="*80)
        print("测试完成！")
        
        # 推荐最佳配置
        print("\n🔍 推荐配置:")
        if best_config:
            print(f"- 最佳配置: {best_config['name']}")
            print(f"- 输出文件: {best_config['filename']}")
        print("- 对于游戏界面，建议使用【繁体中文+英文】配置")
        print("- EasyOCR 在文本定位和置信度评估方面比 Tesseract 更准确")
        print("- 可以通过置信度阈值过滤低质量识别结果")
        print(f"- 所有标注图片已保存到: {output_dir}")
        
        return True
        
    except Exception as e:
        print(f"处理出错: {e}")
        return False

if __name__ == "__main__":
    success = easyocr_test()
    sys.exit(0 if success else 1) 