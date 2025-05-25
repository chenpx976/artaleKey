import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import numpy as np
from artalekey.core.logger import performance_logger

class GameDataDatabase:
    """游戏数据数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认数据库路径
            db_path = os.path.join(os.getcwd(), 'ocr_data', 'game_data.db')
        
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 创建游戏数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS game_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level INTEGER,
                        experience TEXT,
                        money TEXT,
                        raw_data TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 创建索引
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON game_data(timestamp)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_created_at ON game_data(created_at)
                ''')
                
                conn.commit()
                performance_logger.info(f"数据库初始化完成: {self.db_path}")
                
        except Exception as e:
            performance_logger.error(f"数据库初始化失败: {e}")
            raise
    
    def _make_json_serializable(self, obj):
        """将对象转换为JSON可序列化格式"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        else:
            return obj
    
    def insert_game_data(self, game_data: Dict[str, Any]) -> bool:
        """插入游戏数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                timestamp = game_data.get('timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
                level = game_data.get('level')
                experience = game_data.get('experience')
                money = game_data.get('money')
                
                # 使用JSON序列化处理numpy类型
                serializable_data = self._make_json_serializable(game_data)
                raw_data = json.dumps(serializable_data, ensure_ascii=False)
                
                # 将复杂数据类型转换为字符串
                if isinstance(experience, dict):
                    experience = json.dumps(experience, ensure_ascii=False)
                if isinstance(money, (dict, list)):
                    money = json.dumps(money, ensure_ascii=False)
                
                cursor.execute('''
                    INSERT INTO game_data (timestamp, level, experience, money, raw_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (timestamp, level, experience, money, raw_data))
                
                conn.commit()
                performance_logger.info(f"游戏数据已保存到数据库: Level={level}, Exp={experience}, Money={money}")
                return True
                
        except Exception as e:
            performance_logger.error(f"保存游戏数据失败: {e}")
            return False
    
    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """获取最新的游戏数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp, level, experience, money, raw_data, created_at
                    FROM game_data
                    ORDER BY created_at DESC
                    LIMIT 1
                ''')
                
                row = cursor.fetchone()
                if row:
                    # 尝试反序列化复杂数据类型
                    experience = row[2]
                    if experience and isinstance(experience, str) and experience.startswith('{'):
                        try:
                            experience = json.loads(experience)
                        except:
                            pass
                    
                    money = row[3]
                    if money and isinstance(money, str) and (money.startswith('{') or money.startswith('[')):
                        try:
                            money = json.loads(money)
                        except:
                            pass
                    
                    return {
                        'timestamp': row[0],
                        'level': row[1],
                        'experience': experience,
                        'money': money,
                        'raw_data': json.loads(row[4]) if row[4] else {},
                        'created_at': row[5]
                    }
                    
        except Exception as e:
            performance_logger.error(f"获取最新数据失败: {e}")
            
        return None
    
    def get_data_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取历史数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp, level, experience, money, raw_data, created_at
                    FROM game_data
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    # 尝试反序列化复杂数据类型
                    experience = row[2]
                    if experience and isinstance(experience, str) and experience.startswith('{'):
                        try:
                            experience = json.loads(experience)
                        except:
                            pass
                    
                    money = row[3]
                    if money and isinstance(money, str) and (money.startswith('{') or money.startswith('[')):
                        try:
                            money = json.loads(money)
                        except:
                            pass
                    
                    result.append({
                        'timestamp': row[0],
                        'level': row[1],
                        'experience': experience,
                        'money': money,
                        'raw_data': json.loads(row[4]) if row[4] else {},
                        'created_at': row[5]
                    })
                return result
                
        except Exception as e:
            performance_logger.error(f"获取历史数据失败: {e}")
            return []
    
    def get_data_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """根据日期范围获取数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp, level, experience, money, raw_data, created_at
                    FROM game_data
                    WHERE created_at BETWEEN ? AND ?
                    ORDER BY created_at DESC
                ''', (start_date, end_date))
                
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    # 尝试反序列化复杂数据类型
                    experience = row[2]
                    if experience and isinstance(experience, str) and experience.startswith('{'):
                        try:
                            experience = json.loads(experience)
                        except:
                            pass
                    
                    money = row[3]
                    if money and isinstance(money, str) and (money.startswith('{') or money.startswith('[')):
                        try:
                            money = json.loads(money)
                        except:
                            pass
                    
                    result.append({
                        'timestamp': row[0],
                        'level': row[1],
                        'experience': experience,
                        'money': money,
                        'raw_data': json.loads(row[4]) if row[4] else {},
                        'created_at': row[5]
                    })
                return result
                
        except Exception as e:
            performance_logger.error(f"根据日期范围获取数据失败: {e}")
            return []
    
    def delete_old_data(self, days: int = 30) -> int:
        """删除指定天数之前的旧数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM game_data
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                performance_logger.info(f"删除了 {deleted_count} 条 {days} 天前的旧数据")
                return deleted_count
                
        except Exception as e:
            performance_logger.error(f"删除旧数据失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总记录数
                cursor.execute('SELECT COUNT(*) FROM game_data')
                total_count = cursor.fetchone()[0]
                
                # 最早和最新记录时间
                cursor.execute('''
                    SELECT MIN(created_at), MAX(created_at) FROM game_data
                ''')
                min_date, max_date = cursor.fetchone()
                
                # 最高等级
                cursor.execute('SELECT MAX(level) FROM game_data WHERE level IS NOT NULL')
                max_level = cursor.fetchone()[0]
                
                return {
                    'total_records': total_count,
                    'earliest_record': min_date,
                    'latest_record': max_date,
                    'max_level': max_level
                }
                
        except Exception as e:
            performance_logger.error(f"获取统计信息失败: {e}")
            return {}

# 全局数据库实例
game_db = GameDataDatabase() 