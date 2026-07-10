"""应用使用记录和键鼠操作的数据库操作"""

from datetime import datetime, timedelta
from typing import List, Dict


class AppUsageMixin:
    """应用使用记录和键鼠操作的数据库操作"""

    def save_app_usage(self, app_name: str, window_title: str,
                       start_time: str, end_time: str = None,
                       duration_seconds: float = None) -> int:
        """保存应用使用记录（线程安全）"""
        return self._execute("""
            INSERT INTO app_usage (app_name, window_title, start_time, end_time, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (app_name, window_title, start_time, end_time, duration_seconds))

    def update_app_usage(self, record_id: int, end_time: str, duration_seconds: float) -> None:
        """更新应用使用记录的结束时间（线程安全）"""
        self._execute("""
            UPDATE app_usage SET end_time = ?, duration_seconds = ?
            WHERE id = ?
        """, (end_time, duration_seconds, record_id))

    def split_app_usage(self, record_id: int, split_seconds: float) -> int:
        """拆分应用使用记录为两段（线程安全）
        
        Args:
            record_id: 原记录ID
            split_seconds: 从记录开始算起的拆分点秒数
            
        Returns:
            新创建的后半段记录ID
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            # 获取原记录
            cursor.execute("""
                SELECT id, app_name, window_title, start_time, end_time, 
                       duration_seconds, category, is_sensitive, date(start_time) as rec_date
                FROM app_usage WHERE id = ?
            """, (record_id,))
            row = cursor.fetchone()
            if not row:
                return -1
            
            original = dict(row)
            original_start = datetime.fromisoformat(original["start_time"])
            original_end = datetime.fromisoformat(original["end_time"])
            
            # 计算拆分点时间
            split_time = original_start + timedelta(seconds=split_seconds)
            
            # 确保拆分点在有效范围内
            if split_time <= original_start or split_time >= original_end:
                return -1
            
            # 前半段：更新原记录的end_time和duration
            front_duration = split_seconds
            cursor.execute("""
                UPDATE app_usage SET end_time = ?, duration_seconds = ?
                WHERE id = ?
            """, (split_time.isoformat(), front_duration, record_id))
            
            # 后半段：插入新记录
            back_duration = (original_end - split_time).total_seconds()
            cursor.execute("""
                INSERT INTO app_usage (app_name, window_title, start_time, end_time, 
                                       duration_seconds, category, is_sensitive)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (original["app_name"], original["window_title"],
                  split_time.isoformat(), original_end.isoformat(),
                  back_duration, original.get("category"), 
                  original.get("is_sensitive", 0)))
            new_id = cursor.lastrowid
            conn.commit()
            return new_id

    def merge_app_usage(self, record_id1: int, record_id2: int) -> bool:
        """合并两条相邻的应用使用记录（线程安全）
        
        Args:
            record_id1: 前一条记录ID（保留）
            record_id2: 后一条记录ID（删除）
            
        Returns:
            是否合并成功
        """
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            # 获取两条记录
            cursor.execute("""
                SELECT id, app_name, window_title, start_time, end_time, 
                       duration_seconds, category, is_sensitive
                FROM app_usage WHERE id IN (?, ?)
                ORDER BY start_time ASC
            """, (record_id1, record_id2))
            rows = cursor.fetchall()
            if len(rows) != 2:
                return False
            
            rec1, rec2 = dict(rows[0]), dict(rows[1])
            
            # 验证：必须是同一应用且时间连续
            if rec1["app_name"] != rec2["app_name"]:
                return False
            
            # 更新前一条记录的end_time和duration
            new_duration = rec1["duration_seconds"] + rec2["duration_seconds"]
            cursor.execute("""
                UPDATE app_usage SET end_time = ?, duration_seconds = ?
                WHERE id = ?
            """, (rec2["end_time"], new_duration, rec1["id"]))
            
            # 删除后一条记录
            cursor.execute("DELETE FROM app_usage WHERE id = ?", (rec2["id"],))
            conn.commit()
            return True

    def save_input_event(self, event_type: str, event_detail: str,
                         app_name: str = None, timestamp: str = None) -> int:
        """保存键鼠操作记录（线程安全）"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        return self._execute("""
            INSERT INTO input_events (event_type, event_detail, app_name, timestamp)
            VALUES (?, ?, ?, ?)
        """, (event_type, event_detail, app_name, timestamp))

    def save_input_events_batch(self, events: list) -> None:
        """批量保存键鼠操作记录（线程安全，单次事务）

        Args:
            events: [{'event_type': str, 'event_detail': str, 'app_name': str, 'timestamp': str}, ...]
        """
        if not events:
            return
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO input_events (event_type, event_detail, app_name, timestamp)
                VALUES (?, ?, ?, ?)
            """, [
                (e.get("event_type", ""), e.get("event_detail", ""),
                 e.get("app_name"), e.get("timestamp", ""))
                for e in events
            ])
            conn.commit()

    def get_app_usage_summary(self, date: str = None) -> List[Dict]:
        """获取应用使用统计汇总"""
        if date:
            return self._query_all("""
                SELECT app_name, SUM(duration_seconds) as total_seconds,
                       COUNT(*) as session_count
                FROM app_usage
                WHERE date(start_time) = ?
                GROUP BY app_name
                ORDER BY total_seconds DESC
            """, (date,))
        else:
            return self._query_all("""
                SELECT app_name, SUM(duration_seconds) as total_seconds,
                       COUNT(*) as session_count
                FROM app_usage
                GROUP BY app_name
                ORDER BY total_seconds DESC
            """)

    def get_day_total_seconds(self, date: str) -> float:
        """获取某天的总使用时长（秒）"""
        row = self._query_one("""
            SELECT COALESCE(SUM(duration_seconds), 0) as total
            FROM app_usage WHERE date(start_time) = ?
        """, (date,))
        return row["total"] if row else 0

    def get_day_app_count(self, date: str) -> int:
        """获取某天的活跃应用数"""
        row = self._query_one("""
            SELECT COUNT(DISTINCT app_name) as cnt
            FROM app_usage WHERE date(start_time) = ?
        """, (date,))
        return row["cnt"] if row else 0

    def get_heatmap_data(self, end_date: str) -> List[Dict]:
        """获取热力图数据（最近7天按小时统计）"""
        return self._query_all("""
            SELECT
                CAST(strftime('%H', start_time) AS INTEGER) as hour,
                CAST(strftime('%w', start_time) AS INTEGER) as day_of_week,
                SUM(duration_seconds) as total_sec
            FROM app_usage
            WHERE date(start_time) >= date(?, '-6 days')
            GROUP BY hour, day_of_week
        """, (end_date,))

    def get_timeline_data(self, date: str, limit: int = 200) -> List[Dict]:
        """获取时间轴数据"""
        return self._query_all("""
            SELECT id, app_name, window_title, start_time, duration_seconds
            FROM app_usage
            WHERE date(start_time) = ?
            ORDER BY start_time ASC
            LIMIT ?
        """, (date, limit))

    def get_7day_trend(self, end_date: str) -> List[Dict]:
        """获取7天趋势数据"""
        return self.get_n_day_trend(end_date, 7)

    def get_n_day_trend(self, end_date: str, days: int) -> List[Dict]:
        """获取N天趋势数据（单次查询优化，避免N+1查询）"""
        # 计算起始日期
        start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days - 1)).strftime("%Y-%m-%d")

        # 单次查询获取日期范围内所有数据
        rows = self._query_all("""
            SELECT date(start_time) as day, SUM(duration_seconds) as total
            FROM app_usage
            WHERE date(start_time) BETWEEN ? AND ?
            GROUP BY date(start_time)
        """, (start_date, end_date))

        # 构建日期到总时长的映射
        day_map = {r["day"]: r["total"] or 0 for r in rows}

        # 生成完整结果（包含无数据的日期）
        result = []
        for i in range(days - 1, -1, -1):
            target_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
            result.append({"days_ago": i, "total_seconds": day_map.get(target_date, 0)})
        return result

    def get_hourly_distribution(self, date: str) -> List[Dict]:
        """获取按小时分布数据"""
        return self._query_all("""
            SELECT CAST(strftime('%H', start_time) AS INTEGER) as hour,
                   SUM(duration_seconds) as total
            FROM app_usage
            WHERE date(start_time) = ?
            GROUP BY hour
            ORDER BY hour
        """, (date,))

    def get_app_usage_summary_range(self, start_date: str, end_date: str) -> List[Dict]:
        """获取日期范围内应用使用统计汇总"""
        return self._query_all("""
            SELECT app_name, SUM(duration_seconds) as total_seconds,
                   COUNT(*) as session_count
            FROM app_usage
            WHERE date(start_time) BETWEEN ? AND ?
            GROUP BY app_name
            ORDER BY total_seconds DESC
        """, (start_date, end_date))

    def get_range_total_seconds(self, start_date: str, end_date: str) -> float:
        """获取日期范围内总使用时长（秒）"""
        row = self._query_one("""
            SELECT COALESCE(SUM(duration_seconds), 0) as total
            FROM app_usage WHERE date(start_time) BETWEEN ? AND ?
        """, (start_date, end_date))
        return row["total"] if row else 0

    def get_input_event_count_range(self, start_date: str, end_date: str) -> Dict:
        """获取日期范围内键鼠操作统计"""
        rows = self._query_all("""
            SELECT event_type, COUNT(*) as count FROM input_events
            WHERE date(timestamp) BETWEEN ? AND ?
            GROUP BY event_type
        """, (start_date, end_date))
        return {row["event_type"]: row["count"] for row in rows}

    def get_input_event_count(self, date: str = None,
                              event_type: str = None) -> Dict:
        """获取键鼠操作统计"""
        conditions = []
        params = []
        if date:
            conditions.append("date(timestamp) = ?")
            params.append(date)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT event_type, COUNT(*) as count FROM input_events{where_clause} GROUP BY event_type"
        rows = self._query_all(sql, tuple(params) if params else None)
        return {row["event_type"]: row["count"] for row in rows}

    def search_app_usage(
        self,
        keyword: str,
        date_start: str = None,
        date_end: str = None,
        limit: int = 200,
    ) -> List[Dict]:
        """搜索应用使用记录（按应用名或窗口标题模糊匹配）

        Args:
            keyword: 搜索关键词
            date_start: 起始日期(含), 格式YYYY-MM-DD, None不限
            date_end: 结束日期(含), 格式YYYY-MM-DD, None不限
            limit: 最大返回条数

        Returns:
            匹配的记录列表, 每条含 id/app_name/window_title/start_time/end_time/duration_seconds
        """
        if not keyword or not keyword.strip():
            return []

        pattern = f"%{keyword.strip()}%"
        conditions = ["(app_name LIKE ? OR window_title LIKE ?)"]
        params = [pattern, pattern]

        if date_start:
            conditions.append("date(start_time) >= ?")
            params.append(date_start)
        if date_end:
            conditions.append("date(start_time) <= ?")
            params.append(date_end)

        params.append(limit)
        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT id, app_name, window_title, start_time, end_time, duration_seconds
            FROM app_usage
            WHERE {where_clause}
            ORDER BY start_time DESC
            LIMIT ?
        """
        try:
            return self._query_all(sql, tuple(params))
        except Exception as e:
            logger.error(f"搜索应用使用记录失败: {e}")
            return []
