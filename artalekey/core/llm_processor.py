import os
import base64
import yaml
import re
import json
import requests
from typing import Optional, Dict, Any
from PIL import Image
from io import BytesIO
from artalekey.core.logger import performance_logger
from artalekey.core.config import config_manager
from artalekey.core.llm_image_data import hp_mp_potion_image_base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

class LLMProcessor:
    """LLM 图片处理器 - 使用requests直接调用OpenRouter API"""
    
    # 类级别的线程池，避免重复创建
    _thread_pool = None
    _thread_pool_lock = threading.RLock()
    
    def __init__(self):
        self.api_key = None
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self._setup_client()
        
        # 确保线程池初始化
        self._ensure_thread_pool()
        
        # LLM 提示词
        self.prompt = """你是一个冒险岛游戏的高级玩家, 游戏语言选择了繁体中文，可以根据我发送给你的截图，分析获取到下面的信息，输出为标准JSON格式：

请返回以下JSON结构，严格按照字段名输出：
{
  "level": 角色等级 (数字),
  "character_name": "角色名称" (字符串),
  "character_class": "角色职业" (字符串, 繁体中文, 格式: 弩弓手、法师等),
  "map_name": "当前地图名称" (字符串, 繁体中文, 格式: 大地图-小地图),
  "max_hp": 当前等级最大HP (数字),
  "max_mp": 当前等级最大MP (数字),
  "experience_value": 当前经验值 (数字),
  "experience_percentage": 当前经验值百分比 (数字，不含%符号),
  "money": 角色当前持有金钱 (数字), 这个数字是在 "金幣" 的左边展示的, 你找不到就返回 null,
  "hp_potion_count": HP药水数量 (数字), 这个数字在游戏界面右下角快捷键区域中，位于标有 "Ins" 的按键上，通常显示为一个数字，你找不到就返回 null,
  "mp_potion_count": MP药水数量 (数字), 这个数字在游戏界面右下角快捷键区域中，位于标有 "Hm" 的按键上，通常显示为一个数字，你找不到就返回 null
}

注意事项：
- 仔细观察截图中的所有界面元素，特别是右下角的快捷键面板
- 如果某个信息不可见或无法确定，请设置为null
- 数字字段请只输出纯数字，不包含逗号、单位等
- 百分比字段请只输出数字部分，如65.5而不是65.5%
- 请确保输出为有效的JSON格式

"""
    
    @classmethod
    def _ensure_thread_pool(cls):
        """确保线程池已初始化"""
        if cls._thread_pool is None:
            with cls._thread_pool_lock:
                if cls._thread_pool is None:
                    cls._thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="LLM-")
                    performance_logger.info("LLM 处理器线程池已初始化")
    
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
            llm_config = config_manager.get('llm', {})
            api_key = llm_config.get('api_key', '')
            
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
            llm_config = config_manager.get('llm', {})
            llm_config['api_key'] = api_key
            config_manager.set('llm', llm_config)
            
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
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """将图片转换为 base64 编码"""
        try:
            # 转换为 RGB 模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 压缩图片以减少 API 调用成本
            max_size = (1920, 1080)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                performance_logger.info(f"图片已压缩到: {image.size}")
            
            # 转换为 base64
            buffer = BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return image_base64
            
        except Exception as e:
            performance_logger.error(f"图片转换为 base64 失败: {e}")
            return ""
    
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
            
            performance_logger.info(f"提取的 JSON 内容: {json_content}")
            
            # 解析 JSON
            parsed_data = json.loads(json_content)
            
            if not isinstance(parsed_data, dict):
                performance_logger.error(f"解析的数据不是字典格式: {type(parsed_data)}")
                return {}
            
            # 数据清理和验证
            cleaned_data = {}
            
            # 直接使用字段名，无需映射
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
            
            performance_logger.info(f"清理后的数据: {cleaned_data}")
            return cleaned_data
            
        except json.JSONDecodeError as e:
            performance_logger.error(f"JSON 解析失败: {e}")
            return {}
        except Exception as e:
            performance_logger.error(f"解析 LLM 响应失败: {e}")
            return {}
    
    def process_image(self, image: Image.Image) -> Dict[str, Any]:
        """处理图片并提取游戏数据"""
        if not self.api_key:
            performance_logger.error("API 密钥未设置，请检查配置")
            return {}
        
        try:
            performance_logger.info("开始 LLM 图片处理...")
            
            # 转换图片为 base64
            image_base64 = self._image_to_base64(image)
            if not image_base64:
                return {}
            
            # 构建请求数据
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://artalekey.app",
                "X-Title": "ArtaleKey",
            }
            
            data = {
                "model": "qwen/qwen2.5-vl-72b-instruct:free",
                # "model": "google/gemini-2.0-flash-exp:free",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self.prompt
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
                "max_tokens": 1000,
                "temperature": 0.1
            }
            
            # 发送请求
            performance_logger.info("发送请求到 OpenRouter API...")
            response = requests.post(
                self.base_url,
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
            
            # 检查响应状态
            if response.status_code != 200:
                performance_logger.error(f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return {}
            
            # 解析响应
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                performance_logger.error(f"API 响应格式错误: {response_data}")
                return {}
            
            response_text = response_data['choices'][0]['message']['content']
            performance_logger.info(f"LLM 原始响应: {response_text}")
            
            # 解析响应
            parsed_data = self._parse_llm_response(response_text)
            
            # 转换为符合现有系统的格式
            game_data = self._convert_to_game_format(parsed_data)
            
            performance_logger.info(f"LLM 处理完成，提取数据: {game_data}")
            return game_data
            
        except requests.exceptions.Timeout:
            performance_logger.error("LLM API 请求超时")
            return {}
        except requests.exceptions.RequestException as e:
            performance_logger.error(f"LLM API 请求异常: {e}")
            return {}
        except Exception as e:
            performance_logger.error(f"LLM 图片处理失败: {e}")
            return {}
    
    def process_image_async(self, image: Image.Image, callback=None):
        """异步处理图片并提取游戏数据 - 优化的非阻塞版本"""
        def run_process():
            try:
                performance_logger.info("开始异步 LLM 处理任务")
                result = self.process_image(image)
                performance_logger.info("异步 LLM 处理任务完成")
                if callback:
                    # 注意：callback 将在线程池线程中执行，需要确保线程安全
                    callback(result)
                return result
            except Exception as e:
                performance_logger.error(f"异步 LLM 处理失败: {e}")
                if callback:
                    callback({})
                return {}
        
        # 使用类级别的线程池，避免创建新的线程池
        self._ensure_thread_pool()
        future = self._thread_pool.submit(run_process)
        performance_logger.info("LLM 处理任务已提交到线程池")
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
        game_data['processing_method'] = 'llm'
        game_data['llm_model'] = 'qwen/qwen2.5-vl-72b-instruct:free'
        
        return game_data 