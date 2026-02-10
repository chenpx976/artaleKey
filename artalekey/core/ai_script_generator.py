"""
AI Script Generator Module

Uses LLM to generate automation scripts from natural language descriptions.
"""

import json
import requests
from typing import Tuple, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from artalekey.core.script_parser import ScriptParser
from artalekey.core.config import config_manager
from artalekey.core.logger import performance_logger


class AIScriptGenerator(QThread):
    """AI-powered script generator using LLM"""

    # Signals
    generation_started = pyqtSignal()
    generation_completed = pyqtSignal(str)  # Generated YAML content
    generation_failed = pyqtSignal(str)  # Error message
    generation_progress = pyqtSignal(str)  # Progress message

    # System prompt for LLM
    SYSTEM_PROMPT = """You are an expert at creating YAML automation scripts for a game automation tool called ArtaleKey.

Your task is to convert natural language descriptions into valid YAML scripts following this exact format:

## YAML Script Format:

```yaml
name: "Script Name"
description: "Brief description"
version: "1.0"
author: "User"

execution:
  mode: "continuous"  # Options: duration, iterations, continuous
  duration: 60        # Only for duration mode (seconds)
  iterations: 10      # Only for iterations mode

window:
  auto_activate: true
  pause_on_focus_loss: true
  target_window: "MapleStory Worlds"

operations:
  - type: "press"
    key: "a"

  - type: "long_press"
    key: "s"
    duration: 500  # milliseconds

  - type: "hold"
    key: "shift"

  - type: "release"
    key: "shift"

  - type: "delay"
    duration: 1000  # milliseconds

  - type: "repeat"
    count: 3
    operations:
      - type: "press"
        key: "q"
      - type: "delay"
        duration: 200

  - type: "combo"
    keys: ["ctrl", "a"]
    duration: 100  # milliseconds
```

## Supported Keys:
- Letters: a-z
- Numbers: 0-9
- Arrows: up, down, left, right
- Special: space, enter, tab, esc, backspace
- Modifiers: shift, ctrl, alt, cmd
- Function: f1-f12

## Execution Modes:
1. **continuous**: Run forever until stopped
2. **duration**: Run for specified seconds
3. **iterations**: Run for specified number of times

## Operation Types:
1. **press**: Single key tap
2. **long_press**: Hold key for duration (milliseconds)
3. **hold**: Press and keep pressed
4. **release**: Release a held key
5. **delay**: Wait/pause (milliseconds)
6. **repeat**: Repeat a sequence of operations
7. **combo**: Press multiple keys simultaneously

## Important Rules:
1. ONLY output valid YAML, no explanations or markdown code blocks
2. Use proper YAML indentation (2 spaces)
3. All durations are in milliseconds
4. Keys must be lowercase
5. Always include name, execution mode, and operations
6. For continuous mode, omit duration and iterations
7. For duration mode, include duration in seconds
8. For iterations mode, include iterations count

## Examples:

Example 1 - Simple Attack Rotation:
```yaml
name: "Basic Attack"
description: "Two-skill rotation"
version: "1.0"
author: "User"

execution:
  mode: "continuous"

window:
  auto_activate: true
  pause_on_focus_loss: true
  target_window: "MapleStory Worlds"

operations:
  - type: "press"
    key: "a"
  - type: "delay"
    duration: 800
  - type: "press"
    key: "s"
  - type: "delay"
    duration: 800
```

Example 2 - Buff Rotation:
```yaml
name: "Buff Rotation"
description: "Apply buffs every 30 seconds"
version: "1.0"
author: "User"

execution:
  mode: "duration"
  duration: 300

window:
  auto_activate: true
  pause_on_focus_loss: true
  target_window: "MapleStory Worlds"

operations:
  - type: "press"
    key: "f1"
  - type: "delay"
    duration: 500
  - type: "press"
    key: "f2"
  - type: "delay"
    duration: 500
  - type: "delay"
    duration: 30000
```

Example 3 - Complex Combo:
```yaml
name: "Skill Combo"
description: "Multi-skill combo with repeat"
version: "1.0"
author: "User"

execution:
  mode: "iterations"
  iterations: 10

window:
  auto_activate: true
  pause_on_focus_loss: true
  target_window: "MapleStory Worlds"

operations:
  - type: "press"
    key: "f1"
  - type: "delay"
    duration: 500
  - type: "repeat"
    count: 3
    operations:
      - type: "long_press"
        key: "a"
        duration: 300
      - type: "delay"
        duration: 200
      - type: "press"
        key: "s"
      - type: "delay"
        duration: 500
  - type: "combo"
    keys: ["shift", "q"]
    duration: 100
  - type: "delay"
    duration: 2000
```

Now, convert the user's description into a valid YAML script. Output ONLY the YAML, nothing else."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parser = ScriptParser()
        self.user_prompt = ""
        self._api_key = ""
        self._api_base_url = "https://openrouter.ai/api/v1/chat/completions"
        self._model = "anthropic/claude-3.5-sonnet"

    def set_prompt(self, prompt: str):
        """Set the user prompt for generation"""
        self.user_prompt = prompt

    def run(self):
        """Generate script using LLM"""
        try:
            self.generation_started.emit()
            self.generation_progress.emit("正在连接 AI 服务...")

            # Get API key from config
            self._api_key = config_manager.get('llm', 'api_key')
            if not self._api_key:
                self.generation_failed.emit("未配置 API 密钥，请在设置中配置 OpenRouter API Key")
                return

            # Prepare API request
            self.generation_progress.emit("正在生成脚本...")

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/chenpx976/artaleKey",
                "X-Title": "ArtaleKey Script Generator"
            }

            payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"Create a script for: {self.user_prompt}"
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

            # Make API request
            response = requests.post(
                self._api_base_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                error_msg = f"API 请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f" - {error_data['error'].get('message', '')}"
                except:
                    pass
                self.generation_failed.emit(error_msg)
                return

            # Parse response
            result = response.json()
            if 'choices' not in result or len(result['choices']) == 0:
                self.generation_failed.emit("AI 返回了空响应")
                return

            generated_content = result['choices'][0]['message']['content'].strip()

            # Clean up the content (remove markdown code blocks if present)
            if generated_content.startswith('```yaml'):
                generated_content = generated_content[7:]
            elif generated_content.startswith('```'):
                generated_content = generated_content[3:]

            if generated_content.endswith('```'):
                generated_content = generated_content[:-3]

            generated_content = generated_content.strip()

            # Validate the generated script
            self.generation_progress.emit("正在验证生成的脚本...")

            try:
                script = self.parser.parse_yaml(generated_content)
                is_valid, errors = self.parser.validate_script(script)

                if not is_valid:
                    error_msg = "生成的脚本验证失败:\n" + "\n".join(errors)
                    self.generation_failed.emit(error_msg)
                    performance_logger.error(f"Generated script validation failed: {errors}")
                    return

                # Success!
                self.generation_progress.emit("脚本生成成功！")
                self.generation_completed.emit(generated_content)
                performance_logger.info(f"Successfully generated script: {script.name}")

            except Exception as e:
                self.generation_failed.emit(f"脚本解析失败: {str(e)}")
                performance_logger.error(f"Failed to parse generated script: {e}")
                return

        except requests.exceptions.Timeout:
            self.generation_failed.emit("请求超时，请检查网络连接")
        except requests.exceptions.RequestException as e:
            self.generation_failed.emit(f"网络请求失败: {str(e)}")
        except Exception as e:
            self.generation_failed.emit(f"生成失败: {str(e)}")
            performance_logger.error(f"Script generation error: {e}")


# Example prompts for users
EXAMPLE_PROMPTS = [
    {
        "name": "基础攻击循环",
        "prompt": "创建一个攻击脚本，按 A 键攻击，等待 800ms，按 S 键攻击，等待 800ms，循环执行"
    },
    {
        "name": "Buff 刷新",
        "prompt": "每 30 秒按一次 F1 和 F2 键来刷新 buff，持续 5 分钟"
    },
    {
        "name": "技能连招",
        "prompt": "按 F1 键开启 buff，然后重复 3 次：长按 A 键 300ms，等待 200ms，按 S 键，等待 500ms。最后按 Shift+Q 释放大招，等待 2 秒。重复 10 次"
    },
    {
        "name": "快速拾取",
        "prompt": "按 Z 键拾取物品，等待 100ms，重复 20 次"
    },
    {
        "name": "自动跳跃攻击",
        "prompt": "按空格键跳跃，等待 200ms，按 A 键攻击，等待 600ms，循环执行"
    },
    {
        "name": "组合技能",
        "prompt": "按 Q 键，等待 500ms，按 W 键，等待 500ms，按 E 键，等待 500ms，按 R 键，等待 2000ms，循环执行"
    },
    {
        "name": "长按移动",
        "prompt": "按住左方向键 2 秒，释放，等待 500ms，按住右方向键 2 秒，释放，等待 500ms，循环执行"
    },
    {
        "name": "快速施法",
        "prompt": "按 1 键，等待 50ms，按 2 键，等待 50ms，按 3 键，等待 50ms，按 4 键，等待 1000ms，重复 15 次"
    }
]
