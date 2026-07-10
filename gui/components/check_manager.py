"""检测管理器 - 久坐提醒、应用限制、异常行为检测、自动报告"""

from datetime import datetime, timedelta

from PyQt5.QtWidgets import QSystemTrayIcon
from PyQt5.QtCore import QDate

from utils.auto_report import (
    generate_daily_report, generate_weekly_report,
    format_daily_notification, format_weekly_notification,
    should_send_daily_report, should_send_weekly_report,
    mark_daily_report_sent, mark_weekly_report_sent
)


class CheckManager:
    """检测管理器

    管理久坐提醒、应用限制检查、异常行为检测和自动报告。
    """

    def __init__(self, db, tray_icon, app_monitor, input_monitor, callbacks: dict):
        """
        Args:
            db: DatabaseManager实例
            tray_icon: QSystemTrayIcon实例
            app_monitor: AppMonitor实例
            input_monitor: InputMonitor实例
            callbacks: 回调函数字典，支持以下键：
                - is_monitoring: 返回是否正在监控的函数
                - show_status: 显示状态栏消息 (message: str)
                - show_sedentary_dialog: 显示久坐提醒对话框 (minutes: int, snooze_callback)
                - show_anomaly_alerts: 显示异常告警中心
                - update_anomaly_badge: 更新告警badge
                - is_dark: 返回是否深色主题的函数
        """
        self._db = db
        self._tray_icon = tray_icon
        self._app_monitor = app_monitor
        self._input_monitor = input_monitor
        self._callbacks = callbacks

        # 状态
        self._last_active_time = datetime.now()
        self._sedentary_notified = False
        self._snooze_until = None
        self._limit_notified_apps = set()
        self._limit_notified_date = None
        self._anomaly_notified_ids = set()

        # 异常检测器
        from utils.anomaly_detector import AnomalyDetector
        self._anomaly_detector = AnomalyDetector(db)

    def check_sedentary(self):
        """久坐提醒检查 - 每分钟调用，支持暂停15分钟"""
        is_monitoring = self._callbacks.get("is_monitoring")
        if is_monitoring and not is_monitoring():
            return

        # 读取久坐提醒间隔（分钟），默认60分钟
        sedentary_minutes = int(self._db.get_config("sedentary_reminder_minutes", "60"))
        if sedentary_minutes <= 0:
            return  # 设为0则禁用

        # 暂停检查
        if self._snooze_until:
            if datetime.now() < self._snooze_until:
                return  # 还在暂停期内

        # 检查是否有键鼠活动（通过input_monitor的缓冲区判断）
        now = datetime.now()
        if self._input_monitor and hasattr(self._input_monitor, '_last_event_time'):
            last_event = self._input_monitor._last_event_time
            if last_event:
                self._last_active_time = last_event

        # 计算不活动时间
        idle_minutes = (now - self._last_active_time).total_seconds() / 60

        if idle_minutes < 5:  # 5分钟内有活动，说明在使用电脑
            # 计算连续使用时间
            today = QDate.currentDate().toString("yyyy-MM-dd")
            total_seconds = self._db.get_day_total_seconds(today)
            continuous_minutes = total_seconds / 60

            if continuous_minutes >= sedentary_minutes and not self._sedentary_notified:
                self._sedentary_notified = True

                # 系统托盘通知（后台提醒）
                self._tray_icon.showMessage(
                    "久坐提醒",
                    f"您已连续使用电脑 {int(continuous_minutes)} 分钟，请注意休息！",
                    QSystemTrayIcon.Warning,
                    5000
                )

                # 弹出详细提醒对话框
                show_dialog = self._callbacks.get("show_sedentary_dialog")
                if show_dialog:
                    show_dialog(int(continuous_minutes), self._on_sedentary_snooze)
        else:
            # 用户不在电脑前，重置提醒状态
            self._sedentary_notified = False

    def _on_sedentary_snooze(self):
        """久坐提醒暂停15分钟"""
        self._snooze_until = datetime.now() + timedelta(minutes=15)
        show_status = self._callbacks.get("show_status")
        if show_status:
            show_status("久坐提醒已暂停15分钟")

    def check_app_limits(self):
        """检查应用使用限制，超限时发送通知"""
        try:
            # 每日重置已通知记录
            today = QDate.currentDate().toString("yyyy-MM-dd")
            if self._limit_notified_date != today:
                self._limit_notified_apps = set()
                self._limit_notified_date = today

            # 获取所有已超限的应用
            exceeded = self._db.get_exceeded_limits(today)
            for item in exceeded:
                app_name = item["app_name"]
                if app_name not in self._limit_notified_apps:
                    self._limit_notified_apps.add(app_name)
                    limit_min = item["limit_minutes"]
                    used_min = item["used_minutes"]

                    # 系统托盘通知
                    self._tray_icon.showMessage(
                        "⏱ 使用限制提醒",
                        f"\"{app_name}\" 已达到每日限制！\n"
                        f"限制: {limit_min}分钟 | 已使用: {used_min}分钟",
                        QSystemTrayIcon.Warning, 6000
                    )

                    # 状态栏提示
                    show_status = self._callbacks.get("show_status")
                    if show_status:
                        show_status(f"⚠ {app_name} 已超过每日使用限制 ({limit_min}分钟)")
        except Exception as e:
            print(f"应用限制检查失败: {e}")

    def check_anomaly(self):
        """定时检查异常行为并通知"""
        try:
            # 执行异常检测
            new_alerts = self._anomaly_detector.detect_all()
            if not new_alerts:
                return

            # 通知用户新告警
            notification_enabled = self._db.get_config("anomaly_notification_enabled", "1")
            popup_enabled = self._db.get_config("anomaly_popup_enabled", "0")

            for alert in new_alerts:
                alert_id = alert.get("id")
                if alert_id in self._anomaly_notified_ids:
                    continue
                self._anomaly_notified_ids.add(alert_id)

                # 托盘通知
                if notification_enabled == "1" and self._tray_icon:
                    severity = alert.get("severity", "warning")
                    icon = QSystemTrayIcon.Critical if severity == "critical" else QSystemTrayIcon.Warning
                    self._tray_icon.showMessage(
                        "🚨 异常行为告警",
                        alert.get("title", "检测到异常使用模式"),
                        icon, 5000
                    )

                # 状态栏提示
                show_status = self._callbacks.get("show_status")
                if show_status:
                    show_status(f"🚨 {alert.get('title', '异常告警')}")

            # 弹窗通知（合并显示）
            if popup_enabled == "1" and new_alerts:
                show_alerts = self._callbacks.get("show_anomaly_alerts")
                if show_alerts:
                    show_alerts()

        except Exception as e:
            print(f"异常行为检测失败: {e}")

    def check_auto_report(self):
        """检查并发送自动报告（每日/每周）"""
        try:
            # 检查每日报告
            if should_send_daily_report(self._db):
                report = generate_daily_report(self._db)
                if report["total_seconds"] > 0:  # 有数据才发送
                    title, message = format_daily_notification(report)
                    self._tray_icon.showMessage(
                        title, message,
                        QSystemTrayIcon.Information, 8000
                    )
                    mark_daily_report_sent(self._db)
                    show_status = self._callbacks.get("show_status")
                    if show_status:
                        show_status(f"每日报告已推送 - {report['date']}")

            # 检查每周报告
            if should_send_weekly_report(self._db):
                report = generate_weekly_report(self._db)
                if report["total_seconds"] > 0:  # 有数据才发送
                    title, message = format_weekly_notification(report)
                    self._tray_icon.showMessage(
                        title, message,
                        QSystemTrayIcon.Information, 10000
                    )
                    mark_weekly_report_sent(self._db)
                    show_status = self._callbacks.get("show_status")
                    if show_status:
                        show_status(f"周报已推送 - {report['start_date']} ~ {report['end_date']}")
        except Exception as e:
            print(f"自动报告检查失败: {e}")