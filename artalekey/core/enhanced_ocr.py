import os
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PIL import Image, ImageGrab
from artalekey.core.logger import performance_logger
from artalekey.core.config import config_manager
from artalekey.core.window_detector import WindowDetector
from artalekey.core.database import game_db, _get_app_data_dir
from artalekey.core.llm_processor import LLMProcessor

class EnhancedOCRManager(QThread):
    """图片处理管理器 - 使用 LLM 识别游戏界面信息"""
    
    # 信号定义
    ocr_triggered = pyqtSignal()       # 处理触发信号
    data_extracted = pyqtSignal(dict)  # 发送提取的数据
    error_occurred = pyqtSignal(str)   # 发送错误信息
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window_detector = WindowDetector()
        self._output_folder = None
        self._config = {}
        
        # LLM 处理器
        self.llm_processor = LLMProcessor()
        
        # 异步处理相关
        self._processing_future = None
        self._processing_timer = QTimer()
        self._processing_timer.timeout.connect(self._check_processing_result)
        self._current_screenshot = None
        self._current_timestamp = None
        
        # 缓存机制
        self._last_screenshot_hash = None
        self._last_result = None
        self._last_window_bounds = None
        self._bounds_cache_time = 0
        self._bounds_cache_duration = 5.0  # 窗口边界缓存5秒
        
        self._setup_output_folder()
        
    def _setup_output_folder(self):
        """设置输出文件夹"""
        # 使用应用数据目录
        self._output_folder = _get_app_data_dir()
        
        # 创建主文件夹和子文件夹
        os.makedirs(self._output_folder, exist_ok=True)
        os.makedirs(os.path.join(self._output_folder, 'screenshots'), exist_ok=True)
        os.makedirs(os.path.join(self._output_folder, 'llm_results'), exist_ok=True)
        
        performance_logger.info(f"输出文件夹设置为: {self._output_folder}")
    
    def _get_image_hash(self, image: Image.Image) -> str:
        """计算图像哈希值，用于检测重复截图"""
        import numpy as np
        small_image = image.resize((64, 64))
        image_array = np.array(small_image)
        return str(hash(image_array.tobytes()))
    
    def _is_target_window_active(self) -> bool:
        """检查目标窗口是否激活"""
        target_window = self._config.get('target_window', 'MapleStory Worlds')
        
        try:
            active_window = self.window_detector.get_active_window()
            if active_window:
                window_text = f"{active_window.process_name} {active_window.title}".lower()
                if target_window.lower() in window_text:
                    return True
        except Exception as e:
            performance_logger.error(f"检查活动窗口失败: {e}")
            
        return False
    
    def _get_target_window_bounds(self) -> Optional[Dict]:
        """获取目标窗口的边界坐标 - 带缓存"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (self._last_window_bounds and 
            current_time - self._bounds_cache_time < self._bounds_cache_duration):
            performance_logger.debug("使用窗口边界缓存")
            return self._last_window_bounds
        
        target_window = self._config.get('target_window', 'MapleStory Worlds')
        
        try:
            # 尝试直接获取游戏窗口区域
            if hasattr(self.window_detector, 'get_game_window_region'):
                bounds = self.window_detector.get_game_window_region(target_window)
                if bounds:
                    performance_logger.debug(f"获取目标窗口边界: {bounds}")
                    self._last_window_bounds = bounds
                    self._bounds_cache_time = current_time
                    return bounds
            
            # 备用方案
            active_window = self.window_detector.get_active_window()
            if active_window:
                window_text = f"{active_window.process_name} {active_window.title}".lower()
                if target_window.lower() in window_text:
                    if active_window.bounds and all(k in active_window.bounds for k in ['x', 'y', 'width', 'height']):
                        self._last_window_bounds = active_window.bounds
                        self._bounds_cache_time = current_time
                        return active_window.bounds
                    
                    bounds = self.window_detector.get_window_bounds(active_window)
                    if bounds:
                        self._last_window_bounds = bounds
                        self._bounds_cache_time = current_time
                        return bounds
        except Exception as e:
            performance_logger.error(f"获取目标窗口边界失败: {e}")
        
        self._last_window_bounds = None
        return None
    
    def _capture_window_screenshot(self, bounds: Dict) -> Optional[Image.Image]:
        """截取指定窗口区域的完整截图"""
        try:
            # 获取窗口边界
            x, y, width, height = bounds['x'], bounds['y'], bounds['width'], bounds['height']
            
            performance_logger.info(f"截取完整窗口区域: {x},{y},{width},{height}")
            
            # 使用PIL截取完整窗口区域
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height), all_screens=True)
            
            performance_logger.info(f"成功截取完整窗口区域，尺寸: {screenshot.width}x{screenshot.height}")
            return screenshot
            
        except Exception as e:
            performance_logger.error(f"截取窗口截图失败: {e}")
            return None
    
    def _save_result(self, game_data: Dict[str, Any], timestamp: str) -> str:
        """保存处理结果到文件"""
        try:
            result_file = os.path.join(
                self._output_folder, 'llm_results',
                f"llm_result_{timestamp}.json"
            )
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(game_data, f, indent=2, ensure_ascii=False)
                
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
            summary_data.append(game_data)
            
            # 保持最近1000条记录
            if len(summary_data) > 1000:
                summary_data = summary_data[-1000:]
            
            # 保存汇总数据
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            return result_file
                
        except Exception as e:
            performance_logger.error(f"保存处理结果失败: {e}")
            return ""
    
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
    
    def update_llm_api_key(self, api_key: str):
        """更新 LLM API 密钥"""
        if hasattr(self, 'llm_processor') and self.llm_processor:
            self.llm_processor.update_api_key(api_key)
            performance_logger.info("LLM API 密钥已更新")
    
    def run(self):
        """线程运行方法"""
        # QThread 必需方法，使用 QTimer 所以保持空实现
        pass
    
    def trigger_ocr(self):
        """触发单次图片处理"""
        # 更新配置
        self._config = config_manager.get('screenshot_ocr', {})
        
        # 1. 检查目标窗口是否激活
        if not self._is_target_window_active():
            performance_logger.warning("目标窗口未激活，无法进行图片处理")
            self.error_occurred.emit("目标窗口未激活，请确保游戏窗口在前台")
            return
        
        # 发送触发信号
        self.ocr_triggered.emit()
        performance_logger.info("图片处理触发，开始执行截图和LLM识别...")
        
        # 2. 执行截图和LLM处理
        self._perform_single_process()
    
    def _perform_single_process(self):
        """执行单次截图和LLM处理"""
        try:
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 1. 进行截图
            screenshot = self._capture_screenshot()
            if screenshot is None:
                self.error_occurred.emit("截图失败")
                return
            
            # 检查是否为重复截图（可选的性能优化）
            screenshot_hash = self._get_image_hash(screenshot)
            if screenshot_hash == self._last_screenshot_hash and self._last_result:
                performance_logger.debug("检测到重复截图，使用缓存结果")
                self.data_extracted.emit(self._last_result)
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
            
            # 2. 异步进行LLM处理
            self._current_screenshot = screenshot
            self._current_timestamp = timestamp
            self._current_screenshot_path = screenshot_path
            self._current_start_time = start_time
            
            performance_logger.info("开始异步 LLM 图片处理...")
            
            # 使用优化的异步方式处理，不传递回调函数
            # 回调会在_check_processing_result中在主线程执行
            self._processing_future = self.llm_processor.process_image_async(screenshot)
            
            # 启动定时器检查处理结果
            self._processing_timer.start(100)  # 每100ms检查一次
            
        except Exception as e:
            error_msg = f"单次LLM处理过程出错: {e}"
            performance_logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _check_processing_result(self):
        """检查异步处理结果"""
        if self._processing_future and self._processing_future.done():
            self._processing_timer.stop()
            
            try:
                # 获取异步处理结果
                llm_data = self._processing_future.result()
                # 在主线程中处理结果
                self._on_llm_processing_complete(llm_data)
                
            except Exception as e:
                performance_logger.error(f"获取异步处理结果失败: {e}")
                self.error_occurred.emit(f"LLM处理失败: {e}")
            finally:
                self._processing_future = None
    
    def _on_llm_processing_complete(self, llm_data: Dict[str, Any]):
        """LLM处理完成回调"""
        try:
            timestamp = self._current_timestamp
            screenshot_path = self._current_screenshot_path
            start_time = self._current_start_time
            
            # 3. 组装游戏数据
            game_data = {
                'timestamp': timestamp,
                'screenshot_path': screenshot_path,
                'processing_method': 'llm',
                **llm_data
            }
            
            # 检查是否有有效数据 - 更新检查条件以包含新字段
            has_valid_data = any([
                game_data.get('level') is not None,
                game_data.get('experience') is not None,
                game_data.get('max_hp') is not None,
                game_data.get('max_mp') is not None,
                game_data.get('character_name') is not None,
                game_data.get('character_class') is not None,
                game_data.get('map_name') is not None,
                game_data.get('money') is not None
            ])
            
            if not has_valid_data:
                performance_logger.warning("未提取到有效的游戏数据，不保存到数据库")
                self.error_occurred.emit("未识别到有效的游戏数据")
                return
            
            # 缓存结果
            self._last_result = game_data.copy()
            
            # 4. 保存结果
            result_path = self._save_result(game_data, timestamp)
            
            # 保存到数据库（只有在有有效数据时）
            try:
                game_db.insert_game_data(game_data)
                performance_logger.info("游戏数据已保存到数据库")
            except Exception as e:
                performance_logger.error(f"保存数据到数据库失败: {e}")
            
            # 5. 发送数据信号给UI更新
            self.data_extracted.emit(game_data)
            
            total_time = time.time() - start_time
            performance_logger.info(f"单次LLM处理完成: {timestamp}, 总耗时: {total_time:.2f}秒")
            performance_logger.info(f"处理结果已保存: {result_path}")
            performance_logger.info(f"识别数据: 等级={game_data.get('level')}, 角色名={game_data.get('character_name')}, 职业={game_data.get('character_class')}, 地图={game_data.get('map_name')}, 经验={game_data.get('experience')}, HP={game_data.get('max_hp')}, MP={game_data.get('max_mp')}, 金钱={game_data.get('money')}")
            
        except Exception as e:
            error_msg = f"LLM处理完成回调出错: {e}"
            performance_logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    def _capture_screenshot(self) -> Optional[Image.Image]:
        """执行截图操作"""
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
            else:
                # 全屏截图
                screenshot = ImageGrab.grab(all_screens=True)
            
            return screenshot
            
        except Exception as e:
            performance_logger.error(f"截图失败: {e}")
            return None 