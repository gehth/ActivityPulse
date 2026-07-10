"""自动报告生成模块 - 每日/每周自动生成行为报告并通过系统通知推送"""

from datetime import datetime, timedelta
from utils.time_utils import format_duration


def generate_daily_report(db, date: str = None) -> dict:
    """生成每日报告数据
    
    Args:
        db: DatabaseManager实例
        date: 日期字符串(yyyy-MM-dd)，默认为今天
    
    Returns:
        报告数据字典，包含概览、分类统计、Top应用、操作详情等
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # 基础数据
    total_seconds = db.get_day_total_seconds(date)
    app_summary = db.get_app_usage_summary(date)
    app_count = db.get_day_app_count(date)
    input_counts = db.get_input_event_count(date)
    hourly_dist = db.get_hourly_distribution(date)
    
    # 键鼠操作统计
    key_count = input_counts.get("keypress", 0) if isinstance(input_counts, dict) else 0
    click_count = input_counts.get("click", 0) if isinstance(input_counts, dict) else 0
    scroll_count = input_counts.get("scroll", 0) if isinstance(input_counts, dict) else 0
    total_input = key_count + click_count + scroll_count
    
    # 分类统计
    from utils.category_stats import compute_category_stats
    cat_stats, cat_names, _ = compute_category_stats(app_summary)
    peak_hour = None
    peak_seconds = 0
    for h in hourly_dist:
        if (h.get("total") or 0) > peak_seconds:
            peak_seconds = h.get("total") or 0
            peak_hour = h.get("hour")
    
    # 格式化时长
    total_formatted = format_duration(total_seconds, fmt="long")
    
    return {
        "type": "daily",
        "date": date,
        "total_seconds": total_seconds,
        "total_formatted": total_formatted,
        "app_count": app_count,
        "input_total": total_input,
        "key_count": key_count,
        "click_count": click_count,
        "scroll_count": scroll_count,
        "app_summary": app_summary[:10],  # Top 10
        "cat_stats": cat_stats,
        "cat_names": cat_names,
        "peak_hour": peak_hour,
        "peak_seconds": peak_seconds,
    }


def generate_weekly_report(db, end_date: str = None) -> dict:
    """生成每周报告数据
    
    Args:
        db: DatabaseManager实例
        end_date: 结束日期(yyyy-MM-dd)，默认为今天
    
    Returns:
        周报数据字典，包含每日趋势、周汇总、分类对比等
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=6)).strftime("%Y-%m-%d")
    
    # 基础数据
    total_seconds = db.get_range_total_seconds(start_date, end_date)
    app_summary = db.get_app_usage_summary_range(start_date, end_date)
    input_counts = db.get_input_event_count_range(start_date, end_date)
    trend_data = db.get_7day_trend(end_date)
    
    # 键鼠操作统计
    key_count = input_counts.get("keypress", 0) if isinstance(input_counts, dict) else 0
    click_count = input_counts.get("click", 0) if isinstance(input_counts, dict) else 0
    scroll_count = input_counts.get("scroll", 0) if isinstance(input_counts, dict) else 0
    total_input = key_count + click_count + scroll_count
    
    # 分类统计
    from utils.category_stats import compute_category_stats
    cat_stats, cat_names, _ = compute_category_stats(app_summary)
    
    # 每日数据与汇总
    daily_data = _build_daily_data(trend_data, end_date)
    active_days = sum(1 for d in daily_data if d["seconds"] > 0)
    avg_seconds = total_seconds / max(active_days, 1)
    most_active = max(daily_data, key=lambda x: x["seconds"]) if daily_data else None
    
    return {
        "type": "weekly",
        "start_date": start_date,
        "end_date": end_date,
        "total_seconds": total_seconds,
        "total_formatted": format_duration(total_seconds, fmt="long"),
        "active_days": active_days,
        "avg_formatted": _format_duration(avg_seconds),
        "app_count": len(app_summary),
        "input_total": total_input,
        "key_count": key_count,
        "click_count": click_count,
        "scroll_count": scroll_count,
        "app_summary": app_summary[:15],  # Top 15
        "cat_stats": cat_stats,
        "cat_names": cat_names,
        "daily_data": daily_data,
        "most_active": most_active,
    }


def _build_daily_data(trend_data, end_date):
    """从趋势数据构建每日详情列表"""
    daily_data = []
    for item in trend_data:
        days_ago = item.get("days_ago", 0)
        d = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        secs = item.get("total_seconds", 0) or 0
        daily_data.append({
            "date": d,
            "seconds": secs,
            "formatted": _format_duration(secs),
            "weekday": _get_weekday(d),
        })
    return daily_data


