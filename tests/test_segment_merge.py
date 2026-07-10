"""segment_merge 时段合并工具单元测试"""
import pytest
from utils.segment_merge import merge_continuous_segments


def _rec(start, end, duration=None):
    """快速构造测试记录"""
    rec = {"start_time": start, "end_time": end}
    if duration is not None:
        rec["duration_seconds"] = duration
    return rec


FMT = "%Y-%m-%d %H:%M:%S"


class TestMergeContinuousSegments:
    """merge_continuous_segments 核心逻辑测试"""

    def test_empty_records(self):
        assert merge_continuous_segments([]) == []

    def test_single_record_calculate_mode(self):
        """单条记录，从起止时间计算时长"""
        records = [_rec("2025-01-01 10:00:00", "2025-01-01 10:30:00")]
        result = merge_continuous_segments(records, accumulate_duration=False)
        assert len(result) == 1
        assert result[0]["duration_seconds"] == 1800
        assert result[0]["duration_minutes"] == 30

    def test_single_record_accumulate_mode(self):
        """单条记录，累加时长模式"""
        records = [_rec("2025-01-01 10:00:00", "2025-01-01 10:30:00", duration=1800)]
        result = merge_continuous_segments(records, accumulate_duration=True)
        assert len(result) == 1
        assert result[0]["duration_seconds"] == 1800

    def test_continuous_records_merged(self):
        """间隔<=阈值的记录应合并"""
        records = [
            _rec("2025-01-01 10:00:00", "2025-01-01 10:25:00"),
            _rec("2025-01-01 10:28:00", "2025-01-01 10:50:00"),  # 间隔3分钟 < 5分钟
        ]
        result = merge_continuous_segments(records, gap_threshold_seconds=300, accumulate_duration=False)
        assert len(result) == 1
        assert result[0]["start_time"] == "2025-01-01 10:00:00"
        assert result[0]["end_time"] == "2025-01-01 10:50:00"
        assert result[0]["duration_seconds"] == 3000  # 50分钟

    def test_gap_exceeds_threshold_split(self):
        """间隔>阈值的记录应分段"""
        records = [
            _rec("2025-01-01 10:00:00", "2025-01-01 10:25:00"),
            _rec("2025-01-01 10:35:00", "2025-01-01 10:50:00"),  # 间隔10分钟 > 5分钟
        ]
        result = merge_continuous_segments(records, gap_threshold_seconds=300, accumulate_duration=False)
        assert len(result) == 2

    def test_accumulate_duration_mode(self):
        """累加模式：时长来自各记录的duration_seconds之和"""
        records = [
            _rec("2025-01-01 10:00:00", "2025-01-01 10:25:00", duration=1500),
            _rec("2025-01-01 10:28:00", "2025-01-01 10:50:00", duration=1200),
        ]
        result = merge_continuous_segments(records, gap_threshold_seconds=300, accumulate_duration=True)
        assert len(result) == 1
        assert result[0]["duration_seconds"] == 2700  # 1500+1200

    def test_min_duration_filter(self):
        """最小时长过滤"""
        records = [
            _rec("2025-01-01 10:00:00", "2025-01-01 10:01:00"),  # 60秒
            _rec("2025-01-01 10:10:00", "2025-01-01 10:30:00"),  # 1200秒
        ]
        result = merge_continuous_segments(
            records, gap_threshold_seconds=300, min_duration_seconds=120, accumulate_duration=False
        )
        # 60秒 < 120秒，被过滤；1200秒 >= 120秒，保留
        assert len(result) == 1
        assert result[0]["duration_seconds"] == 1200

    def test_sorted_by_duration_desc(self):
        """结果按时长降序排列"""
        records = [
            _rec("2025-01-01 08:00:00", "2025-01-01 08:10:00"),  # 600秒
            _rec("2025-01-01 10:00:00", "2025-01-01 10:30:00"),  # 1800秒
        ]
        result = merge_continuous_segments(records, gap_threshold_seconds=0, accumulate_duration=False)
        assert len(result) == 2
        assert result[0]["duration_seconds"] > result[1]["duration_seconds"]

    def test_invalid_time_format_handled(self):
        """无效时间格式不崩溃，gap计算失败时视为间隔无穷大"""
        records = [
            _rec("2025-01-01 10:00:00", "invalid_end"),  # end_time无效
            _rec("2025-01-01 10:35:00", "2025-01-01 10:50:00"),
        ]
        result = merge_continuous_segments(records, accumulate_duration=False)
        # cur_end无效导致gap计算失败→间隔无穷大→分成两段
        assert len(result) == 2

    def test_three_records_two_continuous(self):
        """三条记录：前两条连续，第三条间隔大"""
        records = [
            _rec("2025-01-01 09:00:00", "2025-01-01 09:25:00"),
            _rec("2025-01-01 09:28:00", "2025-01-01 09:50:00"),  # 连续
            _rec("2025-01-01 11:00:00", "2025-01-01 11:30:00"),  # 间隔大
        ]
        result = merge_continuous_segments(records, gap_threshold_seconds=300, accumulate_duration=False)
        assert len(result) == 2