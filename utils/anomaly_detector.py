"""异常行为检测引擎 - 检测使用模式异常并生成告警

检测规则：
1. 连续使用超时：同一应用连续使用超过阈值
2. 深夜异常活跃：深夜时段（23:00-6:00）使用超过阈值
3. 日使用时长偏离：今日使用时长显著偏离近7日均值
4. 长时间无休息：连续使用电脑超过阈值无长间隔
"""

import logging
from datetime import datetime
from typing import List, Dict
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

# 默认检测配置
DEFAULT_ANOMALY_CONFIG = {
    "anomaly_enabled": "1",                      # 总开关
    "anomaly_continuous_minutes": "120",          # 连续使用阈值（分钟）
    "anomaly_late_night_enabled": "1",            # 深夜检测开关
    "anomaly_late_night_minutes": "60",           # 深夜使用阈值（分钟）
    "anomaly_late_night_start": "23",             # 深夜起始小时
    "anomaly_late_night_end": "6",                # 深夜结束小时
    "anomaly_deviation_enabled": "1",             # 日使用偏离检测开关
    "anomaly_deviation_factor": "1.5",            # 偏离倍数（均值×倍数）
    "anomaly_no_break_minutes": "240",            # 无休息阈值（分钟）
    "anomaly_check_interval": "300",              # 检测间隔（秒）
    "anomaly_alert_cooldown_hours": "1.0",        # 同类型告警冷却时间（小时）
    "anomaly_notification_enabled": "1",          # 托盘通知开关
    "anomaly_popup_enabled": "0",                 # 弹窗通知开关（默认关闭）
}


