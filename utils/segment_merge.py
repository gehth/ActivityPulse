"""时段合并工具 - 统一连续记录合并逻辑"""
from datetime import datetime
from typing import List, Dict


def merge_continuous_segments(
    records: List[Dict],
    gap_threshold_seconds: float = 300,
    min_duration_seconds: float = 0,
    accumulate_duration: bool = False,
    time_format: str = "%Y-%m-%d %H:%M:%S",
) -> List[Dict]:
    """合并连续时段记录

    将时间上连续（间隔 ≤ gap_threshold_seconds）的记录合并为时段。
    两条记录间隔小于阈值视为同一段，超过阈值则分段。

    Args:
        records: 记录列表，每条需含 'start_time' 和 'end_time' 键。
                 accumulate_duration=True 时还需 'duration_seconds' 键。
        gap_threshold_seconds: 间隔小于此秒数视为连续（默认300=5分钟）
        min_duration_seconds: 最小时长过滤（秒），0表示不过滤
        accumulate_duration: True=累加各记录的duration_seconds;
                             False=从合并后起止时间计算时长
        time_format: 时间字符串解析格式

    Returns:
        合并后的时段列表，每项含 start_time/end_time/duration_seconds/duration_minutes
    """
    if not records:
        return []

    segments = []
    cur_start = records[0]["start_time"]
    cur_end = records[0]["end_time"]
    cur_duration = (records[0].get("duration_seconds") or 0) if accumulate_duration else 0

    for rec in records[1:]:
        try:
            prev_end = datetime.strptime(cur_end, time_format)
            next_start = datetime.strptime(rec["start_time"], time_format)
            gap = (next_start - prev_end).total_seconds()
        except (ValueError, TypeError):
            gap = float('inf')

        if gap <= gap_threshold_seconds:
            cur_end = rec["end_time"] or cur_end
            if accumulate_duration:
                cur_duration += rec.get("duration_seconds") or 0
        else:
            dur = cur_duration if accumulate_duration else _calc_duration(
                cur_start, cur_end, time_format
            )
            if dur >= min_duration_seconds:
                segments.append(_make_segment(cur_start, cur_end, dur))
            cur_start = rec["start_time"]
            cur_end = rec["end_time"]
            cur_duration = (rec.get("duration_seconds") or 0) if accumulate_duration else 0

    # 最后一段
    dur = cur_duration if accumulate_duration else _calc_duration(
        cur_start, cur_end, time_format
    )
    if dur >= min_duration_seconds:
        segments.append(_make_segment(cur_start, cur_end, dur))

    return sorted(segments, key=lambda x: x["duration_seconds"], reverse=True)


def _calc_duration(start_time: str, end_time: str, time_format: str) -> float:
    """从起止时间字符串计算时长（秒）"""
    try:
        start_dt = datetime.strptime(start_time, time_format)
        end_dt = datetime.strptime(end_time, time_format)
        return (end_dt - start_dt).total_seconds()
    except (ValueError, TypeError):
        return 0


def _make_segment(start_time: str, end_time: str, duration_seconds: float) -> Dict:
    """创建时段字典"""
    return {
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration_seconds,
        "duration_minutes": duration_seconds / 60,
    }