#!/usr/bin/env python3
"""
EasyOCR 测试脚本 - 全力性能优化版本
"""

import easyocr
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont
import os
import sys
import numpy as np
import random
from scipy import ndimage
import time  # 添加时间模块用于性能测试


class ColorProcessor:
    """颜色处理器 - 性能优化版"""
    
    def __init__(self):
        # 定义橙色RGB值 - 使用numpy数组提升性能
        self.orange_colors = np.array([
            [255, 125, 12],   # #FF7D0C
            [253, 135, 50],   # #FD8732
            [255, 140, 0],    # #FF8C00 (DarkOrange)
            [255, 165, 0],    # #FFA500 (Orange)
            [236, 102, 44],   # #EC662C
            [246, 100, 40],   # #F66428
            [235, 109, 52],   # #EB6D34
            [236, 100, 37],   # #EC6425
            [235, 110, 49],   # #EB6E31
            [245, 89, 37],    # #F55925
        ], dtype=np.uint8)
        
        # 定义黑色RGB值 - 使用numpy数组提升性能
        self.black_colors = np.array([
            [0, 0, 0],        # #000000 (纯黑色)
            [17, 17, 17],     # #111111 (深灰黑)
            [34, 34, 34],     # #222222 (深灰)
            [51, 51, 51],     # #333333 (暗灰)
            [68, 68, 68],     # #444444 (中暗灰)
            [85, 85, 85],     # #555555 (灰色)
            [102, 102, 102],  # #666666 (中灰)
            [119, 119, 119],  # #777777 (浅中灰)
            [136, 136, 136],  # #888888 (浅灰)
            [153, 153, 153],  # #999999 (更浅灰)
            [64, 64, 64],     # #404040 (深灰)
            [32, 32, 32],     # #202020 (很深灰)
            [48, 48, 48],     # #303030 (深灰)
            [16, 16, 16],     # #101010 (极深灰)
            [8, 8, 8],        # #080808 (接近黑色)
        ], dtype=np.uint8)
        
        # 容差设置
        self.rgb_tolerance = 30
        
        # HSV参数
        self.orange_hue_min = 15
        self.orange_hue_max = 35
        self.saturation_min = 100
        self.value_min = 100
        self.black_saturation_max = 50
        self.black_value_max = 100

    def create_hsv_masks(self, hsv_data):
        """创建HSV颜色掩码 - 向量化优化"""
        h_channel = hsv_data[:, :, 0]
        s_channel = hsv_data[:, :, 1] 
        v_channel = hsv_data[:, :, 2]
        
        # 橙色HSV掩码 - 向量化操作
        orange_hsv_mask = (
            (h_channel >= self.orange_hue_min) & (h_channel <= self.orange_hue_max) &
            (s_channel >= self.saturation_min) &
            (v_channel >= self.value_min)
        )
        
        # 黑色HSV掩码 - 向量化操作
        black_hsv_mask = (
            (s_channel <= self.black_saturation_max) &
            (v_channel <= self.black_value_max)
        )
        
        return orange_hsv_mask, black_hsv_mask

    def create_rgb_masks_optimized(self, data):
        """创建RGB颜色掩码 - 高度优化版"""
        height, width = data.shape[:2]
        
        # 使用广播和向量化操作优化橙色检测
        data_rgb = data[:, :, :3].astype(np.float32)
        orange_distances = np.linalg.norm(data_rgb[:, :, None, :] - self.orange_colors[None, None, :, :], axis=3)
        orange_rgb_mask = np.any(orange_distances <= self.rgb_tolerance, axis=2)
        
        # 使用广播和向量化操作优化黑色检测
        black_distances = np.linalg.norm(data_rgb[:, :, None, :] - self.black_colors[None, None, :, :], axis=3)
        black_rgb_mask = np.any(black_distances <= self.rgb_tolerance, axis=2)
        
        # 纯白色检测 - 向量化
        pure_white_rgb_mask = np.all(data[:, :, :3] == 255, axis=2)
        
        # 接近白色检测 - 优化算法
        # 高亮度检测
        high_brightness_mask = np.all(data[:, :, :3] >= 200, axis=2)
        
        # 颜色差值检测 - 向量化
        rgb_channels = data[:, :, :3].astype(np.float32)
        max_diff = np.max(rgb_channels, axis=2) - np.min(rgb_channels, axis=2)
        low_color_diff_mask = max_diff <= 25
        
        # 平均亮度检测
        avg_brightness = np.mean(rgb_channels, axis=2)
        high_avg_brightness_mask = avg_brightness >= 200
        
        # 组合条件
        near_white_not_pure_mask = (high_brightness_mask | (low_color_diff_mask & high_avg_brightness_mask)) & (~pure_white_rgb_mask)
        
        # 简化的邻域检测
        near_white_mask_with_surrounded = self._detect_surrounded_white_pixels_fast(pure_white_rgb_mask, near_white_not_pure_mask)
        
        # 简化的统计输出
        print(f"  颜色检测统计:")
        print(f"    橙色像素: {np.sum(orange_rgb_mask)}")
        print(f"    黑色像素: {np.sum(black_rgb_mask)}")
        print(f"    纯白色像素: {np.sum(pure_white_rgb_mask)}")
        print(f"    接近白色像素: {np.sum(near_white_mask_with_surrounded)}")
        
        # 更新纯白色掩码
        surrounded_white_pixels = near_white_mask_with_surrounded & pure_white_rgb_mask
        updated_pure_white_mask = pure_white_rgb_mask & (~surrounded_white_pixels)
        
        return orange_rgb_mask, black_rgb_mask, updated_pure_white_mask, near_white_mask_with_surrounded
    
    def _detect_surrounded_white_pixels_fast(self, pure_white_mask, near_white_mask):
        """快速邻域检测 - 性能优化版"""
        # 使用更快的形态学操作
        from scipy import ndimage
        structure = np.ones((3, 3), dtype=bool)
        
        # 膨胀操作
        dilated_near_white = ndimage.binary_dilation(near_white_mask, structure=structure, iterations=1)
        
        # 找到候选像素
        candidate_pixels = pure_white_mask & dilated_near_white
        
        if np.sum(candidate_pixels) == 0:
            return near_white_mask.copy()
        
        # 使用卷积快速计算邻域
        kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.float32)
        neighbor_count = ndimage.convolve(near_white_mask.astype(np.float32), kernel, mode='constant', cval=0)
        
        # 向量化处理
        result_mask = near_white_mask.copy()
        surrounded_mask = candidate_pixels & (neighbor_count >= 4)
        result_mask |= surrounded_mask
        
        print(f"    快速邻域检测: 发现 {np.sum(surrounded_mask)} 个被包围像素")
        
        return result_mask