class AnomalyDetector:
    """异常行为检测引擎"""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def _get_config(self, key: str) -> str:
        """获取配置值，带默认值"""
        default = DEFAULT_ANOMALY_CONFIG.get(key, "")
        return self.db.get_config(key, default)

    def _is_enabled(self, key: str) -> bool:
        """检查配置是否启用"""
        return self._get_config(key) == "1"

    def detect_all(self) -> List[Dict]:
        """执行所有异常检测，返回告警列表"""
        if not self._is_enabled("anomaly_enabled"):
            return []

        alerts = []
        try:
            alerts.extend(self.detect_continuous_use())
            alerts.extend(self.detect_late_night())
            alerts.extend(self.detect_daily_deviation())
            alerts.extend(self.detect_no_break())
        except Exception as e:
            logger.error(f"异常检测失败: {e}")

        # 保存告警到数据库
        saved = []
        for alert in alerts:
            try:
                alert_id = self.db.save_anomaly_alert(
                    alert_type=alert["alert_type"],
                    title=alert["title"],
                    description=alert.get("description"),
                    app_name=alert.get("app_name"),
                    severity=alert.get("severity", "warning"),
                    threshold_value=alert.get("threshold_value"),
                    actual_value=alert.get("actual_value"),
                )
                alert["id"] = alert_id
                saved.append(alert)
                logger.info(f"异常告警已保存: [{alert['alert_type']}] {alert['title']}")
            except Exception as e:
                logger.error(f"保存告警失败: {e}")

        return saved

    def detect_continuous_use(self) -> List[Dict]:
        """检测连续使用同一应用超时"""
        if not self._is_enabled("anomaly_enabled"):
            return []

        threshold_minutes = float(self._get_config("anomaly_continuous_minutes") or 120)
        cooldown_hours = float(self._get_config("anomaly_alert_cooldown_hours") or 1.0)

        continuous_records = self.db.get_continuous_app_usage(min_minutes=threshold_minutes)
        alerts = []

        for rec in continuous_records:
            # 检查冷却期
            if self.db.check_recent_alert_exists(
                "continuous_use", hours=cooldown_hours, app_name=rec["app_name"]
            ):
                continue

            duration_min = rec["duration_minutes"]
            severity = "critical" if duration_min >= threshold_minutes * 1.5 else "warning"

            alerts.append({
                "alert_type": "continuous_use",
                "severity": severity,
                "title": f"连续使用 {rec['app_name']} 超时",
                "description": (
                    f"已连续使用 {rec['app_name']} {int(duration_min)} 分钟，"
                    f"超过阈值 {int(threshold_minutes)} 分钟。"
                    f"时段: {rec['start_time']} ~ {rec['end_time']}"
                ),
                "app_name": rec["app_name"],
                "threshold_value": threshold_minutes,
                "actual_value": duration_min,
            })

        return alerts

    def detect_late_night(self) -> List[Dict]:
        """检测深夜异常活跃"""
        if not self._is_enabled("anomaly_late_night_enabled"):
            return []

        threshold_minutes = float(self._get_config("anomaly_late_night_minutes") or 60)
        start_hour = int(self._get_config("anomaly_late_night_start") or 23)
        end_hour = int(self._get_config("anomaly_late_night_end") or 6)
        cooldown_hours = float(self._get_config("anomaly_alert_cooldown_hours") or 1.0)

        late_records = self.db.get_late_night_usage(start_hour=start_hour, end_hour=end_hour)

        if not late_records:
            return []

        # 计算深夜总使用时长
        total_minutes = sum(r["total_minutes"] for r in late_records)
        if total_minutes < threshold_minutes:
            return []

        # 检查冷却期
        if self.db.check_recent_alert_exists("late_night", hours=cooldown_hours):
            return []

        top_apps = ", ".join(f"{r['app_name']}({int(r['total_minutes'])}分钟)" for r in late_records[:3])
        severity = "critical" if total_minutes >= threshold_minutes * 2 else "warning"

        return [{
            "alert_type": "late_night",
            "severity": severity,
            "title": "深夜异常活跃",
            "description": (
                f"深夜({start_hour}:00-{end_hour}:00)累计使用 {int(total_minutes)} 分钟，"
                f"超过阈值 {int(threshold_minutes)} 分钟。主要应用: {top_apps}"
            ),
            "threshold_value": threshold_minutes,
            "actual_value": total_minutes,
        }]

    def detect_daily_deviation(self) -> List[Dict]:
        """检测日使用时长偏离日常模式"""
        if not self._is_enabled("anomaly_deviation_enabled"):
            return []

        factor = float(self._get_config("anomaly_deviation_factor") or 1.5)
        cooldown_hours = float(self._get_config("anomaly_alert_cooldown_hours") or 1.0)

        # 获取最近7天数据
        recent = self.db.get_recent_daily_totals(days=7)
        if len(recent) < 3:  # 至少3天数据才有统计意义
            return []

        today_str = datetime.now().strftime("%Y-%m-%d")
        today_data = next((d for d in recent if d["date"] == today_str), None)
        if not today_data:
            return []

        today_minutes = today_data["total_minutes"]
        # 排除今天计算均值
        other_days = [d["total_minutes"] for d in recent if d["date"] != today_str]
        if not other_days:
            return []

        avg_minutes = sum(other_days) / len(other_days)
        if avg_minutes < 30:  # 均值太低不检测
            return []

        if today_minutes <= avg_minutes * factor:
            return []

        # 检查冷却期
        if self.db.check_recent_alert_exists("daily_deviation", hours=cooldown_hours):
            return []

        deviation_pct = (today_minutes / avg_minutes - 1) * 100
        severity = "critical" if today_minutes >= avg_minutes * 2 else "warning"

        return [{
            "alert_type": "daily_deviation",
            "severity": severity,
            "title": "今日使用时长异常偏高",
            "description": (
                f"今日已使用 {int(today_minutes)} 分钟，是近7日均值 "
                f"{int(avg_minutes)} 分钟的 {today_minutes / avg_minutes:.1f} 倍"
                f"（偏离 +{deviation_pct:.0f}%）。"
            ),
            "threshold_value": avg_minutes * factor,
            "actual_value": today_minutes,
        }]

    def detect_no_break(self) -> List[Dict]:
        """检测长时间无休息连续使用电脑"""
        if not self._is_enabled("anomaly_enabled"):
            return []

        threshold_minutes = float(self._get_config("anomaly_no_break_minutes") or 240)
        cooldown_hours = float(self._get_config("anomaly_alert_cooldown_hours") or 1.0)

        segments = self.db.get_continuous_computer_usage(gap_minutes=10)

        alerts = []
        for seg in segments:
            if seg["duration_minutes"] < threshold_minutes:
                continue
            # 检查冷却期
            if self.db.check_recent_alert_exists("no_break", hours=cooldown_hours):
                continue

            duration_min = seg["duration_minutes"]
            severity = "critical" if duration_min >= threshold_minutes * 1.5 else "warning"

            alerts.append({
                "alert_type": "no_break",
                "severity": severity,
                "title": "长时间连续使用电脑",
                "description": (
                    f"已连续使用电脑 {int(duration_min)} 分钟（无超过10分钟的休息），"
                    f"超过阈值 {int(threshold_minutes)} 分钟。"
                    f"时段: {seg['start_time']} ~ {seg['end_time']}"
                ),
                "threshold_value": threshold_minutes,
                "actual_value": duration_min,
            })

        return alerts