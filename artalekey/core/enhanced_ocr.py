import os
import time
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PIL import Image, ImageGrab
import cv2
import numpy as np
from artalekey.core.logger import performance_logger
from artalekey.core.config import config_manager
from artalekey.core.window_detector import WindowDetector
from artalekey.core.database import game_db

class EnhancedOCRManager(QThread):
    """增强的OCR管理器 - 使用EasyOCR，优化性能"""
    
    # 信号定义
    ocr_started = pyqtSignal()
    ocr_stopped = pyqtSignal()
    data_extracted = pyqtSignal(dict)  # 发送提取的数据
    error_occurred = pyqtSignal(str)   # 发送错误信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window_detector = WindowDetector()
        self._running = False
        self._timer = None
        self._output_folder = None
        self._config = {}
        
        # OCR引擎 - 延迟加载
        self._easyocr_reader = None
        self._ocr_engine_loaded = False
        self._engine_loading = False
        
        # 性能优化缓存
        self._last_screenshot_hash = None
        self._last_ocr_result = None
        self._last_window_bounds = None
        self._bounds_cache_time = 0
        self._bounds_cache_duration = 5.0  # 窗口边界缓存5秒
        
        # 图像预处理缓存
        self._preprocessed_cache = {}
        self._cache_max_size = 3
        
        self._setup_output_folder()
        
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
    
    def _load_ocr_engine(self):
        """延迟加载EasyOCR引擎 - 避免启动时阻塞"""
        if self._ocr_engine_loaded or self._engine_loading:
            return
            
        self._engine_loading = True
        try:
            performance_logger.info("开始加载EasyOCR引擎...")
            start_time = time.time()
            
            import easyocr
            # 优化：只加载必要的语言，禁用GPU以提高兼容性
            self._easyocr_reader = easyocr.Reader(['en', 'ch_sim'], gpu=False, verbose=False)
            
            load_time = time.time() - start_time
            self._ocr_engine_loaded = True
            performance_logger.info(f"EasyOCR引擎加载成功，耗时: {load_time:.2f}秒")
            
        except Exception as e:
            performance_logger.error(f"EasyOCR引擎加载失败: {e}")
            self._ocr_engine_loaded = False
        finally:
            self._engine_loading = False
    
    def _get_image_hash(self, image: Image.Image) -> str:
        """计算图像哈希值，用于检测重复截图"""
        # 缩小图像并计算哈希，提高性能
        small_image = image.resize((64, 64))
        image_array = np.array(small_image)
        return str(hash(image_array.tobytes()))
    
    def _preprocess_image(self, image: Image.Image) -> np.ndarray:
        """预处理图像以提高OCR准确性"""
        image_hash = self._get_image_hash(image)
        
        # 检查缓存
        if image_hash in self._preprocessed_cache:
            performance_logger.debug("使用预处理图像缓存")
            return self._preprocessed_cache[image_hash]
        
        # 转换为numpy数组
        img_array = np.array(image)
        
        # 图像预处理优化
        # 1. 转换为灰度图（提高OCR速度）
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
            
        # 2. 自适应阈值处理（提高文字识别率）
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # 3. 轻微的形态学操作（去噪）
        kernel = np.ones((2, 2), np.uint8)
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
        
        # 转换回RGB格式供EasyOCR使用
        processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        
        # 缓存管理
        if len(self._preprocessed_cache) >= self._cache_max_size:
            # 移除最旧的缓存项
            oldest_key = next(iter(self._preprocessed_cache))
            del self._preprocessed_cache[oldest_key]
        
        self._preprocessed_cache[image_hash] = processed_rgb
        return processed_rgb
    
    def start_monitoring(self):
        """开始监控 - 优化版本"""
        if self._running:
            return
        
        # 延迟加载OCR引擎
        if not self._ocr_engine_loaded:
            self._load_ocr_engine()
            if not self._ocr_engine_loaded:
                self.error_occurred.emit("EasyOCR引擎加载失败，请检查依赖包安装")
                return
            
        self._running = True
        self._config = config_manager.get('screenshot_ocr', {})
        
        # 清理缓存
        self._last_screenshot_hash = None
        self._last_ocr_result = None
        self._preprocessed_cache.clear()
        
        # 如果配置了立即截图，先执行一次
        if self._config.get('immediate_capture_on_start', True):
            performance_logger.info("立即执行首次截图和OCR识别")
            self._take_screenshot_and_ocr()
        
        # 设置定时器
        interval_seconds = self._config.get('interval', 10)
        self._timer = QTimer()
        self._timer.timeout.connect(self._take_screenshot_and_ocr)
        self._timer.start(interval_seconds * 1000)  # 转换为毫秒
        
        self.ocr_started.emit()
        performance_logger.info(f"OCR监控已启动，间隔: {interval_seconds}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self._running:
            return
            
        self._running = False
        
        if self._timer:
            self._timer.stop()
            self._timer = None
            
        self.ocr_stopped.emit()
        performance_logger.info("OCR监控已停止")
    
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
        """截取指定窗口区域的截图"""
        try:
            # 截取指定区域
            x, y, width, height = bounds['x'], bounds['y'], bounds['width'], bounds['height']
            
            # 使用PIL截取指定区域
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            
            performance_logger.info(f"成功截取窗口区域: {x},{y},{width},{height}")
            return screenshot
            
        except Exception as e:
            performance_logger.error(f"截取窗口截图失败: {e}")
            return None
    
    def _take_screenshot_and_ocr(self):
        """执行截屏和OCR识别 - 优化版本"""
        if not self._running:
            return
            
        # 检查目标窗口是否激活
        if not self._is_target_window_active():
            performance_logger.debug("目标窗口未激活，跳过截屏")
            return
            
        try:
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot = None
            
            # 根据配置决定截图方式
            if self._config.get('capture_window_only', True):
                # 只截取目标窗口内容
                window_bounds = self._get_target_window_bounds()
                if window_bounds:
                    screenshot = self._capture_window_screenshot(window_bounds)
                else:
                    performance_logger.warning("无法获取窗口边界，使用全屏截图")
                    screenshot = ImageGrab.grab()
            else:
                # 全屏截图
                screenshot = ImageGrab.grab()
            
            if screenshot is None:
                performance_logger.error("截图失败")
                return
            
            # 检查是否为重复截图
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
            
            # 进行OCR识别
            ocr_results = self._perform_ocr(screenshot)
            
            # 提取游戏数据
            game_data = self._extract_game_data(ocr_results)
            game_data['timestamp'] = timestamp
            game_data['screenshot_path'] = screenshot_path
            
            # 缓存OCR结果
            self._last_ocr_result = game_data.copy()
            
            # 使用EasyOCR自带的可视化功能
            easyocr_viz_path = self._create_easyocr_visualization(
                screenshot, ocr_results, timestamp
            )
            game_data['visualization_path'] = easyocr_viz_path
            
            # 保存OCR结果
            ocr_result_path = self._save_ocr_result(game_data, timestamp)
            
            # 保存到数据库
            try:
                game_db.insert_game_data(game_data)
                performance_logger.info("游戏数据已保存到数据库")
            except Exception as e:
                performance_logger.error(f"保存数据到数据库失败: {e}")
            
            # 发送数据信号
            self.data_extracted.emit(game_data)
            
            total_time = time.time() - start_time
            performance_logger.info(f"截屏OCR完成: {timestamp}, 总耗时: {total_time:.2f}秒")
            performance_logger.info(f"OCR结果已保存: {ocr_result_path}")
            performance_logger.info(f"识别数据: 等级={game_data.get('level')}, 经验={game_data.get('experience')}, 金钱={game_data.get('money')}")
            
        except Exception as e:
            error_msg = f"增强截屏OCR过程出错: {e}"
            performance_logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _perform_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """执行EasyOCR识别"""
        results = {
            'easyocr_results': [],
            'combined_text': '',
            'text_boxes': []
        }
        
        try:
            # 转换为RGB格式（EasyOCR需要RGB）
            rgb_image = np.array(image)
            
            # 使用EasyOCR进行全图识别
            easyocr_results = self._easyocr_reader.readtext(rgb_image)
            
            # 调试信息：记录所有识别到的文本
            performance_logger.debug(f"EasyOCR原始识别结果: {len(easyocr_results)} 个文本")
            for i, (bbox, text, confidence) in enumerate(easyocr_results):
                performance_logger.debug(f"  文本{i+1}: '{text}' (置信度: {confidence:.3f})")
            
            accepted_texts = []
            filtered_texts = []
            
            for (bbox, text, confidence) in easyocr_results:
                # 进一步降低置信度要求，特别是对游戏相关文本
                text_stripped = text.strip()
                is_relevant = self._is_game_relevant_text(text_stripped)
                
                # 对游戏相关文本使用更低的置信度阈值
                min_confidence = 0.05 if is_relevant else 0.3
                
                performance_logger.debug(f"文本 '{text_stripped}' (置信度: {confidence:.3f}) 相关性: {is_relevant}, 阈值: {min_confidence}")
                
                if confidence > min_confidence:
                    if is_relevant:
                        results['text_boxes'].append({
                            'text': text_stripped,
                            'bbox': bbox,
                            'confidence': confidence,
                            'source': 'easyocr'
                        })
                        results['combined_text'] += text_stripped + ' '
                        accepted_texts.append(text_stripped)
                        performance_logger.debug(f"✅ 接受文本: '{text_stripped}'")
                    else:
                        # 高置信度的非相关文本也保留
                        if confidence > 0.5:
                            results['text_boxes'].append({
                                'text': text_stripped,
                                'bbox': bbox,
                                'confidence': confidence,
                                'source': 'easyocr',
                                'filtered': True
                            })
                            filtered_texts.append(text_stripped)
                else:
                    performance_logger.debug(f"❌ 拒绝文本: '{text_stripped}' (置信度过低)")
            
            results['easyocr_results'] = easyocr_results
            performance_logger.info(f"EasyOCR识别完成，接受 {len(accepted_texts)} 个相关文本，过滤 {len(filtered_texts)} 个文本")
            if accepted_texts:
                performance_logger.info(f"接受的文本: {', '.join(accepted_texts[:5])}{'...' if len(accepted_texts) > 5 else ''}")
            
        except Exception as e:
            performance_logger.error(f"EasyOCR识别失败: {e}")
        
        return results
    
    def _is_game_relevant_text(self, text: str) -> bool:
        """判断文本是否与游戏数据相关 - 专注于关键数据"""
        text_lower = text.lower().strip()
        
        # 高优先级：等级相关
        if re.search(r'lv\.?\s*\d+', text_lower):
            return True
        
        # 高优先级：经验值格式 [数字][百分比%]
        if re.search(r'\d+\s*[\[\(]\s*\d+\.?\d*\s*%', text):
            return True
        
        # 高优先级：大数字（可能是金钱或经验）
        if re.search(r'\d{4,}', text):  # 4位以上数字
            return True
        
        # 高优先级：逗号分隔的数字（金钱格式）
        if re.search(r'\d{1,3}(?:,\d{3})+', text):
            return True
        
        # 中优先级：包含百分号的数字
        if re.search(r'\d+\.?\d*\s*%', text):
            return True
        
        # 中优先级：游戏相关关键词
        game_keywords = [
            'lv', 'level', 'exp', 'gold', 'meso', '币', '经验', '等级', 
            'hp', 'mp', 'pp', '攻击', '防御', '魔法', '敏捷', '幸运',
            'str', 'dex', 'int', 'luk', '力量', '敏捷', '智力', '运气',
            'maplestory', 'worlds'
        ]
        for keyword in game_keywords:
            if keyword in text_lower:
                return True
        
        # 低优先级：包含数字的文本
        if re.search(r'\d', text) and len(text.strip()) >= 2:
            return True
        
        return False
    
    def _extract_game_data(self, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
        """从OCR结果中提取游戏数据"""
        game_data = {
            'level': None,
            'experience': None,
            'money': None,
            'raw_text': ocr_results['combined_text'],
            'text_boxes': ocr_results['text_boxes'],
            'extraction_details': {}  # 记录提取详情
        }
        
        try:
            combined_text = ocr_results['combined_text']
            performance_logger.info(f"开始数据提取，合并文本: '{combined_text}'")
            
            # 从合并文本中提取数据
            self._extract_from_combined_text(combined_text, game_data)
            
            # 使用文本框位置和内容进行精确提取
            self._extract_data_from_boxes(ocr_results['text_boxes'], game_data)
            
            performance_logger.info(f"数据提取结果: Level={game_data['level']}, Exp={game_data['experience']}, Money={game_data['money']}")
            
        except Exception as e:
            performance_logger.error(f"提取游戏数据失败: {e}")
        
        return game_data
    
    def _extract_from_combined_text(self, combined_text: str, game_data: Dict[str, Any]):
        """从合并文本中提取数据"""
        try:
            # 提取等级信息 - 针对 "LV.58" 格式
            if not game_data['level']:
                level_patterns = [
                    r'LV\.?\s*(\d+)',
                    r'Level\.?\s*(\d+)',
                    r'等级\.?\s*(\d+)'
                ]
                
                for pattern in level_patterns:
                    level_match = re.search(pattern, combined_text, re.IGNORECASE)
                    if level_match:
                        game_data['level'] = int(level_match.group(1))
                        game_data['extraction_details']['level_source'] = 'combined_text'
                        break
            
            # 提取经验值信息 - 针对 "EXP 542552149 [49.88%]" 格式优化
            if not game_data['experience']:
                exp_patterns = [
                    # 优先匹配明确的EXP格式
                    r'EXP\.?\s+(\d+(?:,\d{3})*)\s*[\[\(](\d+(?:\.\d+)?)%[\]\)]',  # EXP 542552149 [49.88%]
                    r'EXP\.?\s+(\d+(?:,\d{3})*)\s+[\[\(](\d+(?:\.\d+)?)%[\]\)]',  # EXP 542552149 [49.88%] (多空格)
                    r'EXP\s*(\d+(?:,\d{3})*)\s*[\[\(](\d+(?:\.\d+)?)%[\]\)]',     # EXP542552149[49.88%] (紧凑格式)
                    # 通用格式
                    r'(\d+(?:,\d{3})*)\s*[\[\(](\d+(?:\.\d+)?)%[\]\)]',           # 542552149[49.88%]
                    r'(\d+(?:,\d{3})*)/(\d+(?:,\d{3})*)\s*\((\d+(?:\.\d+)?)%?\)', # 495632/1087536(45.57%)
                    # 容错格式（处理OCR识别错误）
                    r'[^\d]*(\d+)\s*[\[\(](\d+(?:\.\d+)?)%',                      # 巨522892[4808% (包含前缀字符)
                    r'(\d{4,})\s*[\[\(](\d+(?:\.\d+)?)%?',                        # 522892[4808 (4位以上数字+百分比)
                ]
                
                for pattern in exp_patterns:
                    exp_match = re.search(pattern, combined_text)
                    if exp_match:
                        try:
                            if len(exp_match.groups()) == 2:  # 格式1: 495632[45.57%] 或 巨522892[4808%
                                exp_value = int(exp_match.group(1).replace(',', ''))
                                exp_percentage = float(exp_match.group(2))
                            elif len(exp_match.groups()) == 3:  # 格式2: 495632/1087536(45.57%)
                                exp_value = int(exp_match.group(1).replace(',', ''))
                                exp_percentage = float(exp_match.group(3))
                            
                            # 验证数据合理性 - 处理OCR识别错误
                            # 如果百分比过大，可能是小数点丢失，尝试修正
                            if exp_percentage > 100:
                                # 尝试将百分比除以100（如4808 -> 48.08）
                                if exp_percentage <= 10000:
                                    exp_percentage = exp_percentage / 100
                                else:
                                    # 百分比过大，可能是识别错误，跳过
                                    continue
                            
                            # 添加经验值合理性检查（调整为10亿上限，适应高等级游戏）
                            if exp_value > 0 and exp_value <= 1000000000 and 0 <= exp_percentage <= 100:
                                game_data['experience'] = {
                                    'value': exp_value,
                                    'percentage': exp_percentage
                                }
                                game_data['extraction_details']['experience_source'] = 'combined_text'
                                performance_logger.info(f"从合并文本提取经验: {exp_value} ({exp_percentage}%)")
                                break
                            else:
                                performance_logger.warning(f"经验值数据不合理，跳过: {exp_value} ({exp_percentage}%)")
                        except (ValueError, IndexError) as e:
                            performance_logger.warning(f"经验值解析失败: {e}, 文本: {exp_match.group()}")
                            continue
            
            # 提取金钱信息 - 针对 "2,669,704" 格式
            if not game_data['money']:
                money_patterns = [
                    r'(\d{1,3}(?:,\d{3})+)(?!\s*[\[\(/])',  # 匹配逗号分隔的大数字，但不是经验值
                    r'金钱[:\s]*(\d{1,3}(?:,\d{3})*)',
                    r'Money[:\s]*(\d{1,3}(?:,\d{3})*)',
                    r'(\d{1,3}(?:,\d{3})*)\s*(?:gold|meso|币)',
                ]
                
                for pattern in money_patterns:
                    money_matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                    for money_match in money_matches:
                        money_value_str = money_match.group(1).replace(',', '')
                        money_value = int(money_value_str)
                        
                        # 过滤掉可能是经验值的数字（通常经验值较小）
                        if money_value > 100000:  # 金钱通常比经验值大
                            game_data['money'] = money_value
                            game_data['extraction_details']['money_source'] = 'combined_text'
                            break
                    
                    if game_data['money']:
                        break
                        
        except Exception as e:
            performance_logger.error(f"从合并文本提取数据失败: {e}")
    
    def _extract_data_from_boxes(self, text_boxes: List[Dict], game_data: Dict[str, Any]):
        """从文本框中提取更精确的数据"""
        try:
            # 按位置对文本框进行分组，便于组合识别
            all_texts = []
            for box in text_boxes:
                text = box['text'].strip()
                confidence = box.get('confidence', 0)
                
                # 对游戏相关文本使用更低的置信度要求
                is_relevant = self._is_game_relevant_text(text)
                min_confidence = 0.1 if is_relevant else 0.5
                
                if confidence < min_confidence:
                    continue
                
                all_texts.append({
                    'text': text,
                    'bbox': box['bbox'],
                    'confidence': confidence,
                    'region': box.get('region', 'unknown')
                })
            
            # 尝试组合相邻的文本来重建完整信息
            combined_texts = self._combine_nearby_texts(all_texts)
            
            # 从组合文本中提取数据
            for combined_text in combined_texts:
                text = combined_text['text']
                
                # 查找等级相关的文本框
                if not game_data['level']:
                    # 更精确的等级匹配，优先匹配明确的等级格式
                    level_patterns = [
                        r'LV\.?\s*(\d+)',
                        r'Level\.?\s*(\d+)',
                        r'等级\.?\s*(\d+)',
                    ]
                    
                    # 首先尝试明确的等级格式
                    for pattern in level_patterns:
                        level_match = re.search(pattern, text, re.IGNORECASE)
                        if level_match:
                            level_value = int(level_match.group(1))
                            if 1 <= level_value <= 300:  # 合理的等级范围
                                game_data['level'] = level_value
                                game_data['extraction_details']['level_source'] = 'text_box'
                                performance_logger.info(f"从文本框提取等级: {level_value}")
                                break
                    
                    # 如果没有找到明确格式，再尝试单独数字（但要更严格）
                    if not game_data['level']:
                        # 只有当文本是纯数字且在合理范围内时才认为是等级
                        if re.match(r'^\d{1,3}$', text.strip()):
                            level_value = int(text.strip())
                            # 更严格的等级范围，避免误识别大数字
                            if 1 <= level_value <= 200 and level_value not in [542552149, 2723302]:  # 排除明显的经验值和金钱
                                game_data['level'] = level_value
                                game_data['extraction_details']['level_source'] = 'text_box'
                                performance_logger.info(f"从文本框提取等级（纯数字）: {level_value}")
                
                # 查找经验相关的文本框 - 针对EXP格式优化
                if not game_data['experience']:
                    exp_patterns = [
                        # 优先匹配明确的EXP格式
                        r'EXP\.?\s+(\d+(?:,\d{3})*)\s*[\[\(](\d+(?:\.\d+)?)%[\]\)]',  # EXP 542552149 [49.88%]
                        r'EXP\.?\s+(\d+(?:,\d{3})*)\s+[\[\(](\d+(?:\.\d+)?)%[\]\)]',  # EXP 542552149 [49.88%] (多空格)
                        r'EXP\s*(\d+(?:,\d{3})*)\s*[\[\(](\d+(?:\.\d+)?)%[\]\)]',     # EXP542552149[49.88%] (紧凑格式)
                        # 通用格式
                        r'(\d+(?:,\d{3})*)\s*[\[\(](\d+(?:\.\d+)?)%[\]\)]',           # 542552149[49.88%]
                        r'(\d+(?:,\d{3})*)\s*[\[\(](\d+)[\]\)]',                      # 无小数点
                        r'(\d{4,})\s*[\[\(](\d+(?:\.\d+)?)%?[\]\)]',                  # 4位以上数字+百分比
                        # 容错格式
                        r'[^\d]*(\d+)\s*[\[\(](\d+(?:\.\d+)?)%',                      # 巨522892[4808% (包含前缀字符)
                        r'(\d{4,})\s*[\[\(](\d+(?:\.\d+)?)%?',                        # 522892[4808 (4位以上数字+百分比)
                        r'(\d{4,})',                                                  # 单独的大数字可能是经验值
                    ]
                    
                    for pattern in exp_patterns:
                        exp_match = re.search(pattern, text)
                        if exp_match:
                            try:
                                if len(exp_match.groups()) >= 2:
                                    exp_value = int(exp_match.group(1).replace(',', ''))
                                    try:
                                        exp_percentage = float(exp_match.group(2))
                                    except:
                                        exp_percentage = 0.0
                                    
                                    # 验证数据合理性 - 处理OCR识别错误
                                    # 如果百分比过大，可能是小数点丢失，尝试修正
                                    if exp_percentage > 100:
                                        # 尝试将百分比除以100（如4808 -> 48.08）
                                        if exp_percentage <= 10000:
                                            exp_percentage = exp_percentage / 100
                                        else:
                                            # 百分比过大，可能是识别错误，跳过
                                            continue
                                    
                                    # 添加经验值合理性检查（调整为10亿上限，适应高等级游戏）
                                    if exp_value > 0 and exp_value <= 1000000000 and 0 <= exp_percentage <= 100:
                                        game_data['experience'] = {
                                            'value': exp_value,
                                            'percentage': exp_percentage
                                        }
                                        game_data['extraction_details']['experience_source'] = 'text_box'
                                        performance_logger.info(f"从文本框提取经验: {exp_value} ({exp_percentage}%)")
                                        break
                                    else:
                                        performance_logger.warning(f"文本框经验值数据不合理，跳过: {exp_value} ({exp_percentage}%)")
                                elif len(exp_match.groups()) == 1:
                                    exp_value = int(exp_match.group(1).replace(',', ''))
                                    # 添加经验值合理性检查（调整为10亿上限）
                                    if exp_value > 1000 and exp_value <= 1000000000:  # 可能的经验值，但不能太大
                                        game_data['experience'] = {
                                            'value': exp_value,
                                            'percentage': 0.0
                                        }
                                        game_data['extraction_details']['experience_source'] = 'text_box'
                                        performance_logger.info(f"从文本框提取经验值: {exp_value}")
                                        break
                                    else:
                                        performance_logger.warning(f"单独经验值数据不合理，跳过: {exp_value}")
                            except (ValueError, IndexError) as e:
                                performance_logger.warning(f"文本框经验值解析失败: {e}, 文本: {text}")
                                continue
                
                # 查找金钱相关的文本框 - 更灵活的匹配
                if not game_data['money']:
                    money_patterns = [
                        r'(\d{1,3}(?:,\d{3})+)',  # 逗号分隔的大数字
                        r'(\d{6,})',  # 6位以上的数字可能是金钱
                    ]
                    
                    for pattern in money_patterns:
                        money_match = re.search(pattern, text)
                        if money_match:
                            money_value = int(money_match.group(1).replace(',', ''))
                            # 确保这是金钱而不是经验值
                            if money_value > 100000 and '%' not in text:
                                game_data['money'] = money_value
                                game_data['extraction_details']['money_source'] = 'text_box'
                                performance_logger.info(f"从文本框提取金钱: {money_value}")
                                break
                            
        except Exception as e:
            performance_logger.error(f"从文本框提取数据失败: {e}")
    
    def _combine_nearby_texts(self, text_boxes: List[Dict]) -> List[Dict]:
        """组合相邻的文本框以重建完整信息"""
        try:
            if not text_boxes:
                return []
            
            # 按Y坐标排序（从上到下）
            sorted_boxes = sorted(text_boxes, key=lambda x: self._get_bbox_center(x['bbox'])[1])
            
            combined = []
            current_line = []
            current_y = None
            y_threshold = 30  # Y坐标差异阈值
            
            for box in sorted_boxes:
                center_x, center_y = self._get_bbox_center(box['bbox'])
                
                if current_y is None or abs(center_y - current_y) <= y_threshold:
                    # 同一行
                    current_line.append(box)
                    current_y = center_y
                else:
                    # 新的一行
                    if current_line:
                        combined.append(self._merge_line_texts(current_line))
                    current_line = [box]
                    current_y = center_y
            
            # 处理最后一行
            if current_line:
                combined.append(self._merge_line_texts(current_line))
            
            # 同时保留原始的单个文本框
            for box in text_boxes:
                combined.append({
                    'text': box['text'],
                    'bbox': box['bbox'],
                    'confidence': box['confidence']
                })
            
            return combined
            
        except Exception as e:
            performance_logger.error(f"组合相邻文本失败: {e}")
            return text_boxes
    
    def _get_bbox_center(self, bbox) -> Tuple[float, float]:
        """获取边界框中心点"""
        try:
            if isinstance(bbox[0], list):  # [[x1,y1], [x2,y2], ...]格式
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                center_x = sum(x_coords) / len(x_coords)
                center_y = sum(y_coords) / len(y_coords)
            else:  # [x1, y1, x2, y2]格式
                center_x = (bbox[0] + bbox[2]) / 2
                center_y = (bbox[1] + bbox[3]) / 2
            
            return center_x, center_y
        except:
            return 0.0, 0.0
    
    def _merge_line_texts(self, line_boxes: List[Dict]) -> Dict:
        """合并同一行的文本框"""
        try:
            # 按X坐标排序（从左到右）
            sorted_line = sorted(line_boxes, key=lambda x: self._get_bbox_center(x['bbox'])[0])
            
            merged_text = ' '.join([box['text'] for box in sorted_line])
            avg_confidence = sum([box['confidence'] for box in sorted_line]) / len(sorted_line)
            
            # 使用第一个框的bbox作为代表
            merged_bbox = sorted_line[0]['bbox']
            
            return {
                'text': merged_text,
                'bbox': merged_bbox,
                'confidence': avg_confidence
            }
        except Exception as e:
            performance_logger.error(f"合并行文本失败: {e}")
            return line_boxes[0] if line_boxes else {'text': '', 'bbox': [], 'confidence': 0}
    
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
        """使用PIL创建EasyOCR可视化"""
        try:
            from PIL import ImageDraw, ImageFont
            
            # 创建图像副本用于绘制
            viz_image = image.copy()
            draw = ImageDraw.Draw(viz_image)
            
            # 尝试加载字体
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # 绘制文本框和识别结果
            for box in ocr_results['text_boxes']:
                bbox = box['bbox']
                text = box['text']
                confidence = box['confidence']
                
                # EasyOCR的bbox格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                points = [(point[0], point[1]) for point in bbox]
                
                # 绘制边框
                draw.polygon(points, outline='red', width=2)
                
                # 在文本框上方绘制文本和置信度
                x1, y1 = points[0]
                label = f"{text} ({confidence:.2f})"
                draw.text((x1, y1-20), label, fill='red', font=font)
            
            # 保存可视化图像
            viz_path = os.path.join(
                self._output_folder, 'annotated_images',
                f"easyocr_viz_{timestamp}.png"
            )
            
            viz_image.save(viz_path)
            
            performance_logger.info(f"EasyOCR可视化已保存: {viz_path}")
            return viz_path
            
        except Exception as e:
            performance_logger.error(f"创建EasyOCR可视化失败: {e}")
            return ""
    
    def run(self):
        """线程运行方法"""
        # 这个方法在QThread中是必需的，但我们使用QTimer，所以保持空实现
        pass 