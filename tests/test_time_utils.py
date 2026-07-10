"""time_utils 工具函数单元测试"""
import pytest
from utils.time_utils import format_duration, format_minutes


class TestFormatDuration:
    """format_duration 秒数格式化测试"""

    def test_short_hours_minutes(self):
        assert format_duration(5400) == "1h 30m"

    def test_short_minutes_only(self):
        assert format_duration(1800) == "30m"

    def test_short_zero(self):
        assert format_duration(0) == "0m"

    def test_short_none(self):
        assert format_duration(None) == "0m"

    def test_short_exact_hour(self):
        assert format_duration(3600) == "1h 0m"

    def test_long_hours_minutes(self):
        assert format_duration(5400, fmt="long") == "1小时30分钟"

    def test_long_minutes_only(self):
        assert format_duration(1800, fmt="long") == "30分钟"

    def test_long_zero(self):
        assert format_duration(0, fmt="long") == "0分钟"

    def test_long_none(self):
        assert format_duration(None, fmt="long") == "0分钟"

    def test_float_input(self):
        assert format_duration(5400.5) == "1h 30m"

    def test_large_hours(self):
        assert format_duration(36000) == "10h 0m"


class TestFormatMinutes:
    """format_minutes 分钟数格式化测试"""

    def test_short_hours_minutes(self):
        assert format_minutes(90) == "1h 30m"

    def test_short_minutes_only(self):
        assert format_minutes(30) == "30m"

    def test_short_zero(self):
        assert format_minutes(0) == "0m"

    def test_short_none(self):
        assert format_minutes(None) == "0m"

    def test_long_hours_minutes(self):
        assert format_minutes(90, fmt="long") == "1小时30分钟"

    def test_long_minutes_only(self):
        assert format_minutes(30, fmt="long") == "30分钟"

    def test_long_zero(self):
        assert format_minutes(0, fmt="long") == "0分钟"

    def test_float_input(self):
        assert format_minutes(90.5) == "1h 30m"