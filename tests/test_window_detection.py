#!/usr/bin/env python3
"""
窗口检测功能测试脚本
"""

import time
from artalekey.core.window_detector import WindowDetector, ActiveWindowMonitor

def test_window_detection():
    """测试窗口检测功能"""
    print("🔍 测试窗口检测功能...")
    
    detector = WindowDetector()
    
    # 测试获取当前活动窗口
    print("\n📱 获取当前活动窗口:")
    for i in range(5):
        window = detector.get_active_window()
        if window:
            print(f"   {i+1}. {window}")
        else:
            print(f"   {i+1}. 无法检测到窗口")
        time.sleep(1)
    
    # 测试获取运行的应用程序
    print("\n📋 获取运行的应用程序 (前10个):")
    apps = detector.get_running_applications()
    for i, app in enumerate(apps[:10]):
        print(f"   {i+1}. {app}")
    
    print(f"\n总共检测到 {len(apps)} 个应用程序")

def test_window_monitor():
    """测试窗口监控器"""
    print("\n🔍 测试窗口监控器...")
    
    monitor = ActiveWindowMonitor()
    
    # 设置一些目标应用
    print("设置目标应用: MapleStory Worlds, Safari, Chrome")
    monitor.set_target_processes(["MapleStory Worlds", "Safari", "Google Chrome"])
    
    def on_window_changed(window_info):
        print(f"   窗口变化: {window_info}")
    
    def on_target_activated():
        print("   ✅ 目标窗口激活!")
    
    def on_target_deactivated():
        print("   ❌ 目标窗口失活!")
    
    # 连接信号
    monitor.active_window_changed.connect(on_window_changed)
    monitor.target_window_activated.connect(on_target_activated)
    monitor.target_window_deactivated.connect(on_target_deactivated)
    
    # 启动监控
    monitor.start()
    
    print("监控已启动，切换不同应用程序窗口来测试...")
    print("按 Ctrl+C 停止测试")
    
    try:
        # 运行10秒
        for i in range(10):
            current = monitor.get_current_window()
            is_target = monitor.is_target_window_active()
            print(f"   第{i+1}秒: 当前窗口: {current.process_name if current else 'None'}, 目标激活: {is_target}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n收到中断信号")
    finally:
        monitor.stop()
        print("监控已停止")

if __name__ == "__main__":
    import sys
    
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        
        print("🚀 开始窗口检测测试\n" + "="*50)
        
        # 基本检测测试
        test_window_detection()
        
        # 监控测试
        test_window_monitor()
        
        print("\n" + "="*50)
        print("✅ 测试完成")
        
        app.quit()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保安装了所有必要的依赖")
    except Exception as e:
        print(f"测试出错: {e}") 