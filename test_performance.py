#!/usr/bin/env python3
"""
ArtaleKey 性能测试脚本
测试优化后的性能改进
"""

import time
import threading
import psutil
import gc
from artalekey.core.hotkey_manager import KeyboardManager, KeySimulator, HotkeyListener
from artalekey.core.config import config_manager
from artalekey.core.logger import performance_logger

class PerformanceTest:
    """性能测试类"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
        
    def get_memory_usage(self):
        """获取内存使用量（MB）"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_cpu_usage(self):
        """获取CPU使用率"""
        return self.process.cpu_percent()
    
    def test_singleton_performance(self):
        """测试单例模式性能"""
        print("🔧 测试键盘管理器单例性能...")
        
        start_time = time.perf_counter()
        instances = []
        
        # 创建多个实例，应该都指向同一个对象
        for _ in range(1000):
            instances.append(KeyboardManager())
        
        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000
        
        # 验证都是同一个实例
        all_same = all(instance is instances[0] for instance in instances)
        
        print(f"   ✓ 创建1000个单例实例耗时: {duration:.2f}ms")
        print(f"   ✓ 单例正确性: {'通过' if all_same else '失败'}")
        
        del instances
        gc.collect()
    
    def test_key_simulator_performance(self):
        """测试按键模拟器性能"""
        print("⌨️  测试按键模拟器性能...")
        
        simulator = KeySimulator()
        
        # 测试设置间隔的性能
        start_time = time.perf_counter()
        for i in range(1000):
            simulator.set_interval(10 + i % 100)
        end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000
        print(f"   ✓ 1000次间隔设置耗时: {duration:.2f}ms")
        
        # 测试启动/停止性能
        start_time = time.perf_counter()
        simulator.start()
        time.sleep(0.1)  # 运行100ms
        simulator.stop()
        simulator.wait(1000)
        end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000
        print(f"   ✓ 启动-运行-停止周期耗时: {duration:.2f}ms")
        
        simulator.deleteLater()
    
    def test_config_performance(self):
        """测试配置管理性能"""
        print("⚙️  测试配置管理性能...")
        
        # 测试配置读取性能
        start_time = time.perf_counter()
        for _ in range(100):
            config = config_manager.get_hotkey_config("default")
        end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000
        print(f"   ✓ 100次配置读取耗时: {duration:.2f}ms")
        
        # 测试配置写入性能（不自动保存）
        start_time = time.perf_counter()
        for i in range(100):
            config_manager.set_hotkey_config(
                "test", 
                {"hold_time": 500 + i, "interval": 40 + i, "enabled": True},
                auto_save=False
            )
        end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000
        print(f"   ✓ 100次配置写入（无保存）耗时: {duration:.2f}ms")
        
        # 测试一次完整保存
        start_time = time.perf_counter()
        config_manager.save_config()
        end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000
        print(f"   ✓ 完整配置保存耗时: {duration:.2f}ms")
    
    def test_memory_leak(self):
        """测试内存泄漏"""
        print("🧠 测试内存泄漏...")
        
        initial_memory = self.get_memory_usage()
        print(f"   📊 初始内存使用: {initial_memory:.1f}MB")
        
        # 创建和销毁多个组件
        for i in range(10):
            simulator = KeySimulator()
            simulator.set_interval(40)
            time.sleep(0.01)
            simulator.deleteLater()
            
            if i % 3 == 0:
                gc.collect()
        
        gc.collect()
        time.sleep(0.5)  # 等待清理
        
        final_memory = self.get_memory_usage()
        memory_diff = final_memory - initial_memory
        
        print(f"   📊 最终内存使用: {final_memory:.1f}MB")
        print(f"   📈 内存变化: {memory_diff:+.1f}MB")
        
        if memory_diff < 5:  # 小于5MB认为正常
            print("   ✅ 内存使用正常")
        else:
            print("   ⚠️  可能存在内存泄漏")
    
    def test_cpu_usage(self):
        """测试CPU使用率"""
        print("💻 测试CPU使用率...")
        
        # 重置CPU计数器
        self.process.cpu_percent()
        
        # 运行模拟器一段时间
        simulator = KeySimulator()
        simulator.set_interval(20)  # 较快的间隔
        
        cpu_samples = []
        
        simulator.start()
        
        for _ in range(10):
            time.sleep(0.1)
            cpu = self.process.cpu_percent()
            cpu_samples.append(cpu)
        
        simulator.stop()
        simulator.wait(1000)
        simulator.deleteLater()
        
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        
        print(f"   📊 平均CPU使用率: {avg_cpu:.1f}%")
        print(f"   📊 峰值CPU使用率: {max_cpu:.1f}%")
        
        if avg_cpu < 5:
            print("   ✅ CPU使用率正常")
        elif avg_cpu < 15:
            print("   ⚠️  CPU使用率偏高")
        else:
            print("   ❌ CPU使用率过高")
    
    def run_all_tests(self):
        """运行所有性能测试"""
        print("🚀 开始ArtaleKey性能测试\n" + "="*50)
        
        start_time = time.time()
        
        try:
            self.test_singleton_performance()
            print()
            
            self.test_key_simulator_performance()
            print()
            
            self.test_config_performance()
            print()
            
            self.test_memory_leak()
            print()
            
            self.test_cpu_usage()
            print()
            
        except Exception as e:
            print(f"❌ 测试出错: {e}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - self.initial_memory
        
        print("="*50)
        print("📊 性能测试报告")
        print(f"   ⏱️  总测试时间: {total_duration:.2f}秒")
        print(f"   🧠 内存增长: {memory_increase:+.1f}MB")
        print(f"   💾 最终内存: {final_memory:.1f}MB")
        
        # 性能评估
        if memory_increase < 10 and total_duration < 30:
            print("   ✅ 性能优秀")
        elif memory_increase < 20 and total_duration < 60:
            print("   ✅ 性能良好")
        else:
            print("   ⚠️  性能需要进一步优化")

if __name__ == "__main__":
    import sys
    
    # 如果PyQt6不可用，跳过GUI相关测试
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        
        tester = PerformanceTest()
        tester.run_all_tests()
        
        app.quit()
        
    except ImportError:
        print("PyQt6不可用，跳过完整测试")
        tester = PerformanceTest()
        tester.test_config_performance() 