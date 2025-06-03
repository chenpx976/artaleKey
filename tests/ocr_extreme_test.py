#!/usr/bin/env python3
"""
EasyOCR 极限性能测试 - 激进优化版本
探索性能的极限边界
"""

import easyocr
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import os
import sys
import numpy as np
import time
from scipy import ndimage
import cv2  # 使用OpenCV进行更快的图像处理


class ExtremeColorProcessor:
    """极限颜色处理器 - 最激进优化版"""
    
    def __init__(self):
        # 使用int8减少内存占用
        self.orange_targets = np.array([[255, 125, 12], [255, 140, 0], [255, 165, 0]], dtype=np.uint8)
        self.black_targets = np.array([[0, 0, 0], [34, 34, 34], [68, 68, 68]], dtype=np.uint8)
        self.tolerance = 30
    
    def fast_color_detection(self, data):
        """超快速颜色检测 - 最小化计算"""
        # 只检测关键颜色，减少计算量
        data_rgb = data[:, :, :3]
        
        # 使用更简单的L1距离代替欧几里得距离
        orange_mask = np.any(np.sum(np.abs(data_rgb[:, :, None, :] - self.orange_targets), axis=3) <= self.tolerance, axis=2)
        black_mask = np.any(np.sum(np.abs(data_rgb[:, :, None, :] - self.black_targets), axis=3) <= self.tolerance, axis=2)
        
        # 简化白色检测
        pure_white = np.all(data_rgb >= 250, axis=2)  # 放宽白色检测
        near_white = (np.mean(data_rgb, axis=2) >= 180) & (~pure_white)
        
        return orange_mask, black_mask, pure_white, near_white


class ExtremePreprocessor:
    """极限预处理器"""
    
    def __init__(self, max_size=768):  # 进一步减少到768
        self.color_processor = ExtremeColorProcessor()
        self.max_size = max_size
    
    def extreme_resize(self, image):
        """极限缩放 - 使用OpenCV获得更好性能"""
        width, height = image.size
        
        if width <= self.max_size and height <= self.max_size:
            return image, 1.0
        
        scale = min(self.max_size / width, self.max_size / height)
        new_size = (int(width * scale), int(height * scale))
        
        # 转换为OpenCV格式
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGR)
        # 使用OpenCV进行快速缩放
        resized_cv = cv2.resize(cv_image, new_size, interpolation=cv2.INTER_LINEAR)  # 更快的插值
        # 转换回PIL
        resized_pil = Image.fromarray(cv2.cvtColor(resized_cv, cv2.COLOR_BGR2RGBA))
        
        print(f"极限缩放: {width}×{height} → {new_size[0]}×{new_size[1]} (OpenCV加速)")
        return resized_pil, scale
    
    def extreme_process(self, image_path):
        """极限处理流程"""
        # 读取和缩放
        image = Image.open(image_path)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        resized_image, scale_factor = self.extreme_resize(image)
        data = np.array(resized_image)
        height, width = data.shape[:2]
        
        # 极简区域定义
        bottom_start = height * 3 // 4
        left_end = width // 4
        middle_start = width // 4
        middle_end = width * 3 // 4
        
        # 快速颜色检测
        orange_mask, black_mask, pure_white, near_white = self.color_processor.fast_color_detection(data)
        
        # 区域掩码 - 向量化
        region_left = np.zeros((height, width), dtype=bool)
        region_left[bottom_start:, :left_end] = True
        
        region_middle = np.zeros((height, width), dtype=bool)
        region_middle[bottom_start:, middle_start:middle_end] = True
        
        # 颜色替换 - 向量化
        # 左区域
        left_replace = (orange_mask | black_mask) & region_left
        data[left_replace, :3] = [0, 0, 0]
        
        # 中间区域
        middle_near_white = near_white & region_middle
        middle_pure_white = pure_white & region_middle
        
        data[middle_near_white, :3] = [0, 0, 255]  # 临时蓝色
        data[middle_pure_white, :3] = [0, 0, 0]    # 黑色
        
        # 蓝色转白色
        blue_mask = np.all(data[:, :, :3] == [0, 0, 255], axis=2)
        data[blue_mask, :3] = [255, 255, 255]
        
        processed_image = Image.fromarray(data, 'RGBA')
        
        print(f"极限处理完成: 处理{np.sum(left_replace) + np.sum(middle_near_white) + np.sum(middle_pure_white)}像素")
        
        return processed_image, scale_factor


