#!/usr/bin/env python3
"""
安装Tesseract OCR的脚本
用于增强OCR识别能力，特别是橙色背景白色文字的识别
"""

import subprocess
import sys
import os
import platform

def run_command(command, description):
    """运行命令并处理错误"""
    print(f"正在{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description}成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def install_tesseract():
    """安装Tesseract OCR"""
    system = platform.system().lower()
    
    print(f"检测到操作系统: {system}")
    
    if system == "darwin":  # macOS
        print("在macOS上安装Tesseract...")
        
        # 检查是否已安装brew
        if not run_command("which brew", "检查Homebrew"):
            print("请先安装Homebrew: https://brew.sh/")
            return False
        
        # 安装tesseract
        if not run_command("brew install tesseract", "安装Tesseract"):
            print("如果已经安装，可以尝试更新:")
            run_command("brew upgrade tesseract", "更新Tesseract")
        
        # 安装中文语言包（如果需要）
        run_command("brew install tesseract-lang", "安装语言包")
        
    elif system == "linux":
        print("在Linux上安装Tesseract...")
        
        # Ubuntu/Debian
        if run_command("which apt-get", "检查apt-get"):
            run_command("sudo apt-get update", "更新包列表")
            run_command("sudo apt-get install -y tesseract-ocr", "安装Tesseract")
            run_command("sudo apt-get install -y libtesseract-dev", "安装开发包")
        
        # CentOS/RHEL
        elif run_command("which yum", "检查yum"):
            run_command("sudo yum install -y tesseract", "安装Tesseract")
        
        # Fedora
        elif run_command("which dnf", "检查dnf"):
            run_command("sudo dnf install -y tesseract", "安装Tesseract")
        
    elif system == "windows":
        print("在Windows上安装Tesseract...")
        print("请手动下载并安装Tesseract:")
        print("1. 访问: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. 下载Windows安装包")
        print("3. 安装后将tesseract.exe添加到PATH环境变量")
        return False
    
    else:
        print(f"不支持的操作系统: {system}")
        return False
    
    return True

def install_python_package():
    """安装Python的pytesseract包"""
    print("安装Python的pytesseract包...")
    
    # 尝试使用uv（如果可用）
    if run_command("which uv", "检查uv"):
        return run_command("uv pip install pytesseract", "使用uv安装pytesseract")
    
    # 回退到pip
    return run_command(f"{sys.executable} -m pip install pytesseract", "使用pip安装pytesseract")

def test_installation():
    """测试Tesseract安装"""
    print("测试Tesseract安装...")
    
    # 测试命令行版本
    if run_command("tesseract --version", "测试Tesseract命令行"):
        print("✅ Tesseract命令行工具安装成功")
    else:
        print("❌ Tesseract命令行工具未正确安装")
        return False
    
    # 测试Python包
    try:
        import pytesseract
        print("✅ pytesseract Python包导入成功")
        
        # 测试基本功能
        from PIL import Image
        import numpy as np
        
        # 创建一个简单的测试图像
        test_image = Image.new('RGB', (200, 50), color='white')
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(test_image)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), "Test 123", fill='black', font=font)
        
        # 尝试OCR识别
        text = pytesseract.image_to_string(test_image, config='--psm 6')
        print(f"✅ Tesseract识别测试成功，结果: '{text.strip()}'")
        
        return True
        
    except ImportError as e:
        print(f"❌ pytesseract Python包导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ Tesseract功能测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=== ArtaleKey OCR增强 - 安装Tesseract OCR ===")
    print()
    
    # 安装系统级别的Tesseract
    if not install_tesseract():
        print("❌ 系统级别Tesseract安装失败")
        return False
    
    # 安装Python包
    if not install_python_package():
        print("❌ Python包安装失败")
        return False
    
    # 测试安装
    if not test_installation():
        print("❌ 安装测试失败")
        return False
    
    print()
    print("🎉 Tesseract OCR安装完成！")
    print("现在可以使用增强的多引擎OCR功能了。")
    print()
    print("提示：")
    print("- 重启ArtaleKey应用以使用新的OCR引擎")
    print("- 新的OCR功能特别优化了橙色背景白色文字的识别")
    print("- 支持多种图像预处理方法提高识别准确性")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 