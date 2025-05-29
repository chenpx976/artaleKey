import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import numpy as np
from artalekey.core.logger import performance_logger
import sys
import platform

def _get_app_data_dir():
    """获取应用数据目录 - 使用系统标准的用户数据目录"""
    app_name = "ArtaleKey"
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # ~/Library/Application Support/ArtaleKey/
        home = os.path.expanduser("~")
        data_dir = os.path.join(home, "Library", "Application Support", app_name)
    elif system == "Windows":
        # %APPDATA%\ArtaleKey\
        appdata = os.environ.get("APPDATA")
        if appdata:
            data_dir = os.path.join(appdata, app_name)
        else:
            # 后备方案
            home = os.path.expanduser("~")
            data_dir = os.path.join(home, "AppData", "Roaming", app_name)
    else:  # Linux 和其他 Unix 系统
        # ~/.local/share/ArtaleKey/
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            data_dir = os.path.join(xdg_data_home, app_name)
        else:
            home = os.path.expanduser("~")
            data_dir = os.path.join(home, ".local", "share", app_name)
    
    return data_dir

def get_app_data_dir():
    """公开的获取应用数据目录函数，供其他模块使用"""
    return _get_app_data_dir()

class GameDataDatabase:
    """游戏数据数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 使用应用数据目录而不是当前工作目录
            data_dir = _get_app_data_dir()
            db_path = os.path.join(data_dir, 'game_data.db')
        
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
                
                # 先查看总记录数和时间范围
                cursor.execute('SELECT COUNT(*) FROM game_data')
                total_before = cursor.fetchone()[0]
                
                cursor.execute('SELECT MIN(created_at), MAX(created_at) FROM game_data')
                date_range = cursor.fetchone()
                performance_logger.info(f"删除前数据: 总计{total_before}条, 时间范围: {date_range[0]} 到 {date_range[1]}")
                
                # 计算截止时间
                cutoff_date = f"datetime('now', '-{days} days')"
                performance_logger.info(f"将删除 {days} 天前的数据")
                
                # 先查看将要删除的记录数
                cursor.execute(f'''
                    SELECT COUNT(*) FROM game_data
                    WHERE created_at < {cutoff_date}
                ''')
                to_delete_count = cursor.fetchone()[0]
                performance_logger.info(f"将要删除 {to_delete_count} 条记录")
                
                # 执行删除
                cursor.execute(f'''
                    DELETE FROM game_data
                    WHERE created_at < {cutoff_date}
                ''')
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                # 查看删除后的记录数
                cursor.execute('SELECT COUNT(*) FROM game_data')
                total_after = cursor.fetchone()[0]
                
                performance_logger.info(f"删除了 {deleted_count} 条 {days} 天前的旧数据")
                performance_logger.info(f"删除后数据: 总计{total_after}条")
                return deleted_count
                
        except Exception as e:
            performance_logger.error(f"删除旧数据失败: {e}")
            return 0
    
    def get_experience_data_for_visualization(self, level_filter: int = None, 
                                            hours_limit: int = 24) -> List[Dict[str, Any]]:
        """获取用于可视化的经验数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 构建查询条件
                where_conditions = []
                params = []
                
                # 时间限制
                where_conditions.append("created_at >= datetime('now', '-{} hours')".format(hours_limit))
                
                # 等级过滤
                if level_filter is not None:
                    where_conditions.append("level = ?")
                    params.append(level_filter)
                
                # 只获取有经验数据的记录
                where_conditions.append("experience IS NOT NULL")
                where_conditions.append("experience != ''")
                
                where_clause = " AND ".join(where_conditions)
                
                query = f'''
                    SELECT timestamp, level, experience, created_at
                    FROM game_data
                    WHERE {where_clause}
                    ORDER BY created_at ASC
                '''
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    experience = row[2]
                    if experience and isinstance(experience, str) and experience.startswith('{'):
                        try:
                            experience = json.loads(experience)
                        except:
                            experience = None
                    
                    if experience and isinstance(experience, dict):
                        result.append({
                            'timestamp': row[0],
                            'level': row[1],
                            'experience': experience,
                            'created_at': row[3]
                        })
                
                performance_logger.info(f"获取到 {len(result)} 条可视化数据，等级过滤: {level_filter}, 时间限制: {hours_limit}小时")
                return result
                
        except Exception as e:
            performance_logger.error(f"获取可视化数据失败: {e}")
            return []
    
    def get_experience_stats_by_time_interval(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """按时间间隔统计经验获取"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 获取最近24小时内的经验数据
                cursor.execute('''
                    SELECT level, experience, created_at
                    FROM game_data
                    WHERE created_at >= datetime('now', '-24 hours')
                    AND experience IS NOT NULL
                    AND experience != ''
                    ORDER BY created_at ASC
                ''')
                
                rows = cursor.fetchall()
                if not rows:
                    return []
                
                # 解析经验数据并按时间间隔分组
                import re
                
                time_groups = {}
                
                for row in rows:
                    level = row[0]
                    experience_str = row[1]
                    created_at_str = row[2]
                    
                    # 解析经验数据
                    experience = None
                    if experience_str and isinstance(experience_str, str) and experience_str.startswith('{'):
                        try:
                            experience = json.loads(experience_str)
                        except:
                            continue
                    
                    if not experience or not isinstance(experience, dict):
                        continue
                    
                    exp_value = experience.get('value', 0)
                    if exp_value <= 0:
                        continue
                    
                    # 解析时间
                    try:
                        # SQLite的时间格式：YYYY-MM-DD HH:MM:SS
                        dt = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        continue
                    
                    # 计算时间分组key（按分钟间隔）
                    minute_group = (dt.hour * 60 + dt.minute) // minutes
                    time_key = dt.replace(hour=minute_group * minutes // 60, 
                                        minute=minute_group * minutes % 60, 
                                        second=0, microsecond=0)
                    
                    if time_key not in time_groups:
                        time_groups[time_key] = {
                            'start_time': time_key,
                            'end_time': time_key + timedelta(minutes=minutes),
                            'exp_records': [],
                            'levels': set()
                        }
                    
                    time_groups[time_key]['exp_records'].append(exp_value)
                    time_groups[time_key]['levels'].add(level)
                
                # 计算每个时间段的统计
                result = []
                for time_key in sorted(time_groups.keys()):
                    group = time_groups[time_key]
                    exp_records = group['exp_records']
                    
                    if len(exp_records) >= 2:  # 至少需要2条记录才能计算增长
                        exp_gain = max(exp_records) - min(exp_records)
                        # 过滤None值
                        valid_levels = [level for level in group['levels'] if level is not None]
                        avg_level = sum(valid_levels) / len(valid_levels) if valid_levels else 0
                        
                        result.append({
                            'start_time': group['start_time'].strftime('%H:%M'),
                            'end_time': group['end_time'].strftime('%H:%M'),
                            'duration_minutes': minutes,
                            'exp_gain': exp_gain,
                            'avg_level': round(avg_level, 1),
                            'record_count': len(exp_records)
                        })
                
                performance_logger.info(f"按 {minutes} 分钟间隔统计，获得 {len(result)} 个时间段的数据")
                return result
                
        except Exception as e:
            performance_logger.error(f"按时间间隔统计经验失败: {e}")
            return []
    
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