def format_daily_notification(report: dict) -> tuple:
    """格式化每日报告为通知文本
    
    Returns:
        (title, message) 元组
    """
    title = f"📊 每日报告 - {report['date']}"
    
    lines = [
        f"⏱ 专注时长: {report['total_formatted']}",
        f"📱 活跃应用: {report['app_count']}个",
        f"🖱 操作次数: {report['input_total']:,}次",
    ]
    
    # 最活跃时段
    if report["peak_hour"] is not None:
        lines.append(f"🔥 最活跃: {report['peak_hour']}:00-{report['peak_hour']+1}:00")
    
    # Top 3 应用
    if report["app_summary"]:
        lines.append("")
        lines.append("🏆 Top应用:")
        for i, app in enumerate(report["app_summary"][:3]):
            secs = app.get("total_seconds", 0) or 0
            name = app.get("app_name", "Unknown")
            lines.append(f"  {i+1}. {name} ({_format_duration(secs)})")
    
    # 分类占比
    if report["cat_stats"]:
        sorted_cats = sorted(report["cat_stats"].items(), key=lambda x: -x[1]["seconds"])
        top_cat_key, top_cat_data = sorted_cats[0]
        top_cat_name = report["cat_names"].get(top_cat_key, top_cat_key)
        pct = top_cat_data["seconds"] / max(report["total_seconds"], 1) * 100
        lines.append(f"📋 主要分类: {top_cat_name} ({pct:.0f}%)")
    
    message = "\n".join(lines)
    return title, message


def format_weekly_notification(report: dict) -> tuple:
    """格式化每周报告为通知文本
    
    Returns:
        (title, message) 元组
    """
    title = f"📈 周报 - {report['start_date']} ~ {report['end_date']}"
    
    lines = [
        f"⏱ 总时长: {report['total_formatted']}",
        f"📅 活跃天数: {report['active_days']}/7天",
        f"📊 日均时长: {report['avg_formatted']}",
        f"📱 使用应用: {report['app_count']}个",
        f"🖱 操作次数: {report['input_total']:,}次",
    ]
    
    # 最活跃的一天
    if report["most_active"]:
        ma = report["most_active"]
        lines.append(f"🔥 最活跃: {ma['date']} ({ma['weekday']}, {ma['formatted']})")
    
    # Top 5 应用
    if report["app_summary"]:
        lines.append("")
        lines.append("🏆 Top应用:")
        for i, app in enumerate(report["app_summary"][:5]):
            secs = app.get("total_seconds", 0) or 0
            name = app.get("app_name", "Unknown")
            lines.append(f"  {i+1}. {name} ({_format_duration(secs)})")
    
    # 分类占比
    if report["cat_stats"]:
        sorted_cats = sorted(report["cat_stats"].items(), key=lambda x: -x[1]["seconds"])
        top_cat_key, top_cat_data = sorted_cats[0]
        top_cat_name = report["cat_names"].get(top_cat_key, top_cat_key)
        pct = top_cat_data["seconds"] / max(report["total_seconds"], 1) * 100
        lines.append(f"📋 主要分类: {top_cat_name} ({pct:.0f}%)")
    
    message = "\n".join(lines)
    return title, message


def should_send_daily_report(db, current_hour: int = None) -> bool:
    """检查是否应该发送每日报告
    
    Args:
        db: DatabaseManager实例
        current_hour: 当前小时(0-23)，默认取当前时间
    
    Returns:
        是否应该发送
    """
    if current_hour is None:
        current_hour = datetime.now().hour
    
    # 检查是否启用
    enabled = db.get_config("daily_report_enabled", "1") == "1"
    if not enabled:
        return False
    
    # 检查发送时间（默认18点）
    report_hour = int(db.get_config("daily_report_hour", "18"))
    if current_hour != report_hour:
        return False
    
    # 检查今天是否已发送
    today = datetime.now().strftime("%Y-%m-%d")
    last_sent = db.get_config("daily_report_last_sent", "")
    if last_sent == today:
        return False
    
    return True


def should_send_weekly_report(db, current_weekday: int = None, current_hour: int = None) -> bool:
    """检查是否应该发送每周报告
    
    Args:
        db: DatabaseManager实例
        current_weekday: 当前星期几(0=周一...6=周日)，默认取当前时间
        current_hour: 当前小时(0-23)，默认取当前时间
    
    Returns:
        是否应该发送
    """
    now = datetime.now()
    if current_weekday is None:
        current_weekday = now.weekday()  # 0=Monday
    if current_hour is None:
        current_hour = now.hour
    
    # 检查是否启用
    enabled = db.get_config("weekly_report_enabled", "1") == "1"
    if not enabled:
        return False
    
    # 检查发送时间（默认周五20点）
    report_weekday = int(db.get_config("weekly_report_weekday", "4"))  # 4=Friday
    report_hour = int(db.get_config("weekly_report_hour", "20"))
    
    if current_weekday != report_weekday or current_hour != report_hour:
        return False
    
    # 检查本周是否已发送
    # 计算当前周的周一日期
    monday = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    last_sent = db.get_config("weekly_report_last_sent", "")
    if last_sent == monday:
        return False
    
    return True


def mark_daily_report_sent(db):
    """标记今日每日报告已发送"""
    today = datetime.now().strftime("%Y-%m-%d")
    db.save_config("daily_report_last_sent", today)


def mark_weekly_report_sent(db):
    """标记本周周报已发送"""
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    db.save_config("weekly_report_last_sent", monday)


def _format_duration(seconds: float) -> str:
    """格式化时长"""
    return format_duration(seconds, fmt="long")


def _get_weekday(date_str: str) -> str:
    """获取星期几中文名"""
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return weekdays[d.weekday()]