class RegionProcessor:
    """区域处理器 - 性能优化版"""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._calculate_regions()
    
    def _calculate_regions(self):
        """计算处理区域边界"""
        # 下面 1/4 区域
        self.bottom_quarter_start = self.height * 3 // 4
        self.bottom_quarter_end = self.height
        
        # 左边 1/4 区域（在下面 1/4 内）
        self.left_quarter_start = 0
        self.left_quarter_end = self.width // 4
        
        # 中间 2/4 区域（在下面 1/4 内）
        self.middle_half_start = self.width // 4
        self.middle_half_end = self.width * 3 // 4
    
    def create_region_masks(self, data_shape):
        """创建区域掩码 - 向量化优化"""
        # 使用向量化操作创建掩码
        left_quarter_region_mask = np.zeros(data_shape[:2], dtype=bool)
        left_quarter_region_mask[self.bottom_quarter_start:self.bottom_quarter_end, 
                                self.left_quarter_start:self.left_quarter_end] = True
        
        middle_half_region_mask = np.zeros(data_shape[:2], dtype=bool)
        middle_half_region_mask[self.bottom_quarter_start:self.bottom_quarter_end, 
                               self.middle_half_start:self.middle_half_end] = True
        
        return left_quarter_region_mask, middle_half_region_mask


