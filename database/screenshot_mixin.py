"""截图记录的数据库操作"""

from datetime import datetime
from typing import List, Dict


class ScreenshotMixin:
    """截图记录的数据库操作"""

    def save_screenshot(self, file_path: str, thumbnail_path: str = None,
                        app_name: str = None, timestamp: str = None) -> int:
        """保存截图记录（线程安全）"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self._execute("""
            INSERT INTO screenshots (file_path, thumbnail_path, app_name, timestamp)
            VALUES (?, ?, ?, ?)
        """, (file_path, thumbnail_path, app_name, timestamp))

    def get_screenshots(self, date: str = None, limit: int = 50) -> List[Dict]:
        """获取截图记录列表"""
        conditions = []
        params = []
        if date:
            conditions.append("date(timestamp) = ?")
            params.append(date)
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        sql = f"SELECT * FROM screenshots{where_clause} ORDER BY timestamp DESC LIMIT ?"
        return self._query_all(sql, tuple(params))

    def get_screenshots_count(self, start_date: str = None, end_date: str = None) -> int:
        """获取截图记录总数（支持日期范围）"""
        conditions = []
        params = []
        if start_date:
            conditions.append("date(timestamp) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date(timestamp) <= ?")
            params.append(end_date)
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT COUNT(*) as cnt FROM screenshots{where_clause}"
        row = self._query_one(sql, tuple(params) if params else None)
        return row["cnt"] if row else 0

    def get_screenshots_page(self, page: int = 1, page_size: int = 20,
                             start_date: str = None, end_date: str = None) -> List[Dict]:
        """获取截图记录分页列表（支持日期范围）"""
        conditions = []
        params = []
        if start_date:
            conditions.append("date(timestamp) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date(timestamp) <= ?")
            params.append(end_date)
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        params.extend([page_size, (page - 1) * page_size])
        sql = f"SELECT * FROM screenshots{where_clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        return self._query_all(sql, tuple(params))

    def get_screenshot_dates(self) -> List[str]:
        """获取有截图记录的日期列表（用于日期选择器范围）"""
        rows = self._query_all("""
            SELECT DISTINCT date(timestamp) as d
            FROM screenshots
            ORDER BY d DESC
        """)
        return [row["d"] for row in rows]

    def get_screenshots_for_playback(self, start_date: str, end_date: str = None) -> List[Dict]:
        """获取截图记录用于屏幕回放（按时间升序排列）

        Args:
            start_date: 起始日期 (yyyy-MM-dd)
            end_date: 结束日期，默认与start_date相同

        Returns:
            截图记录列表，按timestamp升序，包含id/file_path/thumbnail_path/app_name/timestamp
        """
        if end_date is None:
            end_date = start_date
        return self._query_all("""
            SELECT id, file_path, thumbnail_path, app_name, timestamp
            FROM screenshots
            WHERE date(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """, (start_date, end_date))

    def get_screenshots_time_range(self, start_date: str, end_date: str = None) -> Dict:
        """获取截图的时间范围信息（用于回放时间轴）

        Args:
            start_date: 起始日期
            end_date: 结束日期，默认与start_date相同

        Returns:
            {'first_time': str, 'last_time': str, 'count': int, 'duration_hours': float}
        """
        if end_date is None:
            end_date = start_date
        row = self._query_one("""
            SELECT MIN(timestamp) as first_time, MAX(timestamp) as last_time, COUNT(*) as count
            FROM screenshots
            WHERE date(timestamp) BETWEEN ? AND ?
        """, (start_date, end_date))
        if row and row["count"] > 0:
            first = datetime.fromisoformat(row["first_time"])
            last = datetime.fromisoformat(row["last_time"])
            duration_hours = (last - first).total_seconds() / 3600
            return {
                "first_time": row["first_time"],
                "last_time": row["last_time"],
                "count": row["count"],
                "duration_hours": round(duration_hours, 2)
            }
        return {"first_time": None, "last_time": None, "count": 0, "duration_hours": 0}
