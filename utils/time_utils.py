"""时长格式化工具 - 统一时长显示格式"""
from typing import Optional, Union


def format_duration(seconds: Optional[Union[int, float]], fmt: str = "short") -> str:
    """将秒数格式化为时长字符串

    Args:
        seconds: 秒数（int/float/None，None视为0）
        fmt: "short" → "1h 30m" / "long" → "1小时30分钟"

    Returns:
        格式化后的时长字符串
    """
    if seconds is None:
        seconds = 0
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if fmt == "short":
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    else:
        return f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"


def format_minutes(total_minutes: Optional[Union[int, float]], fmt: str = "short") -> str:
    """将分钟数格式化为时长字符串

    Args:
        total_minutes: 分钟数（int/float/None，None视为0）
        fmt: "short" → "1h 30m" / "long" → "1小时30分钟"

    Returns:
        格式化后的时长字符串
    """
    if total_minutes is None:
        total_minutes = 0
    total_minutes = int(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if fmt == "short":
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    else:
        return f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"