class ImagePreprocessor:
    """图片预处理器 - 超级性能优化版"""
    
    def __init__(self, max_size=1024):
        self.color_processor = ColorProcessor()
        self.max_size = max_size  # 最大尺寸限制
    
    def resize_image_smart(self, image):
        """智能缩放图像到指定尺寸范围"""
        width, height = image.size
        
        # 如果图像已经足够小，则不缩放
        if width <= self.max_size and height <= self.max_size:
            return image, 1.0
        
        # 计算缩放比例
        scale_factor = min(self.max_size / width, self.max_size / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # 使用高质量的缩放算法
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        print(f"图像缩放: {width}×{height} → {new_width}×{new_height} (比例: {scale_factor:.3f})")
        
        return resized_image, scale_factor
    
    def preprocess_image_color_replace(self, image_path, output_path=None):
        """预处理图片：高性能颜色替换"""
        try:
            # 读取图片
            image = Image.open(image_path)
            print(f"原始图片尺寸: {image.size}")
            print(f"图片模式: {image.mode}")
            
            # 智能缩放图像
            resized_image, scale_factor = self.resize_image_smart(image)
            
            # 转换为RGBA模式
            if resized_image.mode != 'RGBA':
                resized_image = resized_image.convert('RGBA')
            
            # 将图片转换为numpy数组进行颜色处理
            data = np.array(resized_image)
            height, width = data.shape[:2]
            
            # 创建区域处理器
            region_processor = RegionProcessor(width, height)
            
            # 创建HSV掩码
            image_hsv = resized_image.convert('HSV')
            hsv_data = np.array(image_hsv)
            orange_hsv_mask, black_hsv_mask = self.color_processor.create_hsv_masks(hsv_data)
            
            # 创建RGB掩码 - 使用优化版本
            orange_rgb_mask, black_rgb_mask, pure_white_rgb_mask, near_white_mask_with_surrounded = self.color_processor.create_rgb_masks_optimized(data)
            
            # 创建区域掩码
            left_quarter_region_mask, middle_half_region_mask = region_processor.create_region_masks(data.shape)
            
            # 应用区域限制的颜色掩码 - 向量化操作
            orange_mask_in_left = (orange_hsv_mask | orange_rgb_mask) & left_quarter_region_mask
            black_mask_in_left = (black_hsv_mask | black_rgb_mask) & left_quarter_region_mask
            color_replacement_mask_left = orange_mask_in_left | black_mask_in_left
            
            # 中间区域掩码
            pure_white_mask_in_middle = pure_white_rgb_mask & middle_half_region_mask
            near_white_mask_in_middle = near_white_mask_with_surrounded & middle_half_region_mask
            
            print(f"区域处理统计:")
            print(f"  左边区域处理像素: {np.sum(color_replacement_mask_left)}")
            print(f"  中间区域纯白色像素: {np.sum(pure_white_mask_in_middle)}")
            print(f"  中间区域接近白色像素: {np.sum(near_white_mask_in_middle)}")
            
            # 执行颜色替换 - 向量化操作
            self._apply_color_replacement_fast(data, color_replacement_mask_left, pure_white_mask_in_middle, near_white_mask_in_middle)
            
            # 转换回PIL图片
            processed_image = Image.fromarray(data, 'RGBA')
            
            return processed_image, scale_factor
            
        except Exception as e:
            print(f"❌ 颜色替换失败: {e}")
            return None, None
    
    def _apply_color_replacement_fast(self, data, color_replacement_mask_left, pure_white_mask_in_middle, near_white_mask_in_middle):
        """快速颜色替换 - 向量化操作"""
        # 定义替换颜色
        black_color = np.array([0, 0, 0], dtype=np.uint8)
        blue_temp_color = np.array([0, 0, 255], dtype=np.uint8)
        white_color = np.array([255, 255, 255], dtype=np.uint8)
        
        # 1. 左边区域：橙色+黑色 → 黑色
        data[color_replacement_mask_left, :3] = black_color
        
        # 2. 中间区域：接近白色 → 临时蓝色
        data[near_white_mask_in_middle, :3] = blue_temp_color
        
        # 3. 中间区域：纯白色 → 黑色
        data[pure_white_mask_in_middle, :3] = black_color
        
        # 4. 中间区域：临时蓝色 → 白色
        # 重新查找蓝色像素（向量化操作）
        blue_mask = np.all(data[:, :, :3] == blue_temp_color, axis=2)
        data[blue_mask, :3] = white_color


class OCRProcessor:
    """OCR处理器 - 零文件I/O版本"""
    
    def __init__(self):
        print("初始化EasyOCR引擎...")
        self.reader = easyocr.Reader(['en'], gpu=False)
        print("✅ EasyOCR引擎初始化完成")
    
    def perform_ocr_direct(self, processed_image, scale_factor=1.0):
        """直接对PIL图像进行OCR识别 - 无文件I/O"""
        try:
            print(f"\n=== 开始OCR识别 (无文件I/O) ===")
            
            # 转换PIL图像为RGB格式（EasyOCR需要RGB）
            if processed_image.mode == 'RGBA':
                # 创建白色背景
                rgb_image = Image.new('RGB', processed_image.size, (255, 255, 255))
                rgb_image.paste(processed_image, mask=processed_image.split()[-1])
            else:
                rgb_image = processed_image.convert('RGB')
            
            # 转换为numpy数组
            image_array = np.array(rgb_image)
            
            print(f"处理图像尺寸: {image_array.shape}")
            
            # 直接传递numpy数组给EasyOCR - 无需文件
            results = self.reader.readtext(image_array)
            
            # 如果图像被缩放了，需要将坐标还原到原始尺寸
            if scale_factor != 1.0:
                results = self._scale_back_results(results, scale_factor)
            
            print(f"✅ OCR识别完成，共识别到 {len(results)} 个文本区域")
            self._print_ocr_results(results)
            
            return results, rgb_image
            
        except Exception as e:
            print(f"❌ OCR识别失败: {e}")
            return None, None
    
    def _scale_back_results(self, results, scale_factor):
        """将OCR结果的坐标缩放回原始尺寸"""
        scaled_results = []
        for bbox, text, confidence in results:
            # 缩放边界框坐标
            scaled_bbox = []
            for point in bbox:
                scaled_point = [point[0] / scale_factor, point[1] / scale_factor]
                scaled_bbox.append(scaled_point)
            scaled_results.append((scaled_bbox, text, confidence))
        
        print(f"坐标缩放回原始尺寸 (比例: {1/scale_factor:.3f})")
        return scaled_results
    
    def _print_ocr_results(self, results):
        """打印OCR识别结果"""
        print("\n=== OCR识别结果 ===")
        for i, (bbox, text, confidence) in enumerate(results, 1):
            print(f"{i}. 文本: '{text}' (置信度: {confidence:.3f})")
    
    def draw_ocr_results(self, image_path, ocr_results, processed_image=None, output_path=None):
        """在图片上绘制OCR识别结果"""
        try:
            # 使用原始图片还是处理后的图片
            if processed_image is not None:
                # 使用处理后的图片
                image = processed_image.convert('RGB')
            else:
                # 打开原始图片
                image = Image.open(image_path).convert('RGB')
            
            draw = ImageDraw.Draw(image)
            
            # 尝试加载字体
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            # 绘制识别结果
            for i, (bbox, text, confidence) in enumerate(ocr_results):
                # 获取边界框坐标
                points = np.array(bbox, dtype=np.int32)
                
                # 绘制边界框
                box_coords = [tuple(point) for point in points]
                draw.polygon(box_coords, outline='red', width=2)
                
                # 绘制文本
                text_x = int(points[0][0])
                text_y = int(points[0][1]) - 25
                text_y = max(0, text_y)
                
                text_content = f"{text} ({confidence:.2f})"
                bbox_text = draw.textbbox((text_x, text_y), text_content, font=font)
                draw.rectangle(bbox_text, fill='yellow', outline='red')
                draw.text((text_x, text_y), text_content, fill='black', font=font)
            
            # 保存结果图片
            if output_path is None:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = os.path.dirname(image_path)
                output_path = os.path.join(output_dir, f"{base_name}_ocr_result_optimized.png")
            
            image.save(output_path)
            print(f"✅ OCR结果图片已保存到: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"❌ 绘制OCR结果失败: {e}")
            return None


def main():
    """主函数 - 超级性能优化版"""
    import os  # 确保在函数内部导入os模块
    
    print("=== OCR 超级性能优化测试 ===")
    
    # 记录开始时间
    start_time = time.time()
    
    # 图片路径
    image_path = "ocr_data/CleanShot 2025-06-01 at 02.19.47@2x.png"
    
    print(f"处理图片: {image_path}")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"❌ 错误: 图片文件不存在: {image_path}")
        return False
    
    # 创建处理器实例
    print("创建高性能处理器...")
    init_start = time.time()
    preprocessor = ImagePreprocessor(max_size=1024)  # 限制最大尺寸
    ocr_processor = OCRProcessor()
    init_time = time.time() - init_start
    
    # 执行颜色替换
    preprocessing_start = time.time()
    processed_image, scale_factor = preprocessor.preprocess_image_color_replace(image_path)
    preprocessing_time = time.time() - preprocessing_start
    
    if processed_image is not None:
        print("🎉 颜色替换处理完成！")
        print(f"原始图片: {image_path}")
        print("优化策略:")
        print(f"  - 图像尺寸限制: 最大 {preprocessor.max_size}×{preprocessor.max_size}")
        print("  - 直接内存传递: OCR无需临时文件")
        print("  - 向量化颜色处理: 使用numpy广播操作")
        print("  - 快速邻域检测: 优化的形态学操作")
        
        # 对处理后的图片进行OCR识别 - 直接传递PIL图像
        ocr_start = time.time()
        ocr_results, rgb_image = ocr_processor.perform_ocr_direct(processed_image, scale_factor)
        ocr_time = time.time() - ocr_start
        
        if ocr_results is not None:
            print("🎉 OCR识别完成！")
            
            # 在图片上绘制OCR结果
            draw_start = time.time()
            ocr_result_image = ocr_processor.draw_ocr_results(image_path, ocr_results, rgb_image)
            draw_time = time.time() - draw_start
            
            # 计算总时间
            total_time = time.time() - start_time
            
            # 打印性能统计
            print(f"\n=== 超级优化性能统计 ===")
            print(f"初始化时间: {init_time:.3f} 秒")
            print(f"图像预处理时间: {preprocessing_time:.3f} 秒")
            print(f"OCR识别时间: {ocr_time:.3f} 秒")
            print(f"结果绘制时间: {draw_time:.3f} 秒")
            print(f"总处理时间: {total_time:.3f} 秒")
            print(f"\n性能分布:")
            print(f"  - 初始化: {init_time/total_time*100:.1f}%")
            print(f"  - 预处理: {preprocessing_time/total_time*100:.1f}%")
            print(f"  - OCR识别: {ocr_time/total_time*100:.1f}%")
            print(f"  - 结果绘制: {draw_time/total_time*100:.1f}%")
            
            print(f"\n🚀 优化成果:")
            print(f"  ✅ 消除临时文件I/O")
            print(f"  ✅ 图像尺寸智能缩放")
            print(f"  ✅ 向量化颜色处理")
            print(f"  ✅ 直接内存传递OCR")
            
            if ocr_result_image:
                print("🎉 OCR结果图片生成完成！")
                return True
            else:
                print("❌ OCR结果图片生成失败")
                return False
        else:
            print("❌ OCR识别失败")
            return False
    else:
        print("❌ 颜色替换处理失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
