"""数据库管理模块 - 使用SQLite存储电脑行为记录（线程安全）"""

import sqlite3
import os
import threading
import logging
from typing import List, Dict, Optional

from database.app_usage_mixin import AppUsageMixin
from database.screenshot_mixin import ScreenshotMixin
from database.settings_mixin import SettingsMixin
from database.idle_mixin import IdleMixin
from database.activity_tag_mixin import ActivityTagMixin
from database.app_limit_mixin import AppLimitMixin
from database.anomaly_mixin import AnomalyMixin

logger = logging.getLogger(__name__)


class DatabaseManager(
    AppUsageMixin,
    ScreenshotMixin,
    SettingsMixin,
    IdleMixin,
    ActivityTagMixin,
    AppLimitMixin,
    AnomalyMixin,
):
    """管理SQLite数据库连接和操作（线程安全）

    使用线程锁保护所有数据库操作，避免多线程并发写入导致SQLITE_BUSY错误。
    每个线程获取独立连接（通过thread local），写操作通过全局锁串行化。
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = os.path.join(os.path.expanduser("~"), ".computer_monitor")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "monitor.db")

        self.db_path = db_path
        self._lock = threading.Lock()  # 全局写锁
        self._local = threading.local()  # 线程本地存储
        self._config_cache: Dict[str, str] = {}  # 配置项内存缓存
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接（线程安全）"""
        conn = getattr(self._local, 'conn', None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
            conn.row_factory = sqlite3.Row
            # 启用WAL模式，提升并发读写性能
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()

        self._create_tables(cursor)
        self._create_indexes(cursor)

        conn.commit()

    def _create_tables(self, cursor):
        """创建所有数据库表"""
        # 应用使用记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT NOT NULL,
                window_title TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 键鼠操作记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS input_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_detail TEXT,
                app_name TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 屏幕截图记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                thumbnail_path TEXT,
                app_name TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 应用设置表（自定义分类、敏感标记）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                app_name TEXT PRIMARY KEY,
                custom_category TEXT,
                is_sensitive INTEGER DEFAULT 0
            )
        """)

        # 配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # 应用使用限制表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_limits (
                app_name TEXT PRIMARY KEY,
                daily_limit_minutes INTEGER NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 活动标签表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                tag TEXT NOT NULL,
                note TEXT,
                start_time TEXT,
                end_time TEXT,
                color TEXT DEFAULT '#3B82F6',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 异常告警记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'warning',
                title TEXT NOT NULL,
                description TEXT,
                app_name TEXT,
                detected_at TEXT NOT NULL,
                threshold_value REAL,
                actual_value REAL,
                is_read INTEGER DEFAULT 0,
                is_dismissed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

    def _create_indexes(self, cursor):
        """创建所有索引"""
        # 基础索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_usage_time ON app_usage(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_events_time ON input_events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenshots_time ON screenshots(timestamp)")

        # 性能优化索引：常用查询条件
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_usage_app ON app_usage(app_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_usage_date ON app_usage(date(start_time))")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_events_type ON input_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_input_events_date ON input_events(date(timestamp))")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenshots_date ON screenshots(date(timestamp))")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_usage_end_time ON app_usage(end_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_settings_sensitive ON app_settings(is_sensitive)")

        # 活动标签索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_tags_date ON activity_tags(date)")

        # 异常告警索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_type ON anomaly_alerts(alert_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_detected ON anomaly_alerts(detected_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_read ON anomaly_alerts(is_read)")

    # === 查询助手方法 ===

    def _query_all(self, sql: str, params: tuple = None) -> List[Dict]:
        """执行SELECT查询，返回字典列表（线程安全读操作，无需加锁）

        Args:
            sql: SQL查询语句
            params: 查询参数元组

        Returns:
            字典列表，每个字典对应一行记录
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return [dict(row) for row in cursor.fetchall()]

    def _query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """执行SELECT查询，返回单条字典记录或None

        Args:
            sql: SQL查询语句
            params: 查询参数元组

        Returns:
            字典或None
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        row = cursor.fetchone()
        return dict(row) if row else None

    def _execute(self, sql: str, params: tuple = None, commit: bool = True) -> int:
        """执行写操作（INSERT/UPDATE/DELETE），返回lastrowid（线程安全）

        Args:
            sql: SQL语句
            params: 参数元组
            commit: 是否自动提交（默认True）

        Returns:
            cursor.lastrowid
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            if commit:
                conn.commit()
            return cursor.lastrowid

    def _execute_fetch(self, sql: str, params: tuple = None) -> list:
        """执行写操作并返回fetchall结果（用于DELETE前先SELECT统计，线程安全）

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            cursor.fetchall()结果列表
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            result = cursor.fetchall()
            conn.commit()
            return result

    def cleanup_old_data(self, retention_days: int) -> dict:
        """清理过期数据（线程安全）

        Args:
            retention_days: 保留天数，0表示永久保留

        Returns:
            清理统计 {'app_usage': count, 'input_events': count, 'screenshots': count}
        """
        if retention_days <= 0:
            return {'app_usage': 0, 'input_events': 0, 'screenshots': 0}

        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            stats = {}

            # 使用参数化查询替代f-string拼接，防止SQL注入
            cutoff_param = f"-{retention_days} days"

            # 清理应用使用记录
            cursor.execute(
                "SELECT COUNT(*) FROM app_usage WHERE created_at < datetime('now', ?, 'localtime')",
                (cutoff_param,)
            )
            stats['app_usage'] = cursor.fetchone()[0]
            cursor.execute(
                "DELETE FROM app_usage WHERE created_at < datetime('now', ?, 'localtime')",
                (cutoff_param,)
            )

            # 清理键鼠操作记录
            cursor.execute(
                "SELECT COUNT(*) FROM input_events WHERE created_at < datetime('now', ?, 'localtime')",
                (cutoff_param,)
            )
            stats['input_events'] = cursor.fetchone()[0]
            cursor.execute(
                "DELETE FROM input_events WHERE created_at < datetime('now', ?, 'localtime')",
                (cutoff_param,)
            )

            # 清理截图记录（同时删除文件）
            cursor.execute(
                "SELECT file_path, thumbnail_path FROM screenshots WHERE created_at < datetime('now', ?, 'localtime')",
                (cutoff_param,)
            )
            old_screenshots = cursor.fetchall()
            for row in old_screenshots:
                for col_idx in range(len(row)):
                    fpath = row[col_idx]
                    if fpath:
                        try:
                            if os.path.exists(fpath):
                                os.remove(fpath)
                        except Exception:
                            pass
            cursor.execute(
                "SELECT COUNT(*) FROM screenshots WHERE created_at < datetime('now', ?, 'localtime')",
                (cutoff_param,)
            )
            stats['screenshots'] = cursor.fetchone()[0]
            cursor.execute(
                "DELETE FROM screenshots WHERE created_at < datetime('now', ?, 'localtime')",
                (cutoff_param,)
            )

            conn.commit()
            return stats

    def close(self) -> None:
        """关闭数据库连接（关闭当前线程的连接，用于程序退出时调用）"""
        conn = getattr(self._local, 'conn', None)
        if conn:
            conn.close()
            self._local.conn = None