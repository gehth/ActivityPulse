"""应用使用限制的数据库操作"""

from datetime import datetime
from typing import List, Dict, Optional


class AppLimitMixin:
    """应用使用限制的数据库操作"""

    def set_app_limit(self, app_name: str, daily_limit_minutes: int, enabled: bool = True) -> None:
        """设置应用每日使用限制（线程安全）"""
        self._execute("""
            INSERT OR REPLACE INTO app_limits (app_name, daily_limit_minutes, enabled)
            VALUES (?, ?, ?)
        """, (app_name, daily_limit_minutes, 1 if enabled else 0))

    def get_app_limit(self, app_name: str) -> Optional[Dict]:
        """获取应用使用限制"""
        return self._query_one(
            "SELECT app_name, daily_limit_minutes, enabled FROM app_limits WHERE app_name = ?",
            (app_name,)
        )

    def get_all_limits(self) -> List[Dict]:
        """获取所有应用使用限制"""
        return self._query_all(
            "SELECT app_name, daily_limit_minutes, enabled FROM app_limits ORDER BY app_name"
        )

    def remove_app_limit(self, app_name: str) -> None:
        """删除应用使用限制（线程安全）"""
        self._execute("DELETE FROM app_limits WHERE app_name = ?", (app_name,))

    def check_app_limit(self, app_name: str, date: str = None) -> Optional[Dict]:
        """检查应用是否达到使用限制
        
        Args:
            app_name: 应用名称
            date: 日期(yyyy-MM-dd)，默认今天
        
        Returns:
            None表示无限制或未启用；否则返回 {limit_minutes, used_seconds, used_minutes, exceeded, remaining_minutes}
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        limit_info = self.get_app_limit(app_name)
        if not limit_info or not limit_info.get("enabled"):
            return None

        limit_minutes = limit_info["daily_limit_minutes"]
        if limit_minutes <= 0:
            return None

        # 获取今日该应用使用时长
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0)
            FROM app_usage WHERE app_name = ? AND date(start_time) = ?
        """, (app_name, date))
        used_seconds = cursor.fetchone()[0]
        used_minutes = used_seconds / 60

        return {
            "limit_minutes": limit_minutes,
            "used_seconds": used_seconds,
            "used_minutes": used_minutes,
            "exceeded": used_minutes >= limit_minutes,
            "remaining_minutes": max(0, limit_minutes - used_minutes),
        }

    def get_exceeded_limits(self, date: str = None) -> List[Dict]:
        """获取所有已超限的应用列表（单次JOIN查询优化，避免N+1查询）"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # 单次JOIN查询替代循环调用check_app_limit
        rows = self._query_all("""
            SELECT al.app_name, al.daily_limit_minutes,
                   COALESCE(SUM(au.duration_seconds), 0) as used_seconds
            FROM app_limits al
            LEFT JOIN app_usage au ON al.app_name = au.app_name AND date(au.start_time) = ?
            WHERE al.enabled = 1 AND al.daily_limit_minutes > 0
            GROUP BY al.app_name, al.daily_limit_minutes
            HAVING (COALESCE(SUM(au.duration_seconds), 0) / 60.0) >= al.daily_limit_minutes
        """, (date,))

        return [
            {
                "app_name": r["app_name"],
                "limit_minutes": r["daily_limit_minutes"],
                "used_minutes": int(r["used_seconds"] / 60),
            }
            for r in rows
        ]
