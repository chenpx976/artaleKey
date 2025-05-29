import os
import base64
import yaml
import re
from typing import Optional, Dict, Any
from openai import OpenAI
from PIL import Image
from io import BytesIO
from artalekey.core.logger import performance_logger
from artalekey.core.config import config_manager

class LLMProcessor:
    """LLM 图片处理器 - 使用大模型识别游戏界面信息"""
    
    def __init__(self):
        self.client = None
        self._setup_client()
        
        # LLM 提示词
        self.prompt = """提取图片中的下面相关信息，输出在 <output/> 中，使用 yaml 格式
等级
当前等级最大 HP
当前等级最大 MP
当前经验值
当前经验值百分比"""
    
    def _setup_client(self):
        """设置 OpenAI 客户端"""
        try:
            # 从配置文件获取 API 密钥
            llm_config = config_manager.get('llm', {})
            api_key = llm_config.get('api_key', '')
            
            if not api_key:
                performance_logger.error("未设置 OPENROUTER_API_KEY，请在设置页面配置")
                return
            
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            
            performance_logger.info("LLM 客户端初始化成功")
            
        except Exception as e:
            performance_logger.error(f"LLM 客户端初始化失败: {e}")
    
    def update_api_key(self, api_key: str):
        """更新 API 密钥并重新初始化客户端"""
        try:
            # 更新配置
            llm_config = config_manager.get('llm', {})
            llm_config['api_key'] = api_key
            config_manager.set('llm', llm_config)
            
            # 重新初始化客户端
            self._setup_client()
            
            performance_logger.info("API 密钥已更新")
            
        except Exception as e:
            performance_logger.error(f"更新 API 密钥失败: {e}")
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """将图片转换为 base64 编码"""
        try:
            # 转换为 RGB 模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 压缩图片以减少 API 调用成本
            max_size = (1024, 1024)
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
        """解析 LLM 返回的 YAML 格式数据"""
        try:
            # 提取 <output/> 标签中的内容
            output_match = re.search(r'<output/?>\s*(.*?)\s*</output>', response_text, re.DOTALL | re.IGNORECASE)
            if output_match:
                yaml_content = output_match.group(1).strip()
            else:
                # 如果没有找到标签，尝试查找 YAML 格式的内容
                yaml_patterns = [
                    r'```yaml\s*(.*?)\s*```',
                    r'```\s*((?:等级|level).*?)\s*```',
                ]
                
                for pattern in yaml_patterns:
                    match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        yaml_content = match.group(1).strip()
                        break
                else:
                    # 最后尝试直接解析整个响应
                    yaml_content = response_text.strip()
            
            performance_logger.info(f"提取的 YAML 内容: {yaml_content}")
            
            # 解析 YAML
            parsed_data = yaml.safe_load(yaml_content)
            
            if not isinstance(parsed_data, dict):
                performance_logger.error(f"解析的数据不是字典格式: {type(parsed_data)}")
                return {}
            
            # 标准化字段名
            standardized_data = {}
            
            # 映射可能的字段名
            field_mappings = {
                'level': ['等级', 'level', 'lv', 'Level'],
                'max_hp': ['当前等级最大 HP', '最大HP', 'max_hp', 'hp', '最大血量', 'HP', '生命值'],
                'max_mp': ['当前等级最大 MP', '最大MP', 'max_mp', 'mp', '最大魔法值', 'MP', '魔法值'],
                'experience_value': ['当前经验值', '经验值', 'exp', 'experience', '经验', 'EXP'],
                'experience_percentage': ['当前经验值百分比', '经验百分比', 'exp_percent', '经验值百分比', '经验进度']
            }
            
            for standard_key, possible_keys in field_mappings.items():
                for key in possible_keys:
                    if key in parsed_data:
                        value = parsed_data[key]
                        # 清理数值
                        if isinstance(value, str):
                            # 移除非数字字符（除了小数点）
                            cleaned_value = re.sub(r'[^\d.]', '', value)
                            if cleaned_value:
                                try:
                                    if '.' in cleaned_value:
                                        standardized_data[standard_key] = float(cleaned_value)
                                    else:
                                        standardized_data[standard_key] = int(cleaned_value)
                                except ValueError:
                                    standardized_data[standard_key] = value
                            else:
                                standardized_data[standard_key] = value
                        else:
                            standardized_data[standard_key] = value
                        break
            
            performance_logger.info(f"标准化后的数据: {standardized_data}")
            return standardized_data
            
        except yaml.YAMLError as e:
            performance_logger.error(f"YAML 解析失败: {e}")
            return {}
        except Exception as e:
            performance_logger.error(f"解析 LLM 响应失败: {e}")
            return {}
    
    def process_image(self, image: Image.Image) -> Dict[str, Any]:
        """处理图片并提取游戏数据"""
        if not self.client:
            performance_logger.error("LLM 客户端未初始化，请检查 API 密钥配置")
            return {}
        
        try:
            performance_logger.info("开始 LLM 图片处理...")
            
            # 转换图片为 base64
            image_base64 = self._image_to_base64(image)
            if not image_base64:
                return {}
            
            # 构建消息
            messages = [
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
                        }
                    ]
                }
            ]
            
            # 调用 LLM API - 使用新的参数格式
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://artalekey.app",
                    "X-Title": "ArtaleKey",
                },
                extra_body={},
                model="qwen/qwen2.5-vl-72b-instruct:free",
                messages=messages,
                max_tokens=1000,
                temperature=0.1  # 降低随机性，提高一致性
            )
            
            response_text = completion.choices[0].message.content
            performance_logger.info(f"LLM 原始响应: {response_text}")
            
            # 解析响应
            parsed_data = self._parse_llm_response(response_text)
            
            # 转换为符合现有系统的格式
            game_data = self._convert_to_game_format(parsed_data)
            
            performance_logger.info(f"LLM 处理完成，提取数据: {game_data}")
            return game_data
            
        except Exception as e:
            performance_logger.error(f"LLM 图片处理失败: {e}")
            return {}
    
    def _convert_to_game_format(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """将解析的数据转换为符合现有系统的格式"""
        game_data = {}
        
        # 等级
        if 'level' in parsed_data:
            game_data['level'] = parsed_data['level']
        
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
        
        # 添加处理方式标识
        game_data['processing_method'] = 'llm'
        game_data['llm_model'] = 'qwen/qwen2.5-vl-72b-instruct:free'
        
        return game_data 