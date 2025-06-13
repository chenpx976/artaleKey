import os
import base64
import yaml
import re
import json
import requests
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image
from io import BytesIO
from artalekey.core.logger import performance_logger
from artalekey.core.config import config_manager
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class LLMProcessor:
    """LLM 图片处理器 - 使用并发请求处理分割后的图片区域"""
    
    # 类级别的线程池，增加并发数量
    _thread_pool = None
    _thread_pool_lock = threading.RLock()
    
    def __init__(self):
        self.api_key = None
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self._setup_client()
        
        # 确保线程池初始化
        self._ensure_thread_pool()
        
        # 不同区域的专用提示词
        self.prompts = {
            'map': """你是一个冒险岛游戏的高级玩家，游戏语言选择了繁体中文。请分析这个地图区域截图，提取地图信息。

请返回以下JSON结构：
{
  "map_name": "当前地图名称" (字符串, 繁体中文, 格式: 大地图-小地图)
}

注意事项：
- 仔细观察截图中的地图名称显示
- 如果信息不可见或无法确定，请设置为null
- 请确保输出为有效的JSON格式""",

            'character': """你是一个冒险岛游戏的高级玩家，游戏语言选择了繁体中文。请分析这个角色信息区域截图，提取角色相关信息。

请返回以下JSON结构：
{
  "level": 角色等级 (数字),
  "character_name": "角色名称" (字符串),
  "character_class": "角色职业" (字符串, 繁体中文, 格式: 弩弓手、法师等)
}

注意事项：
- 仔细观察截图中的角色信息显示
- 如果某个信息不可见或无法确定，请设置为null
- 数字字段请只输出纯数字，不包含逗号、单位等
- 请确保输出为有效的JSON格式""",

            'stats': """你是一个冒险岛游戏的高级玩家，游戏语言选择了繁体中文。请分析这个HP/MP/经验值区域截图，提取数值信息。

请返回以下JSON结构：
{
  "max_hp": 当前等级最大HP (数字),
  "max_mp": 当前等级最大MP (数字),
  "experience_value": 当前经验值 (数字),
  "experience_percentage": 当前经验值百分比 (数字，不含%符号)
}

注意事项：
- 仔细观察截图中的HP、MP和经验值显示
- 如果某个信息不可见或无法确定，请设置为null
- 数字字段请只输出纯数字，不包含逗号、单位等
- 百分比字段请只输出数字部分，如65.5而不是65.5%
- 请确保输出为有效的JSON格式""",

            'potions': """你是一个冒险岛游戏的高级玩家，游戏语言选择了繁体中文。请分析这个药水存量区域截图，提取药水数量信息。

请返回以下JSON结构：
{
  "hp_potion_count": HP药水数量 (数字), 这个数字在快捷键区域中，位于标有 "Ins" 的按键上，通常显示为一个数字,
  "mp_potion_count": MP药水数量 (数字), 这个数字在快捷键区域中，位于标有 "Hm" 的按键上，通常显示为一个数字
}

注意事项：
- 仔细观察截图中的快捷键面板和药水数量显示
- 如果某个信息不可见或无法确定，请设置为null
- 数字字段请只输出纯数字，不包含逗号、单位等
- 请确保输出为有效的JSON格式""",

            'money': """你是一个冒险岛游戏的高级玩家，游戏语言选择了繁体中文。请分析这个截图，寻找金钱信息。

请返回以下JSON结构：
{
  "money": 角色当前持有金钱 (数字), 这个数字是在 "金幣" 的左边展示的
}

注意事项：
- 仔细观察截图中的金钱显示，通常在"金幣"字样附近
- 如果信息不可见或无法确定，请设置为null
- 数字字段请只输出纯数字，不包含逗号、单位等
- 请确保输出为有效的JSON格式"""
        }
    
    @classmethod
    def _ensure_thread_pool(cls):
        """确保线程池已初始化，增加并发数量"""
        if cls._thread_pool is None:
            with cls._thread_pool_lock:
                if cls._thread_pool is None:
                    # 增加线程池大小以支持并发请求
                    cls._thread_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="LLM-")
                    performance_logger.info("LLM 处理器线程池已初始化 (6个工作线程)")
    
    @classmethod
    def _cleanup_thread_pool(cls):
        """清理线程池（应用关闭时调用）"""
        if cls._thread_pool is not None:
            with cls._thread_pool_lock:
                if cls._thread_pool is not None:
                    cls._thread_pool.shutdown(wait=False)
                    cls._thread_pool = None
                    performance_logger.info("LLM 处理器线程池已清理")
    
    def _setup_client(self):
        """设置API密钥"""
        try:
            # 从配置文件获取 API 密钥
            api_key = config_manager.get('llm', 'api_key')
            
            performance_logger.info(f"LLM API密钥初始化 - 密钥状态: {'已设置' if api_key else '未设置'}")
            
            if not api_key:
                performance_logger.warning("API 密钥为空，LLM 处理器初始化跳过")
                self.api_key = None
                return
            
            # 验证密钥格式
            if len(api_key) < 10:
                performance_logger.error(f"API 密钥格式可能不正确，长度: {len(api_key)}")
                self.api_key = None
                return
            
            self.api_key = api_key
            performance_logger.info(f"LLM API密钥设置成功，密钥长度: {len(api_key)}")
            
        except Exception as e:
            performance_logger.error(f"LLM API密钥设置失败: {e}")
            self.api_key = None
    
    def update_api_key(self, api_key: str):
        """更新 API 密钥"""
        try:
            performance_logger.info(f"更新 API 密钥 - 新密钥长度: {len(api_key) if api_key else 0}")
            
            # 更新配置
            config_manager.set('llm', 'api_key', api_key)
            
            # 重新设置密钥
            self.api_key = api_key if api_key and len(api_key) >= 10 else None
            
            # 验证设置是否成功
            if self.api_key:
                performance_logger.info("API 密钥更新成功")
            else:
                performance_logger.error("API 密钥更新后验证失败")
            
        except Exception as e:
            performance_logger.error(f"更新 API 密钥失败: {e}")
            self.api_key = None
    
    def _split_image(self, image: Image.Image) -> Dict[str, Image.Image]:
        """将图片分割为不同的区域"""
        try:
            width, height = image.size
            performance_logger.info(f"开始分割图片，原始尺寸: {width}x{height}")
            
            # 计算各个区域的坐标
            quarter_width = width // 4
            quarter_height = height // 4
            # 新增：0.15比例的高度
            bottom_015_height = int(height * 0.15)
            
            regions = {}
            
            # 地图区域: 图片上面四分之一的左边四分之一
            regions['map'] = image.crop((0, 0, quarter_width, quarter_height))
            
            # 角色信息区域: 图片下面 0.15 的左边四分之一
            regions['character'] = image.crop((0, height - bottom_015_height, quarter_width, height))
            
            # HP/MP/经验值: 图片下面 0.15 的中间 2/4
            regions['stats'] = image.crop((quarter_width, height - bottom_015_height, quarter_width * 3, height))
            
            # 药水存量数据: 图片下面四分之一的右边四分之一 (保持原来的比例)
            regions['potions'] = image.crop((quarter_width * 3, height - quarter_height, width, height))
            
            # 金钱: 除去上面的区域之后的图片 (中间区域，需要调整以避免与新的0.15区域重叠)
            regions['money'] = image.crop((0, quarter_height, width, height - quarter_height))
            
            performance_logger.info(f"图片分割完成，共分割出 {len(regions)} 个区域")
            performance_logger.info(f"新的分割比例 - 角色信息和HP/MP/经验值区域使用底部0.15比例 ({bottom_015_height}px)")
            
            # 记录每个区域的尺寸
            for region_name, region_image in regions.items():
                performance_logger.info(f"区域 {region_name}: {region_image.size}")
            
            return regions
            
        except Exception as e:
            performance_logger.error(f"图片分割失败: {e}")
            return {}
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """将图片转换为 base64 编码"""
        try:
            # 转换为 RGB 模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 对小区域图片进行适当压缩
            max_size = (800, 600)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                performance_logger.debug(f"区域图片已压缩到: {image.size}")
            
            # 转换为 base64
            buffer = BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return image_base64
            
        except Exception as e:
            performance_logger.error(f"图片转换为 base64 失败: {e}")
            return ""
    
    def _make_llm_request(self, region_name: str, image: Image.Image) -> Dict[str, Any]:
        """对单个区域进行 LLM 请求"""
        try:
            performance_logger.info(f"开始处理区域: {region_name}")
            
            # 转换图片为 base64
            image_base64 = self._image_to_base64(image)
            if not image_base64:
                return {}
            
            # 获取对应的提示词
            prompt = self.prompts.get(region_name, self.prompts['money'])
            
            # 构建请求数据
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://artalekey.app",
                "X-Title": "ArtaleKey",
            }
            
            data = {
                "model": "qwen/qwen2.5-vl-72b-instruct:free",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                        ]
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.1
            }
            
            # 发送请求
            performance_logger.info(f"发送 {region_name} 区域请求到 OpenRouter API...")
            response = requests.post(
                self.base_url,
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
            
            # 检查响应状态
            if response.status_code != 200:
                performance_logger.error(f"{region_name} 区域 API 请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return {}
            
            # 解析响应
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                performance_logger.error(f"{region_name} 区域 API 响应格式错误: {response_data}")
                return {}
            
            response_text = response_data['choices'][0]['message']['content']
            performance_logger.info(f"{region_name} 区域 LLM 原始响应: {response_text}")
            
            # 解析响应
            parsed_data = self._parse_llm_response(response_text)
            performance_logger.info(f"{region_name} 区域处理完成，提取数据: {parsed_data}")
            
            return parsed_data
            
        except requests.exceptions.Timeout:
            performance_logger.error(f"{region_name} 区域 LLM API 请求超时")
            return {}
        except requests.exceptions.RequestException as e:
            performance_logger.error(f"{region_name} 区域 LLM API 请求异常: {e}")
            return {}
        except Exception as e:
            performance_logger.error(f"{region_name} 区域 LLM 处理失败: {e}")
            return {}
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 格式数据"""
        try:
            # 提取JSON内容
            json_content = None
            
            # 尝试多种提取方法
            patterns = [
                r'```json\s*(.*?)\s*```',
                r'```\s*(\{.*?\})\s*```',
                r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
                if match:
                    json_content = match.group(1).strip()
                    break
            
            # 如果没有找到，尝试直接解析整个响应
            if not json_content:
                json_content = response_text.strip()
            
            performance_logger.debug(f"提取的 JSON 内容: {json_content}")
            
            # 解析 JSON
            parsed_data = json.loads(json_content)
            
            if not isinstance(parsed_data, dict):
                performance_logger.error(f"解析的数据不是字典格式: {type(parsed_data)}")
                return {}
            
            # 数据清理和验证
            cleaned_data = {}
            
            # 定义字段类型
            field_types = {
                'level': int,
                'character_name': str,
                'character_class': str,
                'map_name': str,
                'max_hp': int,
                'max_mp': int,
                'experience_value': int,
                'experience_percentage': float,
                'money': int,
                'hp_potion_count': int,
                'mp_potion_count': int
            }
            
            for field, expected_type in field_types.items():
                if field in parsed_data:
                    value = parsed_data[field]
                    if value is not None:
                        try:
                            if expected_type in [int, float]:
                                # 清理数字字段
                                if isinstance(value, str):
                                    cleaned_value = re.sub(r'[^\d.]', '', value)
                                    if cleaned_value:
                                        cleaned_data[field] = expected_type(float(cleaned_value))
                                    else:
                                        cleaned_data[field] = None
                                else:
                                    cleaned_data[field] = expected_type(value)
                            else:
                                # 字符串字段
                                cleaned_data[field] = str(value).strip()
                        except (ValueError, TypeError) as e:
                            performance_logger.warning(f"字段 {field} 转换失败: {e}, 原值: {value}")
                            cleaned_data[field] = None
                    else:
                        cleaned_data[field] = None
            
            return cleaned_data
            
        except json.JSONDecodeError as e:
            performance_logger.error(f"JSON 解析失败: {e}")
            return {}
        except Exception as e:
            performance_logger.error(f"解析 LLM 响应失败: {e}")
            return {}
    
    def process_image(self, image: Image.Image) -> Dict[str, Any]:
        """并发处理图片并提取游戏数据"""
        if not self.api_key:
            performance_logger.error("API 密钥未设置，请检查配置")
            return {}
        
        try:
            performance_logger.info("开始并发 LLM 图片处理...")
            
            # 分割图片
            regions = self._split_image(image)
            if not regions:
                performance_logger.error("图片分割失败")
                return {}
            
            # 并发处理所有区域
            self._ensure_thread_pool()
            futures = {}
            
            for region_name, region_image in regions.items():
                future = self._thread_pool.submit(self._make_llm_request, region_name, region_image)
                futures[future] = region_name
            
            # 收集所有结果
            all_results = {}
            completed_count = 0
            
            for future in as_completed(futures, timeout=60):
                region_name = futures[future]
                try:
                    result = future.result()
                    all_results.update(result)
                    completed_count += 1
                    performance_logger.info(f"区域 {region_name} 处理完成 ({completed_count}/{len(regions)})")
                except Exception as e:
                    performance_logger.error(f"区域 {region_name} 处理异常: {e}")
            
            # 转换为符合现有系统的格式
            game_data = self._convert_to_game_format(all_results)
            
            performance_logger.info(f"并发 LLM 处理完成，最终数据: {game_data}")
            return game_data
            
        except Exception as e:
            performance_logger.error(f"并发 LLM 图片处理失败: {e}")
            return {}
    
    def process_image_async(self, image: Image.Image, callback=None):
        """异步处理图片并提取游戏数据"""
        def run_process():
            try:
                performance_logger.info("开始异步并发 LLM 处理任务")
                result = self.process_image(image)
                performance_logger.info("异步并发 LLM 处理任务完成")
                if callback:
                    callback(result)
                return result
            except Exception as e:
                performance_logger.error(f"异步并发 LLM 处理失败: {e}")
                if callback:
                    callback({})
                return {}
        
        # 使用类级别的线程池
        self._ensure_thread_pool()
        future = self._thread_pool.submit(run_process)
        performance_logger.info("并发 LLM 处理任务已提交到线程池")
        return future
    
    def _convert_to_game_format(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """将解析的数据转换为符合现有系统的格式"""
        game_data = {}
        
        # 等级
        if 'level' in parsed_data:
            game_data['level'] = parsed_data['level']
        
        # 角色信息
        if 'character_name' in parsed_data:
            game_data['character_name'] = parsed_data['character_name']
        
        if 'character_class' in parsed_data:
            game_data['character_class'] = parsed_data['character_class']
        
        # 地图信息
        if 'map_name' in parsed_data:
            game_data['map_name'] = parsed_data['map_name']
        
        # 经验值
        exp_value = parsed_data.get('experience_value')
        exp_percentage = parsed_data.get('experience_percentage')
        
        if exp_value is not None or exp_percentage is not None:
            game_data['experience'] = {}
            if exp_value is not None:
                game_data['experience']['value'] = exp_value
            if exp_percentage is not None:
                game_data['experience']['percentage'] = exp_percentage
        
        # HP 和 MP
        if 'max_hp' in parsed_data:
            game_data['max_hp'] = parsed_data['max_hp']
        
        if 'max_mp' in parsed_data:
            game_data['max_mp'] = parsed_data['max_mp']
        
        # 金钱
        if 'money' in parsed_data:
            game_data['money'] = parsed_data['money']
        
        # 药水数量
        if 'hp_potion_count' in parsed_data:
            game_data['hp_potion_count'] = parsed_data['hp_potion_count']
        
        if 'mp_potion_count' in parsed_data:
            game_data['mp_potion_count'] = parsed_data['mp_potion_count']
        
        # 添加处理方式标识
        game_data['processing_method'] = 'concurrent_llm'
        game_data['llm_model'] = 'qwen/qwen2.5-vl-72b-instruct:free'
        
        return game_data 