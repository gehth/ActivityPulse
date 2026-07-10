"""空闲时段检测的数据库操作"""

from datetime import datetime
from typing import List, Dict


class IdleMixin:
    """空闲时段检测的数据库操作"""

    def get_idle_periods(self, date: str, min_gap_minutes: int = 10) -> List[Dict]:
        """获取某天的空闲时段（记录间隔超过min_gap_minutes的时段）

        Returns:
            list of dict: [{"start": "HH:MM", "end": "HH:MM", "duration_minutes": int}]
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT start_time, end_time
            FROM app_usage
            WHERE date(start_time) = ?
            ORDER BY start_time ASC
        """, (date,))
        rows = cursor.fetchall()

        if len(rows) < 2:
            return []

        idle_periods = []
        for i in range(len(rows) - 1):
            try:
                end_time = rows[i]["end_time"]
                next_start = rows[i + 1]["start_time"]

                # 解析时间
                if isinstance(end_time, str):
                    end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                else:
                    end_dt = end_time

                if isinstance(next_start, str):
                    next_dt = datetime.strptime(next_start, "%Y-%m-%d %H:%M:%S")
                else:
                    next_dt = next_start

                gap_seconds = (next_dt - end_dt).total_seconds()
                gap_minutes = gap_seconds / 60

                if gap_minutes >= min_gap_minutes:
                    idle_periods.append({
                        "start": end_dt.strftime("%H:%M"),
                        "end": next_dt.strftime("%H:%M"),
                        "duration_minutes": int(gap_minutes),
                        "start_hour": end_dt.hour + end_dt.minute / 60,
                        "duration_hours": gap_minutes / 60
                    })
            except (ValueError, TypeError):
                continue

        return idle_periods

    def get_idle_summary(self, date: str, min_gap_minutes: int = 10) -> Dict:
        """获取某天的空闲时间汇总

        Returns:
            {"total_idle_minutes": int, "idle_count": int, "longest_idle_minutes": int,
             "idle_periods": list}
        """
        periods = self.get_idle_periods(date, min_gap_minutes)
        if not periods:
            return {"total_idle_minutes": 0, "idle_count": 0, "longest_idle_minutes": 0,
                    "idle_periods": []}

        total = sum(p["duration_minutes"] for p in periods)
        longest = max(p["duration_minutes"] for p in periods)

        return {
            "total_idle_minutes": total,
            "idle_count": len(periods),
            "longest_idle_minutes": longest,
            "idle_periods": periods
        }
