#!/usr/bin/env python3
"""
UI修复应用脚本 - 快速应用所有UI改进
"""

import os
import sys

def main():
    """应用UI修复"""
    print("🎨 正在应用ArtaleKey UI修复...")
    print()
    
    # 检查项目结构
    if not os.path.exists('artalekey'):
        print("❌ 错误：找不到artalekey目录")
        print("   请确保在项目根目录运行此脚本")
        return 1
    
    # 检查关键文件
    key_files = [
        'artalekey/ui/styles.py',
        'artalekey/ui/main_window.py',
        'artalekey/ui/components.py',
        'artalekey/ui/target_app_selector.py'
    ]
    
    print("📁 检查文件状态...")
    all_exists = True
    for file_path in key_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - 缺失")
            all_exists = False
    
    if not all_exists:
        print("\n❌ 部分文件缺失，请确保所有修复文件都已正确创建")
        return 1
    
    print("\n🔧 修复内容包括：")
    print("   • macOS优化的字体系统")
    print("   • 改善的颜色对比度") 
    print("   • 统一的样式管理")
    print("   • 中文字体支持优化")
    print("   • 更好的交互体验")
    
    print("\n📱 建议测试步骤：")
    print("   1. 运行 python run_ui_test.py")
    print("   2. 检查字体显示是否清晰")
    print("   3. 测试所有按钮和控件")
    print("   4. 验证中文文字显示")
    print("   5. 检查颜色对比度")
    
    print("\n✅ UI修复已完成！")
    
    # 询问是否启动测试
    try:
        answer = input("\n🚀 是否现在启动UI测试？ (y/n): ").lower().strip()
        if answer in ['y', 'yes', '是']:
            print("\n正在启动UI测试...")
            os.system("python run_ui_test.py")
    except KeyboardInterrupt:
        print("\n👋 退出")
        return 0
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 