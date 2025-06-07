"""
macOS 权限管理模块
用于检查和请求应用所需的系统权限
"""

import platform
import subprocess
from enum import Enum
from typing import Dict, Optional
import os

from artalekey.core.logger import performance_logger


class PermissionStatus(Enum):
    """权限状态枚举"""
    GRANTED = "granted"      # 已授予
    DENIED = "denied"        # 已拒绝
    NOT_DETERMINED = "not_determined"  # 未确定
    UNAVAILABLE = "unavailable"       # 不可用（非macOS系统）


class PermissionType(Enum):
    """权限类型枚举"""
    ACCESSIBILITY = "accessibility"        # 辅助功能
    INPUT_MONITORING = "input_monitoring"  # 输入监控
    SCREEN_CAPTURE = "screen_capture"      # 屏幕录制


class MacOSPermissionManager:
    """macOS 权限管理器"""
    
    def __init__(self):
        self.is_macos = platform.system() == "Darwin"
        self._permission_cache = {}
        
    def is_supported(self) -> bool:
        """检查是否支持权限管理（仅macOS）"""
        return self.is_macos
    
    def check_accessibility_permission(self) -> PermissionStatus:
        """检查辅助功能权限"""
        if not self.is_macos:
            return PermissionStatus.UNAVAILABLE
            
        try:
            # 使用 PyObjC 检查辅助功能权限
            try:
                from Cocoa import NSBundle
                from ApplicationServices import AXIsProcessTrusted
                
                # 检查是否已授予辅助功能权限
                if AXIsProcessTrusted():
                    performance_logger.info("辅助功能权限已授予")
                    return PermissionStatus.GRANTED
                else:
                    performance_logger.info("辅助功能权限未授予")
                    return PermissionStatus.DENIED
                    
            except ImportError:
                performance_logger.warning("PyObjC 未安装，无法检查辅助功能权限")
                # 备用方法：尝试使用 osascript 检查
                return self._check_accessibility_fallback()
                
        except Exception as e:
            performance_logger.error(f"检查辅助功能权限失败: {e}")
            return PermissionStatus.NOT_DETERMINED
    
    def _check_accessibility_fallback(self) -> PermissionStatus:
        """辅助功能权限检查的备用方法"""
        try:
            # 使用 AppleScript 检查辅助功能权限
            script = '''
            tell application "System Events"
                try
                    get name of first process
                    return "granted"
                on error
                    return "denied"
                end try
            end tell
            '''
            
            result = subprocess.run([
                'osascript', '-e', script
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                status = result.stdout.strip()
                if status == "granted":
                    return PermissionStatus.GRANTED
                else:
                    return PermissionStatus.DENIED
            else:
                return PermissionStatus.DENIED
                
        except Exception as e:
            performance_logger.error(f"备用辅助功能权限检查失败: {e}")
            return PermissionStatus.NOT_DETERMINED
    
    def check_input_monitoring_permission(self) -> PermissionStatus:
        """检查输入监控权限"""
        if not self.is_macos:
            return PermissionStatus.UNAVAILABLE
            
        try:
            # 对于输入监控权限，我们可以尝试创建一个事件监听器来测试
            try:
                from pynput import keyboard
                
                # 尝试创建一个全局键盘监听器
                def on_press(key):
                    pass
                
                # 创建监听器但不启动，只是测试是否可以创建
                listener = keyboard.Listener(on_press=on_press)
                
                # 如果能创建监听器，说明可能有权限
                # 但这不是100%准确的检查方法
                performance_logger.info("输入监控权限检查：可以创建监听器")
                return PermissionStatus.GRANTED
                
            except Exception as e:
                performance_logger.warning(f"输入监控权限检查失败: {e}")
                return PermissionStatus.DENIED
                
        except Exception as e:
            performance_logger.error(f"检查输入监控权限失败: {e}")
            return PermissionStatus.NOT_DETERMINED
    
    def check_screen_capture_permission(self) -> PermissionStatus:
        """检查屏幕录制权限"""
        if not self.is_macos:
            return PermissionStatus.UNAVAILABLE
            
        try:
            # 使用 PyObjC 检查屏幕录制权限
            try:
                from Quartz import CGPreflightScreenCaptureAccess, CGRequestScreenCaptureAccess
                
                # 检查屏幕录制权限
                if CGPreflightScreenCaptureAccess():
                    performance_logger.info("屏幕录制权限已授予")
                    return PermissionStatus.GRANTED
                else:
                    performance_logger.info("屏幕录制权限未授予")
                    return PermissionStatus.DENIED
                    
            except ImportError:
                performance_logger.warning("PyObjC 未安装，使用备用方法检查屏幕录制权限")
                return self._check_screen_capture_fallback()
                
        except Exception as e:
            performance_logger.error(f"检查屏幕录制权限失败: {e}")
            return PermissionStatus.NOT_DETERMINED
    
    def _check_screen_capture_fallback(self) -> PermissionStatus:
        """屏幕录制权限检查的备用方法"""
        try:
            # 尝试使用 screencapture 命令测试
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as tmp_file:
                result = subprocess.run([
                    'screencapture', '-x', '-t', 'png', '-R', '0,0,1,1', tmp_file.name
                ], capture_output=True, timeout=5)
                
                if result.returncode == 0:
                    performance_logger.info("屏幕录制权限检查：截图成功")
                    return PermissionStatus.GRANTED
                else:
                    performance_logger.info("屏幕录制权限检查：截图失败")
                    return PermissionStatus.DENIED
                    
        except Exception as e:
            performance_logger.error(f"备用屏幕录制权限检查失败: {e}")
            return PermissionStatus.NOT_DETERMINED
    
    def check_all_permissions(self) -> Dict[PermissionType, PermissionStatus]:
        """检查所有权限状态"""
        if not self.is_macos:
            return {
                PermissionType.ACCESSIBILITY: PermissionStatus.UNAVAILABLE,
                PermissionType.INPUT_MONITORING: PermissionStatus.UNAVAILABLE,
                PermissionType.SCREEN_CAPTURE: PermissionStatus.UNAVAILABLE,
            }
        
        permissions = {}
        
        try:
            permissions[PermissionType.ACCESSIBILITY] = self.check_accessibility_permission()
            permissions[PermissionType.INPUT_MONITORING] = self.check_input_monitoring_permission()
            permissions[PermissionType.SCREEN_CAPTURE] = self.check_screen_capture_permission()
            
            performance_logger.info(f"权限检查完成: {permissions}")
            
        except Exception as e:
            performance_logger.error(f"检查所有权限失败: {e}")
            # 返回默认状态
            for perm_type in PermissionType:
                if perm_type not in permissions:
                    permissions[perm_type] = PermissionStatus.NOT_DETERMINED
        
        return permissions
    
    def request_accessibility_permission(self) -> bool:
        """请求辅助功能权限"""
        if not self.is_macos:
            return False
            
        try:
            # 使用 PyObjC 请求辅助功能权限
            try:
                from Quartz import AXIsProcessTrustedWithOptions
                from Cocoa import kAXTrustedCheckOptionPrompt
                
                # 请求权限并显示提示
                options = {kAXTrustedCheckOptionPrompt.decode('utf-8'): True}
                result = AXIsProcessTrustedWithOptions(options)
                
                performance_logger.info(f"辅助功能权限请求结果: {result}")
                return result
                
            except ImportError:
                performance_logger.warning("PyObjC 未安装，使用备用方法请求辅助功能权限")
                return self._request_accessibility_fallback()
                
        except Exception as e:
            performance_logger.error(f"请求辅助功能权限失败: {e}")
            return False
    
    def _request_accessibility_fallback(self) -> bool:
        """辅助功能权限请求的备用方法"""
        try:
            # 打开系统偏好设置的辅助功能页面
            subprocess.run([
                'open', 
                'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'
            ], check=True)
            
            performance_logger.info("已打开辅助功能设置页面")
            return True
            
        except Exception as e:
            performance_logger.error(f"打开辅助功能设置失败: {e}")
            return False
    
    def request_screen_capture_permission(self) -> bool:
        """请求屏幕录制权限"""
        if not self.is_macos:
            return False
            
        try:
            # 使用 PyObjC 请求屏幕录制权限
            try:
                from Quartz import CGRequestScreenCaptureAccess
                
                # 请求屏幕录制权限
                result = CGRequestScreenCaptureAccess()
                performance_logger.info(f"屏幕录制权限请求结果: {result}")
                return result
                
            except ImportError:
                performance_logger.warning("PyObjC 未安装，使用备用方法请求屏幕录制权限")
                return self._request_screen_capture_fallback()
                
        except Exception as e:
            performance_logger.error(f"请求屏幕录制权限失败: {e}")
            return False
    
    def _request_screen_capture_fallback(self) -> bool:
        """屏幕录制权限请求的备用方法"""
        try:
            # 打开系统偏好设置的屏幕录制页面
            subprocess.run([
                'open', 
                'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'
            ], check=True)
            
            performance_logger.info("已打开屏幕录制设置页面")
            return True
            
        except Exception as e:
            performance_logger.error(f"打开屏幕录制设置失败: {e}")
            return False
    
    def open_input_monitoring_settings(self) -> bool:
        """打开输入监控设置页面"""
        if not self.is_macos:
            return False
            
        try:
            subprocess.run([
                'open', 
                'x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent'
            ], check=True)
            
            performance_logger.info("已打开输入监控设置页面")
            return True
            
        except Exception as e:
            performance_logger.error(f"打开输入监控设置失败: {e}")
            return False
    
    def open_privacy_settings(self) -> bool:
        """打开隐私设置总页面"""
        if not self.is_macos:
            return False
            
        try:
            subprocess.run([
                'open', 
                'x-apple.systempreferences:com.apple.preference.security?Privacy'
            ], check=True)
            
            performance_logger.info("已打开隐私设置页面")
            return True
            
        except Exception as e:
            performance_logger.error(f"打开隐私设置失败: {e}")
            return False


# 全局权限管理器实例
permission_manager = MacOSPermissionManager()


def get_permission_status_text(status: PermissionStatus) -> str:
    """获取权限状态的中文描述"""
    status_map = {
        PermissionStatus.GRANTED: "✅ 已授予",
        PermissionStatus.DENIED: "❌ 未授予", 
        PermissionStatus.NOT_DETERMINED: "❓ 未确定",
        PermissionStatus.UNAVAILABLE: "➖ 不适用"
    }
    return status_map.get(status, "❓ 未知")


def get_permission_name(perm_type: PermissionType) -> str:
    """获取权限类型的中文名称"""
    name_map = {
        PermissionType.ACCESSIBILITY: "辅助功能",
        PermissionType.INPUT_MONITORING: "输入监控",
        PermissionType.SCREEN_CAPTURE: "屏幕录制"
    }
    return name_map.get(perm_type, "未知权限")


def get_permission_description(perm_type: PermissionType) -> str:
    """获取权限的详细描述"""
    desc_map = {
        PermissionType.ACCESSIBILITY: "用于模拟按键操作和监听全局快捷键",
        PermissionType.INPUT_MONITORING: "用于检测全局快捷键组合",
        PermissionType.SCREEN_CAPTURE: "用于截图和OCR文字识别功能"
    }
    return desc_map.get(perm_type, "") 