class ExtremeOCRProcessor:
    """极限OCR处理器"""
    
    def __init__(self):
        print("初始化极限OCR引擎...")
        # 只使用英文，减少模型加载时间
        self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("✅ 极限OCR引擎就绪")
    
    def extreme_ocr(self, processed_image, scale_factor=1.0):
        """极限OCR处理"""
        # 快速RGB转换
        if processed_image.mode == 'RGBA':
            rgb_image = Image.new('RGB', processed_image.size, (255, 255, 255))
            rgb_image.paste(processed_image, mask=processed_image.split()[-1])
        else:
            rgb_image = processed_image.convert('RGB')
        
        # 直接OCR
        image_array = np.array(rgb_image)
        results = self.reader.readtext(image_array, paragraph=False)  # 禁用段落检测加速
        
        # 快速坐标缩放
        if scale_factor != 1.0:
            inv_scale = 1.0 / scale_factor
            scaled_results = []
            for bbox, text, confidence in results:
                scaled_bbox = [[p[0] * inv_scale, p[1] * inv_scale] for p in bbox]
                scaled_results.append((scaled_bbox, text, confidence))
            results = scaled_results
        
        print(f"极限OCR完成: {len(results)}个文本区域")
        return results, rgb_image


def extreme_performance_test():
    """极限性能测试"""
    print("=== 🚀 极限性能挑战 ===")
    
    image_path = "ocr_data/CleanShot 2025-06-01 at 02.19.47@2x.png"
    
    if not os.path.exists(image_path):
        print(f"❌ 图片不存在: {image_path}")
        return False
    
    # 多次运行取平均值
    times = []
    for run in range(5):
        print(f"\n--- 第 {run+1} 次极限测试 ---")
        
        start_time = time.time()
        
        # 初始化
        init_start = time.time()
        preprocessor = ExtremePreprocessor(max_size=768)  # 768像素限制
        ocr_processor = ExtremeOCRProcessor()
        init_time = time.time() - init_start
        
        # 预处理
        preprocess_start = time.time()
        processed_image, scale_factor = preprocessor.extreme_process(image_path)
        preprocess_time = time.time() - preprocess_start
        
        # OCR
        ocr_start = time.time()
        results, rgb_image = ocr_processor.extreme_ocr(processed_image, scale_factor)
        ocr_time = time.time() - ocr_start
        
        total_time = time.time() - start_time
        times.append({
            'init': init_time,
            'preprocess': preprocess_time,
            'ocr': ocr_time,
            'total': total_time,
            'results_count': len(results)
        })
        
        print(f"运行 {run+1}: 总时间 {total_time:.3f}s (预处理: {preprocess_time:.3f}s, OCR: {ocr_time:.3f}s)")
    
    # 统计结果
    avg_times = {
        'init': np.mean([t['init'] for t in times]),
        'preprocess': np.mean([t['preprocess'] for t in times]),
        'ocr': np.mean([t['ocr'] for t in times]),
        'total': np.mean([t['total'] for t in times]),
        'results_count': np.mean([t['results_count'] for t in times])
    }
    
    print(f"\n=== 🏆 极限性能结果 ===")
    print(f"初始化时间: {avg_times['init']:.3f}s")
    print(f"预处理时间: {avg_times['preprocess']:.3f}s")
    print(f"OCR时间: {avg_times['ocr']:.3f}s")
    print(f"总时间: {avg_times['total']:.3f}s")
    print(f"平均识别: {avg_times['results_count']:.1f}个文本")
    
    # 与之前版本对比
    previous_total = 4.527  # 超级优化版本的时间
    improvement = (previous_total - avg_times['total']) / previous_total * 100
    
    print(f"\n🚀 极限优化效果:")
    print(f"vs 超级优化版: {improvement:+.1f}% ({'⚡ 更快' if improvement > 0 else '🐌 更慢'})")
    print(f"vs 原始版本: {(5.973 - avg_times['total']) / 5.973 * 100:+.1f}% 更快")
    
    return True


if __name__ == "__main__":
    success = extreme_performance_test()
    sys.exit(0 if success else 1) 