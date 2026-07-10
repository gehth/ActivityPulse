"""设置对话框 - 监控间隔/截图频率/数据保留等配置"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QCheckBox, QPushButton, QComboBox, QLineEdit,
    QGroupBox, QMessageBox, QFileDialog, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal

from database.db_manager import DatabaseManager
from gui.themes import get_colors, get_theme_qss, HoverButton
from utils.autostart import is_auto_start_enabled, enable_auto_start, disable_auto_start
from utils.backup_restore import create_backup, restore_backup, get_backup_info
from utils.global_hotkey import DEFAULT_HOTKEY_DISPLAY, DEFAULT_HOTKEYS, GlobalHotkeyManager


class BackupWorker(QThread):
    """备份工作线程"""
    progress = pyqtSignal(int, str)  # percent, message
    finished = pyqtSignal(str)       # backup_path
    error = pyqtSignal(str)          # error_message

    def __init__(self, output_dir: str) -> None:
        super().__init__()
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            path = create_backup(self.output_dir, self.progress.emit)
            self.finished.emit(path)
        except Exception as e:
            self.error.emit(str(e))


class RestoreWorker(QThread):
    """恢复工作线程"""
    progress = pyqtSignal(int, str)  # percent, message
    finished = pyqtSignal(dict)      # result dict
    error = pyqtSignal(str)          # error_message

    def __init__(self, backup_path: str) -> None:
        super().__init__()
        self.backup_path = backup_path

    def run(self) -> None:
        try:
            result = restore_backup(self.backup_path, self.progress.emit)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, db_manager: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self.db = db_manager
        self._is_dark = False
        self.setWindowTitle("设置")
        self.setMinimumWidth(480)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addWidget(self._create_monitor_group())
        layout.addWidget(self._create_screenshot_group())
        layout.addWidget(self._create_data_group())
        layout.addWidget(self._create_startup_group())
        layout.addWidget(self._create_reminder_group())
        layout.addWidget(self._create_report_group())
        layout.addWidget(self._create_hotkey_group())
        layout.addWidget(self._create_anomaly_group())

        # ===== 按钮 =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("btn_outline")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("保存设置")
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _create_monitor_group(self) -> None:
        """创建监控设置分组"""
        group = QGroupBox("监控设置")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        # 应用监控间隔
        row1 = QHBoxLayout()
        label1 = QLabel("应用检测间隔")
        label1.setObjectName("card_title")
        row1.addWidget(label1)
        row1.addStretch()
        self.spin_app_interval = QSpinBox()
        self.spin_app_interval.setRange(1, 60)
        self.spin_app_interval.setSuffix(" 秒")
        self.spin_app_interval.setFixedWidth(100)
        row1.addWidget(self.spin_app_interval)
        layout.addLayout(row1)

        desc1 = QLabel("每隔多少秒检测一次活动窗口（越小越精确，但更耗资源）")
        desc1.setObjectName("section_desc")
        layout.addWidget(desc1)

        # 键鼠保存间隔
        row2 = QHBoxLayout()
        label2 = QLabel("键鼠保存间隔")
        label2.setObjectName("card_title")
        row2.addWidget(label2)
        row2.addStretch()
        self.spin_input_interval = QSpinBox()
        self.spin_input_interval.setRange(1, 30)
        self.spin_input_interval.setSuffix(" 秒")
        self.spin_input_interval.setFixedWidth(100)
        row2.addWidget(self.spin_input_interval)
        layout.addLayout(row2)

        desc2 = QLabel("键鼠事件缓冲多久后批量写入数据库")
        desc2.setObjectName("section_desc")
        layout.addWidget(desc2)

        return group

    def _create_screenshot_group(self) -> None:
        """创建截图设置分组"""
        group = QGroupBox("截图设置")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        # 截图开关
        row3 = QHBoxLayout()
        self.cb_screenshot = QCheckBox("启用屏幕截图")
        self.cb_screenshot.setChecked(True)
        row3.addWidget(self.cb_screenshot)
        row3.addStretch()
        layout.addLayout(row3)

        # 截图间隔
        row4 = QHBoxLayout()
        label4 = QLabel("截图间隔")
        label4.setObjectName("card_title")
        row4.addWidget(label4)
        row4.addStretch()
        self.spin_screenshot_interval = QSpinBox()
        self.spin_screenshot_interval.setRange(10, 600)
        self.spin_screenshot_interval.setSuffix(" 秒")
        self.spin_screenshot_interval.setFixedWidth(100)
        row4.addWidget(self.spin_screenshot_interval)
        layout.addLayout(row4)

        desc4 = QLabel("每隔多少秒自动截取一次屏幕（仅在监控运行时）")
        desc4.setObjectName("section_desc")
        layout.addWidget(desc4)

        return group

    def _create_data_group(self) -> None:
        """创建数据管理分组"""
        group = QGroupBox("数据管理")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        # 数据保留天数
        row5 = QHBoxLayout()
        label5 = QLabel("数据保留天数")
        label5.setObjectName("card_title")
        row5.addWidget(label5)
        row5.addStretch()
        self.spin_retention = QSpinBox()
        self.spin_retention.setRange(7, 365)
        self.spin_retention.setSuffix(" 天")
        self.spin_retention.setFixedWidth(100)
        row5.addWidget(self.spin_retention)
        layout.addLayout(row5)

        desc5 = QLabel("超过保留期的数据将自动清理（0表示永久保留）")
        desc5.setObjectName("section_desc")
        layout.addWidget(desc5)

        # 清理按钮
        row6 = QHBoxLayout()
        btn_clean = HoverButton("🗑 立即清理过期数据")
        btn_clean.setObjectName("btn_outline")
        btn_clean.clicked.connect(self._clean_old_data)
        row6.addWidget(btn_clean)
        row6.addStretch()
        layout.addLayout(row6)

        # 备份/恢复按钮
        row_backup = QHBoxLayout()
        btn_backup = HoverButton("📦 备份数据")
        btn_backup.setObjectName("btn_outline")
        btn_backup.clicked.connect(self._on_backup)
        row_backup.addWidget(btn_backup)

        btn_restore = HoverButton("📥 恢复数据")
        btn_restore.setObjectName("btn_outline")
        btn_restore.clicked.connect(self._on_restore)
        row_backup.addWidget(btn_restore)
        row_backup.addStretch()
        layout.addLayout(row_backup)

        # 备份进度条
        self.backup_progress = QProgressBar()
        self.backup_progress.setRange(0, 100)
        self.backup_progress.setVisible(False)
        layout.addWidget(self.backup_progress)

        self.backup_status = QLabel("")
        self.backup_status.setObjectName("section_desc")
        self.backup_status.setVisible(False)
        layout.addWidget(self.backup_status)

        return group

    def _create_startup_group(self) -> None:
        """创建启动设置分组"""
        group = QGroupBox("启动设置")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        self.cb_autostart = QCheckBox("开机自动启动")
        layout.addWidget(self.cb_autostart)

        self.cb_minimize = QCheckBox("启动时最小化到托盘")
        layout.addWidget(self.cb_minimize)

        self.cb_auto_monitor = QCheckBox("启动时自动开始记录")
        self.cb_auto_monitor.setChecked(True)
        layout.addWidget(self.cb_auto_monitor)

        return group

    def _create_reminder_group(self) -> None:
        """创建提醒设置分组"""
        group = QGroupBox("提醒设置")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        row_sedentary = QHBoxLayout()
        label_sedentary = QLabel("久坐提醒间隔")
        label_sedentary.setObjectName("card_title")
        row_sedentary.addWidget(label_sedentary)
        row_sedentary.addStretch()
        self.spin_sedentary = QSpinBox()
        self.spin_sedentary.setRange(0, 240)
        self.spin_sedentary.setSuffix(" 分钟")
        self.spin_sedentary.setSpecialValueText("禁用")
        self.spin_sedentary.setFixedWidth(100)
        row_sedentary.addWidget(self.spin_sedentary)
        layout.addLayout(row_sedentary)

        desc_sedentary = QLabel("连续使用电脑超过此时间将弹出提醒（0表示禁用）")
        desc_sedentary.setObjectName("section_desc")
        layout.addWidget(desc_sedentary)

        return group

    def _create_report_group(self) -> None:
        """创建报告设置分组"""
        group = QGroupBox("报告设置")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        # 每日报告
        row_daily = QHBoxLayout()
        self.cb_daily_report = QCheckBox("每日报告")
        self.cb_daily_report.setChecked(True)
        self.cb_daily_report.setToolTip("每天在指定时间推送当日使用报告")
        row_daily.addWidget(self.cb_daily_report)
        row_daily.addStretch()
        label_daily_time = QLabel("推送时间")
        label_daily_time.setObjectName("card_title")
        row_daily.addWidget(label_daily_time)
        self.spin_daily_hour = QSpinBox()
        self.spin_daily_hour.setRange(6, 23)
        self.spin_daily_hour.setSuffix(" 时")
        self.spin_daily_hour.setFixedWidth(80)
        row_daily.addWidget(self.spin_daily_hour)
        layout.addLayout(row_daily)

        desc_daily = QLabel("每日定时通过系统通知推送当日使用报告")
        desc_daily.setObjectName("section_desc")
        layout.addWidget(desc_daily)

        # 每周报告
        row_weekly = QHBoxLayout()
        self.cb_weekly_report = QCheckBox("每周报告")
        self.cb_weekly_report.setChecked(True)
        self.cb_weekly_report.setToolTip("每周在指定时间推送本周使用报告")
        row_weekly.addWidget(self.cb_weekly_report)
        row_weekly.addStretch()
        label_weekly_day = QLabel("推送日")
        label_weekly_day.setObjectName("card_title")
        row_weekly.addWidget(label_weekly_day)
        self.combo_weekly_day = QComboBox()
        self.combo_weekly_day.addItems(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        self.combo_weekly_day.setCurrentIndex(4)  # 默认周五
        self.combo_weekly_day.setFixedWidth(70)
        row_weekly.addWidget(self.combo_weekly_day)
        label_weekly_time = QLabel("时间")
        label_weekly_time.setObjectName("card_title")
        row_weekly.addWidget(label_weekly_time)
        self.spin_weekly_hour = QSpinBox()
        self.spin_weekly_hour.setRange(6, 23)
        self.spin_weekly_hour.setSuffix(" 时")
        self.spin_weekly_hour.setFixedWidth(80)
        self.spin_weekly_hour.setValue(20)
        row_weekly.addWidget(self.spin_weekly_hour)
        layout.addLayout(row_weekly)

        desc_weekly = QLabel("每周定时通过系统通知推送本周使用报告汇总")
        desc_weekly.setObjectName("section_desc")
        layout.addWidget(desc_weekly)

        return group

    def _create_hotkey_group(self) -> None:
        """创建快捷键设置分组"""
        group = QGroupBox("快捷键设置")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        desc_hotkey = QLabel("全局快捷键可在任何应用中使用，需重启应用生效")
        desc_hotkey.setObjectName("section_desc")
        layout.addWidget(desc_hotkey)

        # 多组快捷键配置
        self._hotkey_inputs = {}  # {action: QLineEdit}
        for action, info in DEFAULT_HOTKEYS.items():
            row = QHBoxLayout()
            label = QLabel(info["label"])
            label.setObjectName("card_title")
            label.setFixedWidth(140)
            row.addWidget(label)

            input_field = QLineEdit()
            input_field.setPlaceholderText(f"例如: {info['display']}")
            input_field.setFixedWidth(160)
            input_field.setToolTip(f"格式: 修饰键+按键，如 {info['display']}")
            self._hotkey_inputs[action] = input_field
            row.addWidget(input_field)

            btn_reset = HoverButton("重置")
            btn_reset.setObjectName("btn_outline")
            btn_reset.setFixedHeight(28)
            btn_reset.setFixedWidth(50)
            btn_reset.clicked.connect(
                lambda checked, a=action, d=info["display"]: self._hotkey_inputs[a].setText(d)
            )
            row.addWidget(btn_reset)

            row.addStretch()
            layout.addLayout(row)

        # 兼容旧版：保留 input_hotkey 引用指向 toggle_window
        self.input_hotkey = self._hotkey_inputs.get("toggle_window")

        return group

    def _create_anomaly_group(self) -> None:
        """创建异常告警设置分组"""
        group = QGroupBox("异常告警设置")
        group.setObjectName("card")
        layout = QVBoxLayout(group)

        # 总开关
        row_a0 = QHBoxLayout()
        self.cb_anomaly_enabled = QCheckBox("启用异常行为检测")
        self.cb_anomaly_enabled.setChecked(True)
        row_a0.addWidget(self.cb_anomaly_enabled)
        row_a0.addStretch()
        layout.addLayout(row_a0)

        desc_a0 = QLabel("检测异常使用模式并在发现异常时发送告警通知")
        desc_a0.setObjectName("section_desc")
        layout.addWidget(desc_a0)

        # 连续使用阈值
        row_a1 = QHBoxLayout()
        label_a1 = QLabel("连续使用阈值")
        label_a1.setObjectName("card_title")
        row_a1.addWidget(label_a1)
        row_a1.addStretch()
        self.spin_continuous_minutes = QSpinBox()
        self.spin_continuous_minutes.setRange(30, 480)
        self.spin_continuous_minutes.setSuffix(" 分钟")
        self.spin_continuous_minutes.setFixedWidth(120)
        row_a1.addWidget(self.spin_continuous_minutes)
        layout.addLayout(row_a1)

        desc_a1 = QLabel("同一应用连续使用超过此时长将触发告警")
        desc_a1.setObjectName("section_desc")
        layout.addWidget(desc_a1)

        # 深夜检测
        row_a2 = QHBoxLayout()
        self.cb_late_night = QCheckBox("深夜异常活跃检测")
        self.cb_late_night.setChecked(True)
        row_a2.addWidget(self.cb_late_night)
        row_a2.addStretch()
        layout.addLayout(row_a2)

        row_a2b = QHBoxLayout()
        label_a2b = QLabel("深夜使用阈值")
        label_a2b.setObjectName("card_title")
        row_a2b.addWidget(label_a2b)
        row_a2b.addStretch()
        self.spin_late_night_minutes = QSpinBox()
        self.spin_late_night_minutes.setRange(10, 300)
        self.spin_late_night_minutes.setSuffix(" 分钟")
        self.spin_late_night_minutes.setFixedWidth(120)
        row_a2b.addWidget(self.spin_late_night_minutes)
        layout.addLayout(row_a2b)

        # 日使用偏离检测
        row_a3 = QHBoxLayout()
        self.cb_deviation = QCheckBox("日使用时长偏离检测")
        self.cb_deviation.setChecked(True)
        row_a3.addWidget(self.cb_deviation)
        row_a3.addStretch()
        layout.addLayout(row_a3)

        row_a3b = QHBoxLayout()
        label_a3b = QLabel("偏离倍数阈值")
        label_a3b.setObjectName("card_title")
        row_a3b.addWidget(label_a3b)
        row_a3b.addStretch()
        self.spin_deviation_factor = QSpinBox()
        self.spin_deviation_factor.setRange(12, 30)  # 1.2 ~ 3.0 (÷10)
        self.spin_deviation_factor.setSuffix("")
        self.spin_deviation_factor.setFixedWidth(80)
        self._deviation_label = QLabel("1.5 倍")
        self._deviation_label.setObjectName("card_title")
        self.spin_deviation_factor.valueChanged.connect(
            lambda v: self._deviation_label.setText(f"{v / 10:.1f} 倍")
        )
        row_a3b.addWidget(self.spin_deviation_factor)
        row_a3b.addWidget(self._deviation_label)
        row_a3b.addStretch()
        layout.addLayout(row_a3b)

        desc_a3 = QLabel("今日使用时长超过近7日均值的指定倍数时触发告警")
        desc_a3.setObjectName("section_desc")
        layout.addWidget(desc_a3)

        # 无休息阈值
        row_a4 = QHBoxLayout()
        label_a4 = QLabel("无休息连续使用阈值")
        label_a4.setObjectName("card_title")
        row_a4.addWidget(label_a4)
        row_a4.addStretch()
        self.spin_no_break_minutes = QSpinBox()
        self.spin_no_break_minutes.setRange(60, 720)
        self.spin_no_break_minutes.setSuffix(" 分钟")
        self.spin_no_break_minutes.setFixedWidth(120)
        row_a4.addWidget(self.spin_no_break_minutes)
        layout.addLayout(row_a4)

        desc_a4 = QLabel("连续使用电脑超过此时长（无10分钟以上休息）将触发告警")
        desc_a4.setObjectName("section_desc")
        layout.addWidget(desc_a4)

        # 检测间隔
        row_a5 = QHBoxLayout()
        label_a5 = QLabel("检测间隔")
        label_a5.setObjectName("card_title")
        row_a5.addWidget(label_a5)
        row_a5.addStretch()
        self.spin_anomaly_interval = QSpinBox()
        self.spin_anomaly_interval.setRange(1, 30)
        self.spin_anomaly_interval.setSuffix(" 分钟")
        self.spin_anomaly_interval.setFixedWidth(120)
        row_a5.addWidget(self.spin_anomaly_interval)
        layout.addLayout(row_a5)

        desc_a5 = QLabel("每隔多少分钟执行一次异常检测")
        desc_a5.setObjectName("section_desc")
        layout.addWidget(desc_a5)

        # 通知方式
        row_a6 = QHBoxLayout()
        self.cb_anomaly_notification = QCheckBox("托盘通知")
        self.cb_anomaly_notification.setChecked(True)
        row_a6.addWidget(self.cb_anomaly_notification)
        self.cb_anomaly_popup = QCheckBox("弹窗通知")
        self.cb_anomaly_popup.setChecked(False)
        row_a6.addWidget(self.cb_anomaly_popup)
        row_a6.addStretch()
        layout.addLayout(row_a6)

        return group

    def _load_settings(self) -> None:
        """从数据库加载设置"""
        self.spin_app_interval.setValue(int(self.db.get_config("app_interval", "5")))
        self.spin_input_interval.setValue(int(self.db.get_config("input_interval", "2")))
        self.spin_screenshot_interval.setValue(int(self.db.get_config("screenshot_interval", "60")))
        self.cb_screenshot.setChecked(self.db.get_config("screenshot_enabled", "1") == "1")
        self.spin_retention.setValue(int(self.db.get_config("retention_days", "90")))
        self.cb_autostart.setChecked(is_auto_start_enabled())
        self.cb_minimize.setChecked(self.db.get_config("start_minimized", "0") == "1")
        self.cb_auto_monitor.setChecked(self.db.get_config("auto_monitor", "1") == "1")
        self.spin_sedentary.setValue(int(self.db.get_config("sedentary_reminder_minutes", "60")))

        # 报告设置
        self.cb_daily_report.setChecked(self.db.get_config("daily_report_enabled", "1") == "1")
        self.spin_daily_hour.setValue(int(self.db.get_config("daily_report_hour", "18")))
        self.cb_weekly_report.setChecked(self.db.get_config("weekly_report_enabled", "1") == "1")
        self.combo_weekly_day.setCurrentIndex(int(self.db.get_config("weekly_report_weekday", "4")))
        self.spin_weekly_hour.setValue(int(self.db.get_config("weekly_report_hour", "20")))

        # 快捷键设置 - 多组快捷键加载
        for action, info in DEFAULT_HOTKEYS.items():
            config_key = f"hotkey_{action}_display"
            default_display = info["display"]
            display = self.db.get_config(config_key, default_display)
            if action in self._hotkey_inputs:
                self._hotkey_inputs[action].setText(display)

        # 异常告警设置加载
        self.cb_anomaly_enabled.setChecked(self.db.get_config("anomaly_enabled", "1") == "1")
        self.spin_continuous_minutes.setValue(int(self.db.get_config("anomaly_continuous_minutes", "120")))
        self.cb_late_night.setChecked(self.db.get_config("anomaly_late_night_enabled", "1") == "1")
        self.spin_late_night_minutes.setValue(int(self.db.get_config("anomaly_late_night_minutes", "60")))
        self.cb_deviation.setChecked(self.db.get_config("anomaly_deviation_enabled", "1") == "1")
        deviation_val = int(float(self.db.get_config("anomaly_deviation_factor", "1.5")) * 10)
        self.spin_deviation_factor.setValue(deviation_val)
        self.spin_no_break_minutes.setValue(int(self.db.get_config("anomaly_no_break_minutes", "240")))
        self.spin_anomaly_interval.setValue(int(self.db.get_config("anomaly_check_interval", "300")) // 60)
        self.cb_anomaly_notification.setChecked(self.db.get_config("anomaly_notification_enabled", "1") == "1")
        self.cb_anomaly_popup.setChecked(self.db.get_config("anomaly_popup_enabled", "0") == "1")

    def _save_settings(self) -> None:
        """保存设置到数据库"""
        self.db.save_config("app_interval", str(self.spin_app_interval.value()))
        self.db.save_config("input_interval", str(self.spin_input_interval.value()))
        self.db.save_config("screenshot_interval", str(self.spin_screenshot_interval.value()))
        self.db.save_config("screenshot_enabled", "1" if self.cb_screenshot.isChecked() else "0")
        self.db.save_config("retention_days", str(self.spin_retention.value()))
        # 开机自启 - 实际操作注册表
        if self.cb_autostart.isChecked():
            enable_auto_start()
        else:
            disable_auto_start()
        self.db.save_config("autostart", "1" if self.cb_autostart.isChecked() else "0")
        self.db.save_config("start_minimized", "1" if self.cb_minimize.isChecked() else "0")
        self.db.save_config("auto_monitor", "1" if self.cb_auto_monitor.isChecked() else "0")
        self.db.save_config("sedentary_reminder_minutes", str(self.spin_sedentary.value()))

        # 报告设置
        self.db.save_config("daily_report_enabled", "1" if self.cb_daily_report.isChecked() else "0")
        self.db.save_config("daily_report_hour", str(self.spin_daily_hour.value()))
        self.db.save_config("weekly_report_enabled", "1" if self.cb_weekly_report.isChecked() else "0")
        self.db.save_config("weekly_report_weekday", str(self.combo_weekly_day.currentIndex()))
        self.db.save_config("weekly_report_hour", str(self.spin_weekly_hour.value()))

        # 快捷键设置 - 多组快捷键保存
        for action, info in DEFAULT_HOTKEYS.items():
            if action not in self._hotkey_inputs:
                continue
            hotkey_display = self._hotkey_inputs[action].text().strip()
            if hotkey_display:
                hotkey_str = GlobalHotkeyManager.display_to_hotkey(hotkey_display)
                if GlobalHotkeyManager.validate_hotkey(hotkey_str):
                    self.db.save_config(f"hotkey_{action}_display", hotkey_display)
                    self.db.save_config(f"hotkey_{action}", hotkey_str)
                else:
                    QMessageBox.warning(self, "快捷键格式错误",
                        f"\"{info['label']}\" 的快捷键 \"{hotkey_display}\" 格式无效。\n"
                        f"请使用格式如: Ctrl+Shift+H、Alt+Q 等")
                    return
            else:
                # 空值表示禁用该快捷键
                self.db.save_config(f"hotkey_{action}_display", "")
                self.db.save_config(f"hotkey_{action}", "")

        # 异常告警设置保存
        self.db.save_config("anomaly_enabled", "1" if self.cb_anomaly_enabled.isChecked() else "0")
        self.db.save_config("anomaly_continuous_minutes", str(self.spin_continuous_minutes.value()))
        self.db.save_config("anomaly_late_night_enabled", "1" if self.cb_late_night.isChecked() else "0")
        self.db.save_config("anomaly_late_night_minutes", str(self.spin_late_night_minutes.value()))
        self.db.save_config("anomaly_deviation_enabled", "1" if self.cb_deviation.isChecked() else "0")
        self.db.save_config("anomaly_deviation_factor", str(self.spin_deviation_factor.value() / 10))
        self.db.save_config("anomaly_no_break_minutes", str(self.spin_no_break_minutes.value()))
        self.db.save_config("anomaly_check_interval", str(self.spin_anomaly_interval.value() * 60))
        self.db.save_config("anomaly_notification_enabled", "1" if self.cb_anomaly_notification.isChecked() else "0")
        self.db.save_config("anomaly_popup_enabled", "1" if self.cb_anomaly_popup.isChecked() else "0")

        QMessageBox.information(self, "设置", "设置已保存，部分设置将在重启后生效")
        self.accept()

    def _clean_old_data(self) -> None:
        """清理过期数据"""
        retention_days = self.spin_retention.value()
        if retention_days == 0:
            QMessageBox.warning(self, "提示", "当前设置为永久保留数据，无法清理")
            return

        reply = QMessageBox.question(
            self, "确认清理",
            f"将清理 {retention_days} 天前的所有数据，此操作不可撤销。\n确定继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                stats = self.db.cleanup_old_data(retention_days)
                total = sum(stats.values())
                QMessageBox.information(self, "清理完成", f"已清理过期数据：共 {total} 条记录")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清理失败: {e}")

    def _on_backup(self) -> None:
        """创建数据备份"""
        output_dir = QFileDialog.getExistingDirectory(self, "选择备份保存位置", os.path.expanduser("~"))
        if not output_dir:
            return

        # 显示进度
        self.backup_progress.setVisible(True)
        self.backup_status.setVisible(True)
        self.backup_status.setText("正在备份...")
        self.backup_progress.setValue(0)

        # 禁用按钮防止重复操作
        self.findChild(QPushButton, "btn_outline").setEnabled(False)

        self._backup_worker = BackupWorker(output_dir)
        self._backup_worker.progress.connect(self._on_backup_progress)
        self._backup_worker.finished.connect(self._on_backup_done)
        self._backup_worker.error.connect(self._on_backup_error)
        self._backup_worker.start()

    def _on_backup_progress(self, percent: int, message: str) -> None:
        """备份进度更新"""
        self.backup_progress.setValue(percent)
        self.backup_status.setText(message)

    def _on_backup_done(self, backup_path: str) -> None:
        """备份完成"""
        self.backup_progress.setValue(100)
        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        self.backup_status.setText(f"备份完成！文件: {os.path.basename(backup_path)} ({size_mb:.1f}MB)")
        QMessageBox.information(self, "备份完成",
            f"数据已成功备份到：\n{backup_path}\n\n大小: {size_mb:.1f}MB")

    def _on_backup_error(self, error_msg: str) -> None:
        """备份失败"""
        self.backup_progress.setVisible(False)
        self.backup_status.setText(f"备份失败: {error_msg}")
        QMessageBox.critical(self, "备份失败", f"备份数据时出错：\n{error_msg}")

    def _on_restore(self) -> None:
        """从备份恢复数据"""
        backup_path, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", os.path.expanduser("~"),
            "备份文件 (*.zip);;所有文件 (*.*)")
        if not backup_path:
            return

        # 显示备份信息
        info = get_backup_info(backup_path)
        if not info or not info["has_db"]:
            QMessageBox.warning(self, "无效备份", "选择的文件不是有效的行为记录备份")
            return

        # 确认恢复
        reply = QMessageBox.warning(
            self, "确认恢复",
            f"将从备份恢复数据，当前数据将被替换！\n\n"
            f"备份信息：\n"
            f"  大小: {info['size_mb']:.1f}MB\n"
            f"  截图数量: {info['screenshot_count']}\n"
            f"  日期: {info['date']}\n\n"
            f"恢复后需要重启应用才能生效。确定继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 显示进度
        self.backup_progress.setVisible(True)
        self.backup_status.setVisible(True)
        self.backup_status.setText("正在恢复...")
        self.backup_progress.setValue(0)

        self._restore_worker = RestoreWorker(backup_path)
        self._restore_worker.progress.connect(self._on_backup_progress)
        self._restore_worker.finished.connect(self._on_restore_done)
        self._restore_worker.error.connect(self._on_backup_error)
        self._restore_worker.start()

    def _on_restore_done(self, result: dict) -> None:
        """恢复完成"""
        self.backup_progress.setValue(100)
        db_status = "✅ 数据库已恢复" if result["db_restored"] else "❌ 数据库恢复失败"
        ss_status = f"✅ 截图已恢复 ({result['screenshots_restored']}个)" if result["screenshots_restored"] > 0 else "无截图"
        self.backup_status.setText(f"恢复完成！{db_status}，{ss_status}")
        QMessageBox.information(self, "恢复完成",
            f"数据恢复完成！\n\n"
            f"数据库: {'已恢复' if result['db_restored'] else '失败'}\n"
            f"截图: {result['screenshots_restored']} 个已恢复\n\n"
            f"请重启应用以加载恢复的数据。")

    def _on_reset_hotkey(self) -> None:
        """重置快捷键为默认值"""
        self.input_hotkey.setText(DEFAULT_HOTKEY_DISPLAY)

    def set_theme(self, is_dark: bool) -> None:
        self._is_dark = is_dark
        colors = get_colors("dark" if is_dark else "light")
        
        # 应用主题QSS到对话框
        qss = get_theme_qss("dark" if is_dark else "light")
        self.setStyleSheet(qss)
        
        # 设置对话框背景色（确保覆盖）
        bg_color = colors["bg_primary"]
        self.setStyleSheet(self.styleSheet() + f"""
            QDialog {{
                background-color: {bg_color};
            }}
        """)