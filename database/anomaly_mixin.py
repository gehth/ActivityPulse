"""异常告警和持续使用检测的数据库操作"""

from collections import defaultdict
from datetime import datetime
from typing import List, Dict
from utils.segment_merge import merge_continuous_segments


class AnomalyMixin:
    """异常告警和持续使用检测的数据库操作"""

    def save_anomaly_alert(self, alert_type: str, title: str, description: str = None,
                           app_name: str = None, severity: str = "warning",
                           threshold_value: float = None, actual_value: float = None) -> int:
        """保存异常告警记录（线程安全）

        Args:
            alert_type: 告警类型 (continuous_use/late_night/daily_deviation/no_break)
            title: 告警标题
            description: 告警描述
            app_name: 关联应用名（可选）
            severity: 严重程度 info/warning/critical
            threshold_value: 阈值
            actual_value: 实际值

        Returns:
            新记录ID
        """
        return self._execute("""
            INSERT INTO anomaly_alerts
                (alert_type, severity, title, description, app_name,
                 detected_at, threshold_value, actual_value)
            VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'), ?, ?)
        """, (alert_type, severity, title, description, app_name,
              threshold_value, actual_value))

    def get_anomaly_alerts(self, limit: int = 50, unread_only: bool = False,
                           dismissed: bool = False) -> List[Dict]:
        """获取异常告警列表"""
        conditions = []
        params = []
        if unread_only:
            conditions.append("is_read = 0")
        if not dismissed:
            conditions.append("is_dismissed = 0")
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT id, alert_type, severity, title, description, app_name,
                   detected_at, threshold_value, actual_value, is_read, is_dismissed
            FROM anomaly_alerts{where_clause}
            ORDER BY detected_at DESC
            LIMIT ?
        """
        params.append(limit)
        return self._query_all(sql, tuple(params))

    def get_unread_alert_count(self) -> int:
        """获取未读告警数量"""
        row = self._query_one(
            "SELECT COUNT(*) as cnt FROM anomaly_alerts WHERE is_read = 0 AND is_dismissed = 0"
        )
        return row["cnt"] if row else 0

    def mark_alert_read(self, alert_id: int) -> None:
        """标记告警已读（线程安全）"""
        self._execute("UPDATE anomaly_alerts SET is_read = 1 WHERE id = ?", (alert_id,))

    def mark_all_alerts_read(self) -> None:
        """标记所有告警已读（线程安全）"""
        self._execute("UPDATE anomaly_alerts SET is_read = 1 WHERE is_read = 0")

    def dismiss_alert(self, alert_id: int) -> None:
        """忽略告警（线程安全）"""
        self._execute("UPDATE anomaly_alerts SET is_dismissed = 1 WHERE id = ?", (alert_id,))

    def check_recent_alert_exists(self, alert_type: str, hours: float = 1.0,
                                  app_name: str = None) -> bool:
        """检查近期是否已有相同类型的告警（避免重复告警）

        Args:
            alert_type: 告警类型
            hours: 检查最近N小时内
            app_name: 可选，限定应用名
        """
        hours_param = f"-{hours} hours"
        if app_name:
            row = self._query_one("""
                SELECT COUNT(*) as cnt FROM anomaly_alerts
                WHERE alert_type = ? AND app_name = ?
                  AND detected_at >= datetime('now', 'localtime', ?)
            """, (alert_type, app_name, hours_param))
        else:
            row = self._query_one("""
                SELECT COUNT(*) as cnt FROM anomaly_alerts
                WHERE alert_type = ?
                  AND detected_at >= datetime('now', 'localtime', ?)
            """, (alert_type, hours_param))
        return (row["cnt"] if row else 0) > 0

    def get_continuous_app_usage(self, date: str = None, min_minutes: float = 60) -> List[Dict]:
        """获取连续使用同一应用的记录（超过指定时长）

        通过查找同一天中同一应用的连续记录，计算不间断使用时长。
        两条记录间隔小于5分钟视为连续。
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT app_name, start_time, end_time, duration_seconds
            FROM app_usage
            WHERE date(start_time) = ?
            ORDER BY app_name, start_time
        """, (date,))
        rows = cursor.fetchall()

        # 按应用分组，检测连续使用
        app_records = defaultdict(list)
        for r in rows:
            app_records[r[0]].append({
                "start_time": r[1], "end_time": r[2], "duration_seconds": r[3]
            })

        results = []
        for app_name, records in app_records.items():
            segments = merge_continuous_segments(
                records,
                gap_threshold_seconds=300,
                min_duration_seconds=min_minutes * 60,
                accumulate_duration=True,
            )
            for seg in segments:
                seg["app_name"] = app_name
            results.extend(segments)

        return sorted(results, key=lambda x: x["duration_seconds"], reverse=True)

    def get_late_night_usage(self, date: str = None,
                             start_hour: int = 23, end_hour: int = 6) -> List[Dict]:
        """获取深夜使用记录

        Args:
            date: 日期，默认今天
            start_hour: 深夜起始小时（默认23点）
            end_hour: 深夜结束小时（默认6点）
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        rows = self._query_all("""
            SELECT app_name,
                   SUM(duration_seconds) as total_seconds,
                   MIN(start_time) as first_active,
                   MAX(end_time) as last_active
            FROM app_usage
            WHERE date(start_time) = ?
              AND (strftime('%H', start_time) >= ? OR strftime('%H', start_time) < ?)
            GROUP BY app_name
            ORDER BY total_seconds DESC
        """, (date, f"{start_hour:02d}", f"{end_hour:02d}"))
        return [
            {
                "app_name": r["app_name"],
                "total_seconds": r["total_seconds"],
                "total_minutes": (r["total_seconds"] or 0) / 60,
                "first_active": r["first_active"],
                "last_active": r["last_active"],
            }
            for r in rows
        ]

    def get_recent_daily_totals(self, days: int = 7) -> List[Dict]:
        """获取最近N天的每日总使用时长（用于计算均值和偏离检测）"""
        rows = self._query_all("""
            SELECT date(start_time) as day,
                   SUM(duration_seconds) as total_seconds
            FROM app_usage
            WHERE date(start_time) >= date('now', 'localtime', ?)
            GROUP BY date(start_time)
            ORDER BY day
        """, (f"-{days} days",))
        return [
            {"date": r["day"], "total_seconds": r["total_seconds"], "total_minutes": (r["total_seconds"] or 0) / 60}
            for r in rows
        ]

    def get_continuous_computer_usage(self, date: str = None,
                                      gap_minutes: int = 10) -> List[Dict]:
        """获取连续使用电脑的时段（无长间隔）

        Args:
            date: 日期，默认今天
            gap_minutes: 间隔超过此分钟数视为中断
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        rows = self._query_all("""
            SELECT start_time, end_time, duration_seconds
            FROM app_usage
            WHERE date(start_time) = ?
            ORDER BY start_time
        """, (date,))

        if not rows:
            return []

        records = [{"start_time": r["start_time"], "end_time": r["end_time"]}
                   for r in rows]
        return merge_continuous_segments(
            records,
            gap_threshold_seconds=gap_minutes * 60,
            accumulate_duration=False,
        )
