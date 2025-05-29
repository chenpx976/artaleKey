import os
import time
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PIL import Image, ImageGrab, ImageEnhance, ImageFilter
import cv2
import numpy as np
from artalekey.core.logger import performance_logger
from artalekey.core.config import config_manager
from artalekey.core.window_detector import WindowDetector
from artalekey.core.database import game_db

class EnhancedOCRManager(QThread):
    """增强的OCR管理器 - 使用多种OCR引擎，专门优化橙色背景白色文字识别"""
    
    # 信号定义
    ocr_triggered = pyqtSignal()       # OCR触发信号
    data_extracted = pyqtSignal(dict)  # 发送提取的数据
    error_occurred = pyqtSignal(str)   # 发送错误信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window_detector = WindowDetector()
        self._output_folder = None
        self._config = {}
        
        # OCR引擎 - 延迟加载
        self._easyocr_reader = None
        self._ocr_engine_loaded = False
        self._engine_loading = False
        
        # Tesseract支持
        self._tesseract_available = False
        
        # 性能优化缓存
        self._last_screenshot_hash = None
        self._last_ocr_result = None
        self._last_window_bounds = None
        self._bounds_cache_time = 0
        self._bounds_cache_duration = 5.0  # 窗口边界缓存5秒
        
        self._setup_output_folder()
        
        # 确保OCR引擎已加载
        self._load_ocr_engines()
        
    def _setup_output_folder(self):
        """设置输出文件夹"""
        folder_name = config_manager.get('screenshot_ocr.output_folder', 'ocr_data')
        self._output_folder = os.path.join(os.getcwd(), folder_name)
        
        # 创建主文件夹和子文件夹
        os.makedirs(self._output_folder, exist_ok=True)
        os.makedirs(os.path.join(self._output_folder, 'screenshots'), exist_ok=True)
        os.makedirs(os.path.join(self._output_folder, 'ocr_results'), exist_ok=True)
        os.makedirs(os.path.join(self._output_folder, 'annotated_images'), exist_ok=True)
        
        performance_logger.info(f"OCR输出文件夹设置为: {self._output_folder}")
    
    def _load_ocr_engines(self):
        """加载所有可用的OCR引擎"""
        if self._ocr_engine_loaded or self._engine_loading:
            return
            
        self._engine_loading = True
        try:
            # 加载EasyOCR
            performance_logger.info("开始加载OCR引擎...")
            start_time = time.time()
            
            import easyocr
            # 优化：只加载英文，禁用GPU以提高兼容性
            self._easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            
            # 尝试加载Tesseract
            try:
                import pytesseract
                self._tesseract_available = True
                performance_logger.info("Tesseract OCR引擎可用")
            except ImportError:
                performance_logger.warning("Tesseract OCR引擎不可用，将只使用EasyOCR")
                self._tesseract_available = False
            
            load_time = time.time() - start_time
            self._ocr_engine_loaded = True
            performance_logger.info(f"OCR引擎加载成功，耗时: {load_time:.2f}秒")
            
        except Exception as e:
            performance_logger.error(f"OCR引擎加载失败: {e}")
            self._ocr_engine_loaded = False
        finally:
            self._engine_loading = False
    
    def _get_image_hash(self, image: Image.Image) -> str:
        """计算图像哈希值，用于检测重复截图"""
        # 缩小图像并计算哈希，提高性能
        small_image = image.resize((64, 64))
        image_array = np.array(small_image)
        return str(hash(image_array.tobytes()))
    
    def _preprocess_image_parallel(self, image: Image.Image) -> List[Tuple[str, np.ndarray]]:
        """并行处理图像预处理 - 根据配置决定使用哪些预处理方法"""
        # 转换为RGB模式的原始图片
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            original_image = background
        elif image.mode != 'RGB':
            original_image = image.convert('RGB')
        else:
            original_image = image.copy()
        
        # 转换为numpy数组
        original_array = np.array(original_image)
        
        processed_results = []
        
        # 获取预处理配置
        preprocessing_config = self._config.get('preprocessing', {})
        
        # 定义所有预处理任务 - 默认只启用orange_optimized
        preprocessing_tasks = []
        
        # 橙色背景优化处理 - 默认启用
        if preprocessing_config.get('orange_optimized', True):
            preprocessing_tasks.append(('orange_optimized', self._process_orange_background_text, original_array.copy()))
        
        # 其他预处理方法 - 需要配置启用
        if preprocessing_config.get('standard', False):
            preprocessing_tasks.append(('standard', self._standard_preprocessing, original_image))
        
        if preprocessing_config.get('high_contrast', False):
            preprocessing_tasks.append(('high_contrast', self._high_contrast_processing, original_array.copy()))
        
        if preprocessing_config.get('color_separated', False):
            preprocessing_tasks.append(('color_separated', self._color_separation_processing, original_array.copy()))
        
        # 如果没有启用任何预处理方法，至少使用orange_optimized
        if not preprocessing_tasks:
            preprocessing_tasks.append(('orange_optimized', self._process_orange_background_text, original_array.copy()))
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=min(4, len(preprocessing_tasks))) as executor:
            # 提交所有任务
            future_to_method = {}
            for method_name, method_func, input_data in preprocessing_tasks:
                future = executor.submit(method_func, input_data)
                future_to_method[future] = method_name
            
            # 收集结果
            for future in as_completed(future_to_method):
                method_name = future_to_method[future]
                try:
                    result = future.result()
                    processed_results.append((method_name, result))
                    performance_logger.debug(f"预处理完成: {method_name}")
                except Exception as e:
                    performance_logger.error(f"预处理方法 {method_name} 失败: {e}")
        
        # 按原始顺序排序结果
        method_order = ['orange_optimized', 'standard', 'high_contrast', 'color_separated']
        processed_results.sort(key=lambda x: method_order.index(x[0]) if x[0] in method_order else 999)
        
        performance_logger.info(f"图像预处理完成，生成了 {len(processed_results)} 种处理版本")
        return processed_results
    
    def _standard_preprocessing(self, image: Image.Image) -> np.ndarray:
        """标准预处理方法"""
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.15)
        
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.05)
        
        return np.array(image)
    
    def _process_orange_background_text(self, img_array: np.ndarray) -> np.ndarray:
        """专门处理橙色背景白色文字"""
        try:
            # 转换到HSV颜色空间，更容易分离橙色
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            
            # 定义橙色的HSV范围 (橙色在HSV中的色调范围大约是10-25)
            lower_orange = np.array([5, 100, 100])   # 更宽泛的橙色范围
            upper_orange = np.array([35, 255, 255])
            
            # 创建橙色区域的掩码
            orange_mask = cv2.inRange(hsv, lower_orange, upper_orange)
            
            # 形态学操作来清理掩码
            kernel = np.ones((3,3), np.uint8)
            orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_CLOSE, kernel)
            orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_OPEN, kernel)
            
            # 创建输出图像
            result = img_array.copy()
            
            # 在橙色区域内，增强白色文字的对比度
            orange_regions = img_array[orange_mask > 0]
            if len(orange_regions) > 0:
                # 转换为灰度来分析亮度
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                
                # 在橙色区域内找到白色文字（高亮度像素）
                white_threshold = 200  # 白色文字的亮度阈值
                white_text_mask = (gray > white_threshold) & (orange_mask > 0)
                
                # 增强白色文字区域
                result[white_text_mask] = [255, 255, 255]  # 纯白色
                
                # 将橙色背景调暗，增加对比度
                orange_bg_mask = (gray <= white_threshold) & (orange_mask > 0)
                result[orange_bg_mask] = result[orange_bg_mask] * 0.3  # 调暗背景
            
            performance_logger.debug("橙色背景白色文字专用处理完成")
            return result
            
        except Exception as e:
            performance_logger.error(f"橙色背景处理失败: {e}")
            return img_array
    
    def _high_contrast_processing(self, img_array: np.ndarray) -> np.ndarray:
        """高对比度处理"""
        try:
            # 转换为灰度
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # 自适应直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 应用双边滤波减少噪声但保持边缘
            filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
            
            # 锐化
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(filtered, -1, kernel)
            
            # 转换回RGB
            result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)
            
            performance_logger.debug("高对比度处理完成")
            return result
            
        except Exception as e:
            performance_logger.error(f"高对比度处理失败: {e}")
            return img_array
    
    def _color_separation_processing(self, img_array: np.ndarray) -> np.ndarray:
        """颜色分离处理 - 专门提取白色文字"""
        try:
            # 转换为HSV
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            
            # 定义白色的HSV范围
            lower_white = np.array([0, 0, 200])     # 高亮度，低饱和度
            upper_white = np.array([180, 30, 255])  # 任何色调，低饱和度，高亮度
            
            # 创建白色文字掩码
            white_mask = cv2.inRange(hsv, lower_white, upper_white)
            
            # 形态学操作清理掩码
            kernel = np.ones((2,2), np.uint8)
            white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, kernel)
            
            # 创建二值图像：白色文字为白色，其他为黑色
            result = np.zeros_like(img_array)
            result[white_mask > 0] = [255, 255, 255]
            
            performance_logger.debug("颜色分离处理完成")
            return result
            
        except Exception as e:
            performance_logger.error(f"颜色分离处理失败: {e}")
            return img_array
    
    def _is_target_window_active(self) -> bool:
        """检查目标窗口是否激活"""
        target_window = self._config.get('target_window', 'MapleStory Worlds')
        
        try:
            # 获取当前活动窗口
            active_window = self.window_detector.get_active_window()
            if active_window:
                # 检查进程名或窗口标题是否包含目标窗口名称
                window_text = f"{active_window.process_name} {active_window.title}".lower()
                if target_window.lower() in window_text:
                    return True
        except Exception as e:
            performance_logger.error(f"检查活动窗口失败: {e}")
            
        return False
    
    def _get_target_window_bounds(self) -> Optional[Dict]:
        """获取目标窗口的边界坐标 - 优化版本，带缓存"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (self._last_window_bounds and 
            current_time - self._bounds_cache_time < self._bounds_cache_duration):
            performance_logger.debug("使用窗口边界缓存")
            return self._last_window_bounds
        
        target_window = self._config.get('target_window', 'MapleStory Worlds')
        
        try:
            # 首先尝试使用新的高效方法直接获取游戏窗口区域
            if hasattr(self.window_detector, 'get_game_window_region'):
                bounds = self.window_detector.get_game_window_region(target_window)
                if bounds:
                    performance_logger.debug(f"通过Quartz直接获取目标窗口边界: {bounds}")
                    self._last_window_bounds = bounds
                    self._bounds_cache_time = current_time
                    return bounds
            
            # 备用方案：使用原有方法
            active_window = self.window_detector.get_active_window()
            if active_window:
                window_text = f"{active_window.process_name} {active_window.title}".lower()
                if target_window.lower() in window_text:
                    # 如果活动窗口已经包含边界信息，直接使用
                    if active_window.bounds and all(k in active_window.bounds for k in ['x', 'y', 'width', 'height']):
                        performance_logger.debug(f"从活动窗口信息获取边界: {active_window.bounds}")
                        self._last_window_bounds = active_window.bounds
                        self._bounds_cache_time = current_time
                        return active_window.bounds
                    
                    # 否则尝试获取窗口边界
                    bounds = self.window_detector.get_window_bounds(active_window)
                    if bounds:
                        performance_logger.debug(f"通过窗口检测器获取边界: {bounds}")
                        self._last_window_bounds = bounds
                        self._bounds_cache_time = current_time
                        return bounds
        except Exception as e:
            performance_logger.error(f"获取目标窗口边界失败: {e}")
        
        # 清理无效缓存
        self._last_window_bounds = None
        return None
    
    def _capture_window_screenshot(self, bounds: Dict) -> Optional[Image.Image]:
        """截取指定窗口区域的截图 - 只截取下面四分之一区域"""
        try:
            # 获取原始窗口边界
            x, y, width, height = bounds['x'], bounds['y'], bounds['width'], bounds['height']
            
            # 计算下面四分之一区域的坐标
            quarter_height = height // 4
            new_y = y + height - quarter_height  # 从窗口底部往上四分之一处开始
            new_height = quarter_height
            
            performance_logger.info(f"原始窗口区域: {x},{y},{width},{height}")
            performance_logger.info(f"截取下面四分之一区域: {x},{new_y},{width},{new_height}")
            
            # 使用PIL截取指定区域，支持Retina显示器的高分辨率
            screenshot = ImageGrab.grab(bbox=(x, new_y, x + width, new_y + new_height), all_screens=True)
            
            # 如果需要提高分辨率，可以通过缩放实现
            scale_factor = self._config.get('screenshot_scale', 2.0)  # 默认2x分辨率
            if scale_factor != 1.0:
                new_width = int(screenshot.width * scale_factor)
                new_height_scaled = int(screenshot.height * scale_factor)
                screenshot = screenshot.resize((new_width, new_height_scaled), Image.Resampling.LANCZOS)
                performance_logger.info(f"截图已缩放到 {scale_factor}x 分辨率: {new_width}x{new_height_scaled}")
            
            performance_logger.info(f"成功截取窗口下面四分之一区域，最终尺寸: {screenshot.width}x{screenshot.height}")
            return screenshot
            
        except Exception as e:
            performance_logger.error(f"截取窗口截图失败: {e}")
            return None
    
    def _perform_ocr_parallel(self, image: Image.Image) -> Dict[str, Any]:
        """并行执行多引擎OCR识别 - 根据配置决定使用的引擎"""
        results = {
            'individual_results': [],  # 每个OCR结果单独存储
            'processing_summary': {}   # 处理摘要
        }
        
        try:
            # 并行获取多种预处理版本
            processed_versions = self._preprocess_image_parallel(image)
            
            all_individual_results = []
            
            # 获取OCR引擎配置
            ocr_engines_config = self._config.get('ocr_engines', {})
            enable_easyocr = ocr_engines_config.get('easyocr', True)
            enable_tesseract = ocr_engines_config.get('tesseract', False)
            
            # 对每种预处理版本并行进行OCR
            max_workers = len(processed_versions) * (int(enable_easyocr) + int(enable_tesseract and self._tesseract_available))
            with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
                future_to_task = {}
                
                for version_name, processed_image in processed_versions:
                    # EasyOCR任务
                    if enable_easyocr:
                        future_easy = executor.submit(self._run_easyocr, processed_image, version_name)
                        future_to_task[future_easy] = f'easyocr_{version_name}'
                    
                    # Tesseract任务（如果可用且启用）
                    if enable_tesseract and self._tesseract_available:
                        future_tess = executor.submit(self._run_tesseract, processed_image, version_name)
                        future_to_task[future_tess] = f'tesseract_{version_name}'
                
                # 收集所有OCR结果
                for future in as_completed(future_to_task):
                    task_name = future_to_task[future]
                    try:
                        ocr_result = future.result()
                        if ocr_result:
                            all_individual_results.extend(ocr_result)
                            performance_logger.debug(f"OCR任务完成: {task_name}, 获得 {len(ocr_result)} 个文本")
                    except Exception as e:
                        performance_logger.error(f"OCR任务 {task_name} 失败: {e}")
            
            results['individual_results'] = all_individual_results
            results['processing_summary'] = {
                'total_texts': len(all_individual_results),
                'preprocessing_methods': len(processed_versions),
                'ocr_engines': int(enable_easyocr) + int(enable_tesseract and self._tesseract_available)
            }
            
            performance_logger.info(f"OCR识别完成，共获得 {len(all_individual_results)} 个文本结果")
            
        except Exception as e:
            performance_logger.error(f"OCR识别失败: {e}")
        
        return results
    
    def _run_easyocr(self, processed_image: np.ndarray, version_name: str) -> List[Dict]:
        """运行EasyOCR识别"""
        try:
            easyocr_results = self._easyocr_reader.readtext(processed_image)
            text_boxes = []
            
            for (bbox, text, confidence) in easyocr_results:
                text_stripped = text.strip()
                
                if confidence > 0.3 and len(text_stripped) > 0:
                    text_box = {
                        'text': text_stripped,
                        'bbox': bbox,
                        'confidence': confidence,
                        'source': f'easyocr_{version_name}',
                        'engine': 'easyocr',
                        'version': version_name,
                        'timestamp': time.time()
                    }
                    text_boxes.append(text_box)
            
            return text_boxes
            
        except Exception as e:
            performance_logger.error(f"EasyOCR识别失败 ({version_name}): {e}")
            return []
    
    def _run_tesseract(self, processed_image: np.ndarray, version_name: str) -> List[Dict]:
        """运行Tesseract识别"""
        try:
            import pytesseract
            
            # 转换为PIL图像
            pil_image = Image.fromarray(processed_image.astype('uint8'))
            
            # 配置Tesseract参数
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789LVlv.:'
            
            # 获取详细识别结果
            data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)
            
            text_boxes = []
            for i, text in enumerate(data['text']):
                confidence = int(data['conf'][i])
                if confidence > 30 and text.strip():  # Tesseract的置信度范围是0-100
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    bbox = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                    
                    text_box = {
                        'text': text.strip(),
                        'bbox': bbox,
                        'confidence': confidence / 100.0,  # 转换为0-1范围
                        'source': f'tesseract_{version_name}',
                        'engine': 'tesseract',
                        'version': version_name,
                        'timestamp': time.time()
                    }
                    text_boxes.append(text_box)
            
            return text_boxes
            
        except Exception as e:
            performance_logger.error(f"Tesseract识别失败 ({version_name}): {e}")
            return []
    
    def _extract_game_data_individual(self, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """从OCR结果中提取游戏数据 - 移除历史数据依赖"""
        game_data = {
            'level': None,
            'experience': None,
            'candidate_results': [],  # 所有候选结果
            'selected_result': None,  # 最终选择的结果
            'extraction_details': {},
            'confidence_analysis': {}
        }
        
        try:
            individual_results = ocr_results.get('individual_results', [])
            performance_logger.info(f"开始数据提取，共 {len(individual_results)} 个OCR结果")
            
            # 步骤1: 从每个OCR结果中单独提取数据
            candidates = []
            for i, text_box in enumerate(individual_results):
                candidate = self._extract_single_result(text_box, i)
                if candidate['level'] is not None or candidate['experience'] is not None:
                    candidates.append(candidate)
            
            game_data['candidate_results'] = candidates
            performance_logger.info(f"提取到 {len(candidates)} 个候选结果")
            
            # 步骤2: 分析每个候选结果的合理性
            for candidate in candidates:
                self._analyze_candidate_reasonableness(candidate)
            
            # 步骤3: 选择最佳结果（不依赖历史数据）
            combined_result = self._select_best_candidate(candidates)
            
            if combined_result:
                game_data['level'] = combined_result.get('level')
                game_data['experience'] = combined_result.get('experience')
                game_data['selected_result'] = combined_result
                
                # 提取详细信息
                selection_details = combined_result.get('selection_details', {})
                game_data['extraction_details'] = {
                    'level_source': selection_details.get('level_source'),
                    'experience_source': selection_details.get('experience_source'),
                    'level_score': selection_details.get('level_score', 0),
                    'experience_score': selection_details.get('experience_score', 0)
                }
                
                performance_logger.info(f"最终选择结果: Level={game_data['level']}, Exp={game_data['experience']}")
                level_info = f"等级来源: {selection_details.get('level_source', 'None')}, 评分: {selection_details.get('level_score', 0):.1f}"
                exp_info = f"经验来源: {selection_details.get('experience_source', 'None')}, 评分: {selection_details.get('experience_score', 0):.1f}"
                performance_logger.info(f"{level_info}")
                performance_logger.info(f"{exp_info}")
            else:
                performance_logger.warning("没有找到合适的候选结果")
            
        except Exception as e:
            performance_logger.error(f"数据提取失败: {e}")
        
        return game_data
    
    def _extract_single_result(self, text_box: Dict, index: int) -> Dict[str, Any]:
        """从单个OCR结果中提取数据"""
        candidate = {
            'index': index,
            'text': text_box['text'],
            'source': text_box.get('source', 'unknown'),
            'engine': text_box.get('engine', 'unknown'),
            'version': text_box.get('version', 'unknown'),
            'confidence': text_box.get('confidence', 0),
            'level': None,
            'experience': None,
            'extraction_method': None,
            'details': {},
            'reasonableness_score': 0
        }
        
        text = text_box['text'].strip()
        
        try:
            # 尝试提取等级
            level = self._extract_level_from_text(text)
            if level is not None:
                candidate['level'] = level
                candidate['extraction_method'] = 'level_pattern'
                candidate['details']['level_source'] = f"single_text_{text_box.get('source', 'unknown')}"
            
            # 尝试提取经验值
            experience = self._extract_experience_from_text(text)
            if experience is not None:
                candidate['experience'] = experience
                candidate['extraction_method'] = 'experience_pattern'
                candidate['details']['experience_source'] = f"single_text_{text_box.get('source', 'unknown')}"
            
            # 如果是橙色背景优化的结果，尝试数字组合
            if 'orange_optimized' in text_box.get('source', '') or 'color_separated' in text_box.get('source', ''):
                if text.isdigit() and candidate['level'] is None:
                    num = int(text)
                    if 1 <= num <= 300:
                        candidate['level'] = num
                        candidate['extraction_method'] = 'orange_digit'
                        candidate['details']['level_source'] = 'orange_background_digit'
            
        except Exception as e:
            performance_logger.error(f"单个结果提取失败 (index {index}): {e}")
        
        return candidate
    
    def _extract_level_from_text(self, text: str) -> Optional[int]:
        """从文本中提取等级"""
        level_patterns = [
            r'LV\.?\s*(\d+)',
            r'LV:\s*(\d+)',
            r'Lv\.?\s*(\d+)',
            r'Level:?\s*(\d+)',
        ]
        
        for pattern in level_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    level = int(match.group(1))
                    if 1 <= level <= 300:
                        return level
                except ValueError:
                    continue
        
        return None
    
    def _extract_experience_from_text(self, text: str) -> Optional[Dict[str, float]]:
        """从文本中提取经验值"""
        exp_patterns = [
            r'EXP(\d+)\[([\d.]+)%\s*\]',
            r'EXP\s*(\d+)\s*\[([\d.]+)%\s*\]',
            r'EXP(\d+)\s*\[\s*([\d.]+)\s*%\s*\]',
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    exp_value = int(match.group(1))
                    exp_percentage = float(match.group(2))
                    
                    if exp_value > 0 and exp_value <= 1000000000 and 0 <= exp_percentage <= 100:
                        return {
                            'value': exp_value,
                            'percentage': exp_percentage
                        }
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _analyze_candidate_reasonableness(self, candidate: Dict[str, Any]):
        """分析候选结果的合理性 - 移除历史数据依赖"""
        score = 0
        
        # 基础置信度评分 (0-40分)
        confidence = candidate.get('confidence', 0)
        score += min(confidence * 40, 40)
        
        # 等级合理性评分 (0-30分)
        level = candidate.get('level')
        if level is not None:
            if 1 <= level <= 300:
                score += 30
            else:
                score -= 30  # 不合理的等级扣分
        
        # 经验值合理性评分 (0-30分)
        experience = candidate.get('experience')
        if experience is not None:
            exp_value = experience.get('value', 0)
            exp_percentage = experience.get('percentage', 0)
            
            if 0 < exp_value <= 1000000000 and 0 <= exp_percentage <= 100:
                score += 30
            else:
                score -= 30  # 不合理的经验值扣分
        
        # 来源可靠性评分 (0-20分)
        source = candidate.get('source', '')
        engine = candidate.get('engine', '')
        
        # EasyOCR通常更可靠
        if 'easyocr' in engine:
            score += 10
        elif 'tesseract' in engine:
            score += 8
        
        # 橙色背景优化的结果更可靠（针对我们的场景）
        if 'orange_optimized' in source:
            score += 10
        elif 'color_separated' in source:
            score += 8
        elif 'high_contrast' in source:
            score += 6
        else:
            score += 4
        
        candidate['reasonableness_score'] = score
        performance_logger.debug(f"候选结果评分: {score}, 文本: '{candidate['text']}', 来源: {source}")
    
    def _select_best_candidate(self, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """选择最佳候选结果 - 不依赖历史数据"""
        if not candidates:
            return None
        
        # 分别提取包含等级和经验值的候选
        level_candidates = [c for c in candidates if c.get('level') is not None]
        experience_candidates = [c for c in candidates if c.get('experience') is not None]
        
        # 按合理性评分排序
        level_candidates.sort(key=lambda x: x['reasonableness_score'], reverse=True)
        experience_candidates.sort(key=lambda x: x['reasonableness_score'], reverse=True)
        
        # 记录评分前几名
        performance_logger.info("=== 等级候选结果排名 ===")
        for i, candidate in enumerate(level_candidates[:3]):
            performance_logger.info(f"等级Top {i+1}: 评分={candidate['reasonableness_score']:.1f}, "
                                  f"Level={candidate.get('level')}, "
                                  f"来源={candidate.get('source')}")
        
        performance_logger.info("=== 经验值候选结果排名 ===")
        for i, candidate in enumerate(experience_candidates[:3]):
            performance_logger.info(f"经验Top {i+1}: 评分={candidate['reasonableness_score']:.1f}, "
                                  f"Exp={candidate.get('experience')}, "
                                  f"来源={candidate.get('source')}")
        
        # 选择最佳等级和经验值候选
        best_level_candidate = level_candidates[0] if level_candidates else None
        best_exp_candidate = experience_candidates[0] if experience_candidates else None
        
        # 创建综合结果
        combined_result = {
            'level': best_level_candidate.get('level') if best_level_candidate else None,
            'experience': best_exp_candidate.get('experience') if best_exp_candidate else None,
            'level_candidate': best_level_candidate,
            'experience_candidate': best_exp_candidate,
            'selection_details': {
                'level_score': best_level_candidate.get('reasonableness_score', 0) if best_level_candidate else 0,
                'experience_score': best_exp_candidate.get('reasonableness_score', 0) if best_exp_candidate else 0,
                'level_source': best_level_candidate.get('source') if best_level_candidate else None,
                'experience_source': best_exp_candidate.get('source') if best_exp_candidate else None
            }
        }
        
        # 额外的质量检查
        level = combined_result.get('level')
        experience = combined_result.get('experience')
        
        if level is not None and best_level_candidate.get('reasonableness_score', 0) < 50:
            performance_logger.warning(f"等级候选评分较低: {best_level_candidate.get('reasonableness_score'):.1f}")
        
        if experience is not None and best_exp_candidate.get('reasonableness_score', 0) < 50:
            performance_logger.warning(f"经验值候选评分较低: {best_exp_candidate.get('reasonableness_score'):.1f}")
        
        performance_logger.info(f"=== 最终选择结果 ===")
        performance_logger.info(f"等级: {level} (来源: {combined_result['selection_details']['level_source']}, 评分: {combined_result['selection_details']['level_score']:.1f})")
        performance_logger.info(f"经验: {experience} (来源: {combined_result['selection_details']['experience_source']}, 评分: {combined_result['selection_details']['experience_score']:.1f})")
        
        return combined_result
    
    def _save_ocr_result(self, game_data: Dict[str, Any], timestamp: str) -> str:
        """保存OCR结果到文件"""
        try:
            # 转换numpy类型为Python原生类型以支持JSON序列化
            serializable_data = self._make_json_serializable(game_data)
            
            result_file = os.path.join(
                self._output_folder, 'ocr_results',
                f"ocr_result_{timestamp}.json"
            )
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
                
            # 同时追加到汇总文件
            summary_file = os.path.join(self._output_folder, 'game_data_summary.json')
            
            # 读取现有数据
            summary_data = []
            if os.path.exists(summary_file):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                except:
                    summary_data = []
            
            # 添加新数据
            summary_data.append(serializable_data)
            
            # 保持最近1000条记录
            if len(summary_data) > 1000:
                summary_data = summary_data[-1000:]
            
            # 保存汇总数据
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            return result_file
                
        except Exception as e:
            performance_logger.error(f"保存OCR结果失败: {e}")
            return ""
    
    def _make_json_serializable(self, obj):
        """将对象转换为JSON可序列化格式"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        else:
            return obj
    
    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """获取最新的游戏数据"""
        try:
            summary_file = os.path.join(self._output_folder, 'game_data_summary.json')
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        return data[-1]
        except Exception as e:
            performance_logger.error(f"获取最新数据失败: {e}")
        
        return None
    
    def get_data_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取历史数据"""
        try:
            summary_file = os.path.join(self._output_folder, 'game_data_summary.json')
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data[-limit:] if data else []
        except Exception as e:
            performance_logger.error(f"获取历史数据失败: {e}")
        
        return []
    
    def _create_easyocr_visualization(self, image: Image.Image, ocr_results: Dict[str, Any], timestamp: str) -> str:
        """创建多引擎并行OCR可视化"""
        try:
            from PIL import ImageDraw, ImageFont
            
            # 创建图像副本用于绘制
            viz_image = image.copy()
            draw = ImageDraw.Draw(viz_image)
            
            # 尝试加载字体
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
                small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 12)
                tiny_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 10)
            except:
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                tiny_font = ImageFont.load_default()
            
            # 定义不同引擎和处理版本的颜色
            colors = {
                'easyocr_standard': 'red',
                'easyocr_orange_optimized': 'orange',
                'easyocr_high_contrast': 'blue',
                'easyocr_color_separated': 'green',
                'tesseract_standard': 'purple',
                'tesseract_orange_optimized': 'magenta',
                'tesseract_high_contrast': 'cyan',
                'tesseract_color_separated': 'yellow'
            }
            
            # 绘制所有识别结果
            individual_results = ocr_results.get('individual_results', [])
            candidate_results = ocr_results.get('candidate_results', [])
            selected_result = ocr_results.get('selected_result')
            
            # 绘制所有文本框
            for i, box in enumerate(individual_results):
                bbox = box['bbox']
                text = box['text']
                confidence = box['confidence']
                source = box.get('source', 'unknown')
                
                # 选择颜色
                color = colors.get(source, 'gray')
                
                # 检查是否是选中的结果
                is_selected = False
                if selected_result:
                    selected_text = selected_result.get('text', '')
                    selected_source = selected_result.get('source', '')
                    if text == selected_text and source == selected_source:
                        is_selected = True
                        color = 'lime'  # 选中结果用亮绿色
                
                # 绘制边框
                try:
                    line_width = 3 if is_selected else 2
                    
                    if isinstance(bbox[0], list):  # EasyOCR格式: [[x1,y1], [x2,y2], ...]
                        points = [(point[0], point[1]) for point in bbox]
                        draw.polygon(points, outline=color, width=line_width)
                        x1, y1 = points[0]
                    else:  # Tesseract格式: [x1, y1, x2, y2]
                        x1, y1, x2, y2 = bbox
                        draw.rectangle([x1, y1, x2, y2], outline=color, width=line_width)
                    
                    # 在文本框上方绘制标签
                    engine = box.get('engine', 'unknown')
                    version = box.get('version', 'unknown')
                    label = f"{text} ({confidence:.2f}) [{engine}_{version}]"
                    
                    if is_selected:
                        label = f"✅ {label} [SELECTED]"
                    
                    # 计算标签背景
                    y_offset = -35 if is_selected else -25
                    font_to_use = small_font if is_selected else tiny_font
                    
                    bbox_label = draw.textbbox((x1, y1 + y_offset), label, font=font_to_use)
                    draw.rectangle(bbox_label, fill='white', outline=color)
                    draw.text((x1, y1 + y_offset + 2), label, fill=color, font=font_to_use)
                    
                except Exception as e:
                    performance_logger.warning(f"绘制文本框 {i} 失败: {e}")
                    continue
            
            # 在图像顶部添加汇总信息
            summary_text = f"并行OCR识别结果 (时间: {timestamp})"
            draw.text((10, 10), summary_text, fill='black', font=font)
            
            # 添加处理摘要
            processing_summary = ocr_results.get('processing_summary', {})
            if processing_summary:
                summary_info = (f"总文本: {processing_summary.get('total_texts', 0)}, "
                              f"预处理方法: {processing_summary.get('preprocessing_methods', 0)}, "
                              f"OCR引擎: {processing_summary.get('ocr_engines', 0)}")
                draw.text((10, 35), summary_info, fill='darkblue', font=small_font)
            
            # 添加候选结果信息
            if candidate_results:
                candidate_info = f"候选结果: {len(candidate_results)} 个"
                draw.text((10, 55), candidate_info, fill='purple', font=small_font)
                
                # 显示前3个候选的评分
                top_candidates = sorted(candidate_results, key=lambda x: x.get('reasonableness_score', 0), reverse=True)[:3]
                for i, candidate in enumerate(top_candidates):
                    score = candidate.get('reasonableness_score', 0)
                    level = candidate.get('level')
                    exp = candidate.get('experience')
                    source = candidate.get('source', 'unknown')
                    
                    result_text = f"#{i+1} 评分:{score:.1f}"
                    if level is not None:
                        result_text += f" LV:{level}"
                    if exp is not None:
                        result_text += f" EXP:{exp.get('value', 0)}"
                    result_text += f" [{source}]"
                    
                    color = 'darkgreen' if i == 0 else 'orange' if i == 1 else 'brown'
                    draw.text((10, 75 + i * 15), result_text, fill=color, font=tiny_font)
            
            # 添加最终提取结果
            if selected_result:
                level = selected_result.get('level')
                experience = selected_result.get('experience')
                final_text = f"最终结果: "
                if level is not None:
                    final_text += f"LV.{level} "
                if experience is not None:
                    final_text += f"EXP:{experience.get('value', 0)}({experience.get('percentage', 0):.1f}%)"
                
                draw.text((10, image.height - 30), final_text, fill='darkgreen', font=font)
            
            # 保存可视化图像
            viz_path = os.path.join(
                self._output_folder, 'annotated_images',
                f"parallel_ocr_viz_{timestamp}.png"
            )
            
            viz_image.save(viz_path)
            
            performance_logger.info(f"并行OCR可视化已保存: {viz_path}")
            return viz_path
            
        except Exception as e:
            performance_logger.error(f"创建并行OCR可视化失败: {e}")
            return ""
    
    def run(self):
        """线程运行方法"""
        # 这个方法在QThread中是必需的，但我们使用QTimer，所以保持空实现
        pass
    
    def trigger_ocr(self):
        """触发单次OCR识别 - 新的工作流程"""
        # 更新配置
        self._config = config_manager.get('screenshot_ocr', {})
        
        # 1. 检查目标窗口是否激活
        if not self._is_target_window_active():
            performance_logger.warning("目标窗口未激活，无法进行OCR识别")
            self.error_occurred.emit("目标窗口未激活，请确保游戏窗口在前台")
            return
        
        # 2. 检查OCR引擎是否已加载
        if not self._ocr_engine_loaded:
            self._load_ocr_engines()
            if not self._ocr_engine_loaded:
                self.error_occurred.emit("OCR引擎加载失败，请检查依赖包安装")
                return
        
        # 发送触发信号
        self.ocr_triggered.emit()
        performance_logger.info("OCR触发，开始执行截图和识别...")
        
        # 3. 执行截图和OCR识别
        self._perform_single_ocr()
    
    def _perform_single_ocr(self):
        """执行单次截图和OCR识别"""
        try:
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 3. 进行截图
            screenshot = self._capture_screenshot()
            if screenshot is None:
                self.error_occurred.emit("截图失败")
                return
            
            # 检查是否为重复截图（可选的性能优化）
            screenshot_hash = self._get_image_hash(screenshot)
            if screenshot_hash == self._last_screenshot_hash and self._last_ocr_result:
                performance_logger.debug("检测到重复截图，使用缓存结果")
                self.data_extracted.emit(self._last_ocr_result)
                return
            
            self._last_screenshot_hash = screenshot_hash
            
            # 保存截图（如果配置启用）
            screenshot_path = None
            if self._config.get('save_screenshots', True):
                screenshot_path = os.path.join(
                    self._output_folder, 'screenshots', 
                    f"screenshot_{timestamp}.png"
                )
                screenshot.save(screenshot_path)
                performance_logger.info(f"截图已保存: {screenshot_path}")
            
            # 4. 进行OCR识别
            ocr_results = self._perform_ocr_parallel(screenshot)
            
            # 5. 提取游戏数据
            game_data = self._extract_game_data_individual(ocr_results)
            game_data['timestamp'] = timestamp
            game_data['screenshot_path'] = screenshot_path
            
            # 检查是否有有效数据
            if game_data.get('level') is None and game_data.get('experience') is None:
                performance_logger.warning("未提取到有效的等级或经验数据，不保存到数据库")
                self.error_occurred.emit("未识别到有效的等级或经验数据")
                return
            
            # 缓存OCR结果
            self._last_ocr_result = game_data.copy()
            
            # 6. 保存结果和可视化
            # 创建包含所有信息的完整结果用于可视化
            complete_results = {
                'individual_results': ocr_results.get('individual_results', []),
                'processing_summary': ocr_results.get('processing_summary', {}),
                'candidate_results': game_data.get('candidate_results', []),
                'selected_result': game_data.get('selected_result', None)
            }
            
            easyocr_viz_path = self._create_easyocr_visualization(
                screenshot, complete_results, timestamp
            )
            game_data['visualization_path'] = easyocr_viz_path
            
            # 保存OCR结果
            ocr_result_path = self._save_ocr_result(game_data, timestamp)
            
            # 保存到数据库（只有在有有效数据时）
            try:
                game_db.insert_game_data(game_data)
                performance_logger.info("游戏数据已保存到数据库")
            except Exception as e:
                performance_logger.error(f"保存数据到数据库失败: {e}")
            
            # 7. 发送数据信号给UI更新
            self.data_extracted.emit(game_data)
            
            total_time = time.time() - start_time
            performance_logger.info(f"单次OCR完成: {timestamp}, 总耗时: {total_time:.2f}秒")
            performance_logger.info(f"OCR结果已保存: {ocr_result_path}")
            performance_logger.info(f"识别数据: 等级={game_data.get('level')}, 经验={game_data.get('experience')}")
            
        except Exception as e:
            error_msg = f"单次OCR过程出错: {e}"
            performance_logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _capture_screenshot(self) -> Optional[Image.Image]:
        """执行截图操作 - 支持高分辨率"""
        try:
            # 根据配置决定截图方式
            if self._config.get('capture_window_only', True):
                # 只截取目标窗口内容
                window_bounds = self._get_target_window_bounds()
                if window_bounds:
                    screenshot = self._capture_window_screenshot(window_bounds)
                else:
                    performance_logger.warning("无法获取窗口边界，使用全屏截图")
                    screenshot = ImageGrab.grab(all_screens=True)
                    
                    # 应用缩放因子
                    scale_factor = self._config.get('screenshot_scale', 2.0)
                    if scale_factor != 1.0:
                        new_width = int(screenshot.width * scale_factor)
                        new_height = int(screenshot.height * scale_factor)
                        screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        performance_logger.info(f"全屏截图已缩放到 {scale_factor}x 分辨率: {new_width}x{new_height}")
            else:
                # 全屏截图
                screenshot = ImageGrab.grab(all_screens=True)
                
                # 应用缩放因子
                scale_factor = self._config.get('screenshot_scale', 2.0)
                if scale_factor != 1.0:
                    new_width = int(screenshot.width * scale_factor)
                    new_height = int(screenshot.height * scale_factor)
                    screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    performance_logger.info(f"全屏截图已缩放到 {scale_factor}x 分辨率: {new_width}x{new_height}")
            
            return screenshot
            
        except Exception as e:
            performance_logger.error(f"截图失败: {e}")
            return None 