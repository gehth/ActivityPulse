"""活动标签的数据库操作"""

from typing import List, Dict


class ActivityTagMixin:
    """活动标签的数据库操作"""

    _ACTIVITY_TAG_COLUMNS = {"tag", "note", "start_time", "end_time", "color"}


    def add_activity_tag(self, date: str, tag: str, note: str = "",
                         start_time: str = None, end_time: str = None,
                         color: str = "#3B82F6") -> int:
        """添加活动标签（线程安全）"""
        return self._execute("""
            INSERT INTO activity_tags (date, tag, note, start_time, end_time, color)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, tag, note, start_time, end_time, color))

    def get_activity_tags(self, date: str) -> List[Dict]:
        """获取某天的活动标签"""
        return self._query_all("""
            SELECT id, date, tag, note, start_time, end_time, color
            FROM activity_tags WHERE date = ?
            ORDER BY start_time ASC
        """, (date,))

    def delete_activity_tag(self, tag_id: int) -> None:
        """删除活动标签（线程安全）"""
        self._execute("DELETE FROM activity_tags WHERE id = ?", (tag_id,))

    def update_activity_tag(self, tag_id: int, tag: str = None, note: str = None,
                            start_time: str = None, end_time: str = None,
                            color: str = None) -> None:
        """更新活动标签（线程安全）"""
        # 使用白名单构建更新字段，避免f-string拼接SQL
        field_map = {
            "tag": tag, "note": note, "start_time": start_time,
            "end_time": end_time, "color": color,
        }
        updates = []
        params = []
        for col, val in field_map.items():
            if val is not None and col in self._ACTIVITY_TAG_COLUMNS:
                updates.append(f"{col} = ?")
                params.append(val)
        if updates:
            params.append(tag_id)
            set_clause = ", ".join(updates)
            self._execute(
                f"UPDATE activity_tags SET {set_clause} WHERE id = ?", tuple(params)
            )
