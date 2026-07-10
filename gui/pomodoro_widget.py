"""专注模式/番茄钟 - 浮动计时器组件

功能：
- 工作/短休息/长休息三种模式
- 圆形进度条倒计时
- 完成提醒（系统通知+声音）
- 今日完成次数统计
- 可配置时长（存储到数据库）
"""

from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSpinBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QConicalGradient

from database.db_manager import DatabaseManager


# 默认配置
DEFAULT_WORK_MINUTES = 25
DEFAULT_SHORT_BREAK_MINUTES = 5
DEFAULT_LONG_BREAK_MINUTES = 15
DEFAULT_LONG_BREAK_INTERVAL = 4  # 每完成4个番茄钟后长休息


class PomodoroWidget(QWidget):
    """番茄钟浮动组件"""

    # 信号：番茄钟完成
    pomodoro_completed = pyqtSignal(int)  # 今日完成数
    # 信号：模式切换
    mode_changed = pyqtSignal(str)  # "work" / "short_break" / "long_break"

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._is_dark = False

        # 从数据库读取配置
        self.work_minutes = int(self.db.get_config("pomodoro_work", str(DEFAULT_WORK_MINUTES)))
        self.short_break_minutes = int(self.db.get_config("pomodoro_short_break", str(DEFAULT_SHORT_BREAK_MINUTES)))
        self.long_break_minutes = int(self.db.get_config("pomodoro_long_break", str(DEFAULT_LONG_BREAK_MINUTES)))
        self.long_break_interval = int(self.db.get_config("pomodoro_interval", str(DEFAULT_LONG_BREAK_INTERVAL)))

        # 状态
        self._mode = "work"  # work / short_break / long_break
        self._running = False
        self._seconds_left = self.work_minutes * 60
        self._total_seconds = self.work_minutes * 60
        self._completed_count = self._load_today_count()
        self._cycle_count = 0  # 当前周期内完成的番茄钟数

        # 定时器
        self._timer = QTimer(self)
        self._timer.setInterval(1000)  # 1秒
        self._timer.timeout.connect(self._tick)

        self._setup_ui()
        self._update_display()

    def _load_today_count(self) -> int:
        """从数据库加载今日完成次数"""
        try:
            count = self.db.get_config(f"pomodoro_count_{datetime.now().strftime('%Y-%m-%d')}", "0")
            return int(count)
        except Exception:
            return 0

    def _save_today_count(self, count: int):
        """保存今日完成次数"""
        try:
            self.db.save_config(f"pomodoro_count_{datetime.now().strftime('%Y-%m-%d')}", str(count))
        except Exception:
            pass

    def _setup_ui(self):
        self.setFixedSize(280, 380)
        self.setObjectName("pomodoro_widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignCenter)

        # 标题
        self.title_label = QLabel("🍅 专注模式")
        self.title_label.setObjectName("pomodoro_title")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        layout.addLayout(self._create_mode_bar())
        layout.addWidget(self._create_progress_area(), 0, Qt.AlignCenter)
        layout.addWidget(self.count_label)
        layout.addLayout(self._create_controls())
        layout.addWidget(self.btn_settings)
        self._create_settings_panel()
        self.settings_frame.hide()
        layout.addWidget(self.settings_frame)

        self._apply_styles()

    def _create_mode_bar(self):
        """创建模式选择按钮组"""
        mode_bar = QHBoxLayout()
        mode_bar.setSpacing(4)

        self.btn_work = QPushButton("专注")
        self.btn_work.setObjectName("mode_btn_active")
        self.btn_work.setFixedHeight(28)
        self.btn_work.clicked.connect(lambda: self._switch_mode("work"))
        mode_bar.addWidget(self.btn_work)

        self.btn_short = QPushButton("短休息")
        self.btn_short.setObjectName("mode_btn")
        self.btn_short.setFixedHeight(28)
        self.btn_short.clicked.connect(lambda: self._switch_mode("short_break"))
        mode_bar.addWidget(self.btn_short)

        self.btn_long = QPushButton("长休息")
        self.btn_long.setObjectName("mode_btn")
        self.btn_long.setFixedHeight(28)
        self.btn_long.clicked.connect(lambda: self._switch_mode("long_break"))
        mode_bar.addWidget(self.btn_long)

        return mode_bar

    def _create_progress_area(self):
        """创建圆形进度区域"""
        self.progress_widget = QWidget()
        self.progress_widget.setFixedSize(180, 180)
        self.progress_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 倒计时文字（叠加在进度条上）
        self.time_label = QLabel("25:00")
        self.time_label.setObjectName("pomodoro_time")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setGeometry(0, 0, 180, 180)
        self.time_label.setParent(self.progress_widget)

        # 完成计数
        self.count_label = QLabel(f"今日完成: {self._completed_count} 🍅")
        self.count_label.setObjectName("pomodoro_count")
        self.count_label.setAlignment(Qt.AlignCenter)

        return self.progress_widget

    def _create_controls(self):
        """创建控制按钮"""
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)

        self.btn_start = QPushButton("▶ 开始")
        self.btn_start.setObjectName("pomodoro_start")
        self.btn_start.setFixedHeight(36)
        self.btn_start.clicked.connect(self._toggle_run)
        ctrl_bar.addWidget(self.btn_start)

        self.btn_reset = QPushButton("↻ 重置")
        self.btn_reset.setObjectName("pomodoro_reset")
        self.btn_reset.setFixedHeight(36)
        self.btn_reset.clicked.connect(self._reset)
        ctrl_bar.addWidget(self.btn_reset)

        # 设置按钮
        self.btn_settings = QPushButton("⚙ 设置时长")
        self.btn_settings.setObjectName("pomodoro_settings_btn")
        self.btn_settings.setFixedHeight(28)
        self.btn_settings.clicked.connect(self._toggle_settings)

        return ctrl_bar

    def _create_settings_panel(self):
        """创建设置面板"""
        self.settings_frame = QFrame()
        self.settings_frame.setObjectName("pomodoro_settings")
        settings_layout = QVBoxLayout(self.settings_frame)
        settings_layout.setContentsMargins(0, 4, 0, 4)
        settings_layout.setSpacing(4)

        # 工作时长
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("专注(分):"))
        self.spin_work = QSpinBox()
        self.spin_work.setRange(1, 120)
        self.spin_work.setValue(self.work_minutes)
        row1.addWidget(self.spin_work)
        settings_layout.addLayout(row1)

        # 短休息
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("短休息(分):"))
        self.spin_short = QSpinBox()
        self.spin_short.setRange(1, 30)
        self.spin_short.setValue(self.short_break_minutes)
        row2.addWidget(self.spin_short)
        settings_layout.addLayout(row2)

        # 长休息
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("长休息(分):"))
        self.spin_long = QSpinBox()
        self.spin_long.setRange(1, 60)
        self.spin_long.setValue(self.long_break_minutes)
        row3.addWidget(self.spin_long)
        settings_layout.addLayout(row3)

        # 保存按钮
        btn_save = QPushButton("保存")
        btn_save.setObjectName("pomodoro_save")
        btn_save.clicked.connect(self._save_settings)
        settings_layout.addWidget(btn_save)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(self._build_qss("light"))

    def _apply_dark_styles(self):
        """应用暗色主题样式"""
        self.setStyleSheet(self._build_qss("dark"))

    def _build_qss(self, theme: str) -> str:
        """构建番茄钟QSS样式"""
        c = {
            "light": {
                "bg": "#ffffff", "title_color": "#1e293b", "mode_bg": "#f1f5f9",
                "mode_color": "#64748b", "mode_border": "#e2e8f0", "mode_hover": "#e2e8f0",
                "time_color": "#1e293b", "count_color": "#64748b",
                "reset_bg": "#f1f5f9", "reset_color": "#475569", "reset_border": "#e2e8f0", "reset_hover": "#e2e8f0",
                "settings_btn_color": "#94a3b8", "settings_btn_hover": "#64748b",
                "settings_bg": "#f8fafc", "settings_border": "#e2e8f0",
                "spin_bg": "white", "spin_color": "#1e293b", "spin_border": "#e2e8f0",
                "label_color": "#475569",
            },
            "dark": {
                "bg": "#1e293b", "title_color": "#e2e8f0", "mode_bg": "#334155",
                "mode_color": "#94a3b8", "mode_border": "#475569", "mode_hover": "#475569",
                "time_color": "#e2e8f0", "count_color": "#94a3b8",
                "reset_bg": "#334155", "reset_color": "#94a3b8", "reset_border": "#475569", "reset_hover": "#475569",
                "settings_btn_color": "#64748b", "settings_btn_hover": "#94a3b8",
                "settings_bg": "#0f172a", "settings_border": "#334155",
                "spin_bg": "#0f172a", "spin_color": "#e2e8f0", "spin_border": "#334155",
                "label_color": "#94a3b8",
            },
        }[theme]

        return f"""
            #pomodoro_widget {{
                background-color: {c['bg']};
                border-radius: 12px;
            }}
            #pomodoro_title {{
                font-size: 18px;
                font-weight: bold;
                color: {c['title_color']};
                padding: 4px;
            }}
            #mode_btn {{
                background-color: {c['mode_bg']};
                color: {c['mode_color']};
                border: 1px solid {c['mode_border']};
                border-radius: 6px;
                font-size: 12px;
                padding: 4px 12px;
            }}
            #mode_btn:hover {{
                background-color: {c['mode_hover']};
            }}
            #mode_btn_active {{
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 12px;
            }}
            #pomodoro_time {{
                font-size: 42px;
                font-weight: bold;
                color: {c['time_color']};
                background: transparent;
            }}
            #pomodoro_count {{
                font-size: 14px;
                color: {c['count_color']};
                padding: 2px;
            }}
            #pomodoro_start {{
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 20px;
            }}
            #pomodoro_start:hover {{
                background-color: #dc2626;
            }}
            #pomodoro_reset {{
                background-color: {c['reset_bg']};
                color: {c['reset_color']};
                border: 1px solid {c['reset_border']};
                border-radius: 8px;
                font-size: 14px;
                padding: 8px 16px;
            }}
            #pomodoro_reset:hover {{
                background-color: {c['reset_hover']};
            }}
            #pomodoro_settings_btn {{
                background: transparent;
                color: {c['settings_btn_color']};
                border: none;
                font-size: 12px;
                padding: 4px;
            }}
            #pomodoro_settings_btn:hover {{
                color: {c['settings_btn_hover']};
            }}
            #pomodoro_settings {{
                background-color: {c['settings_bg']};
                border: 1px solid {c['settings_border']};
                border-radius: 8px;
                padding: 8px;
            }}
            #pomodoro_save {{
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                padding: 6px;
            }}
            #pomodoro_save:hover {{
                background-color: #2563eb;
            }}
            QSpinBox {{
                padding: 4px 8px;
                border: 1px solid {c['spin_border']};
                border-radius: 4px;
                background: {c['spin_bg']};
                color: {c['spin_color']};
                font-size: 13px;
            }}
            QLabel {{
                color: {c['label_color']};
                font-size: 13px;
            }}
        """

    def _switch_mode(self, mode: str):
        """切换模式"""
        if self._running:
            self._timer.stop()
            self._running = False

        self._mode = mode
        self._update_mode_buttons()
        self._reset_timer_for_mode()
        self._update_display()
        self.mode_changed.emit(mode)

    def _update_mode_buttons(self):
        """更新模式按钮样式"""
        active_map = {
            "work": self.btn_work,
            "short_break": self.btn_short,
            "long_break": self.btn_long,
        }
        for m, btn in active_map.items():
            btn.setObjectName("mode_btn_active" if m == self._mode else "mode_btn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _reset_timer_for_mode(self):
        """根据模式重置计时器"""
        if self._mode == "work":
            self._total_seconds = self.work_minutes * 60
        elif self._mode == "short_break":
            self._total_seconds = self.short_break_minutes * 60
        else:
            self._total_seconds = self.long_break_minutes * 60
        self._seconds_left = self._total_seconds

    def _toggle_run(self):
        """开始/暂停"""
        if self._running:
            self._timer.stop()
            self._running = False
            self.btn_start.setText("▶ 继续")
        else:
            self._timer.start()
            self._running = True
            self.btn_start.setText("⏸ 暂停")

    def _reset(self):
        """重置计时器"""
        self._timer.stop()
        self._running = False
        self._reset_timer_for_mode()
        self._update_display()
        self.btn_start.setText("▶ 开始")

    def _tick(self):
        """每秒更新"""
        if self._seconds_left > 0:
            self._seconds_left -= 1
            self._update_display()
        else:
            self._timer.stop()
            self._running = False
            self._on_complete()

    def _on_complete(self):
        """计时完成"""
        if self._mode == "work":
            # 完成一个番茄钟
            self._completed_count += 1
            self._cycle_count += 1
            self._save_today_count(self._completed_count)
            self.count_label.setText(f"今日完成: {self._completed_count} 🍅")
            self.pomodoro_completed.emit(self._completed_count)

            # 播放提示音
            self._play_sound()

            # 判断是否需要长休息
            if self._cycle_count >= self.long_break_interval:
                self._cycle_count = 0
                self._switch_mode("long_break")
            else:
                self._switch_mode("short_break")

            # 显示系统通知
            self._show_notification(
                "🍅 番茄钟完成！",
                f"恭喜完成第 {self._completed_count} 个番茄钟，休息一下吧！"
            )
        else:
            # 休息结束
            self._play_sound()
            self._switch_mode("work")
            self._show_notification(
                "☕ 休息结束",
                "休息完毕，开始新的专注吧！"
            )

        self.btn_start.setText("▶ 开始")

    def _play_sound(self):
        """播放提示音"""
        try:
            from PyQt5.QtWidgets import QApplication
            QApplication.beep()
        except Exception:
            pass

    def _show_notification(self, title: str, message: str):
        """显示系统通知"""
        try:
            # 尝试使用系统托盘通知
            main_window = self.window()
            if hasattr(main_window, 'tray_icon') and main_window.tray_icon.isVisible():
                main_window.tray_icon.showMessage(title, message)
        except Exception:
            pass

    def _update_display(self):
        """更新显示"""
        minutes = self._seconds_left // 60
        seconds = self._seconds_left % 60
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        # 触发进度条重绘
        self.progress_widget.update()

    def _toggle_settings(self):
        """切换设置面板"""
        if self.settings_frame.isVisible():
            self.settings_frame.hide()
            self.btn_settings.setText("⚙ 设置时长")
        else:
            self.settings_frame.show()
            self.btn_settings.setText("⚙ 收起设置")
            # 调整窗口大小以容纳设置
            self.setFixedSize(280, 520)

    def _save_settings(self):
        """保存设置"""
        self.work_minutes = self.spin_work.value()
        self.short_break_minutes = self.spin_short.value()
        self.long_break_minutes = self.spin_long.value()

        # 保存到数据库
        self.db.save_config("pomodoro_work", str(self.work_minutes))
        self.db.save_config("pomodoro_short_break", str(self.short_break_minutes))
        self.db.save_config("pomodoro_long_break", str(self.long_break_minutes))

        # 重置当前计时器
        self._reset()
        self.settings_frame.hide()
        self.btn_settings.setText("⚙ 设置时长")
        self.setFixedSize(280, 380)

    @property
    def completed_count(self) -> int:
        return self._completed_count

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_running(self) -> bool:
        return self._running

    # ── 绘制圆形进度条 ──

    def paintEvent(self, event):
        """绘制圆形进度条"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 进度条区域
        w = self.progress_widget.width()
        h = self.progress_widget.height()
        x = self.progress_widget.x()
        y = self.progress_widget.y() + 30  # 偏移以在标题下方

        # 背景圆环
        pen_width = 8
        margin = pen_width // 2 + 2
        rect = QRectF(x + margin, y + margin, w - margin * 2, h - margin * 2)

        # 背景轨道
        bg_color = QColor("#e2e8f0") if not self._is_dark else QColor("#334155")
        painter.setPen(QPen(bg_color, pen_width, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)

        # 进度弧
        if self._total_seconds > 0:
            progress = self._seconds_left / self._total_seconds
        else:
            progress = 0

        # 颜色根据模式变化
        if self._mode == "work":
            arc_color = QColor("#ef4444")  # 红色-专注
        elif self._mode == "short_break":
            arc_color = QColor("#22c55e")  # 绿色-短休息
        else:
            arc_color = QColor("#3b82f6")  # 蓝色-长休息

        # 渐变效果
        gradient = QConicalGradient(rect.center(), 90)
        gradient.setColorAt(0, arc_color)
        gradient.setColorAt(progress, arc_color.lighter(120))
        gradient.setColorAt(progress + 0.001, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(0, 0, 0, 0))

        painter.setPen(QPen(gradient, pen_width, Qt.SolidLine, Qt.RoundCap))
        start_angle = 90 * 16  # 从顶部开始
        span_angle = int(-progress * 360 * 16)
        painter.drawArc(rect, start_angle, span_angle)

        painter.end()

    def set_theme(self, is_dark: bool):
        """设置主题"""
        self._is_dark = is_dark
        if is_dark:
            self._apply_dark_styles()
        else:
            self._apply_styles()
        self.update()


class PomodoroDialog(QFrame):
    """番茄钟弹出面板（嵌入主窗口或独立显示）"""

    pomodoro_completed = pyqtSignal(int)

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._is_dark = False
        self._visible = False

        self.setObjectName("pomodoro_dialog")
        self.setFixedSize(280, 380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 内嵌番茄钟组件
        self.pomodoro = PomodoroWidget(db, self)
        self.pomodoro.pomodoro_completed.connect(self.pomodoro_completed.emit)
        layout.addWidget(self.pomodoro)

        self.hide()

    def toggle_visibility(self):
        """切换可见性"""
        if self._visible:
            self.hide()
            self._visible = False
        else:
            self.show()
            self._visible = True

    def set_theme(self, is_dark: bool):
        """设置主题"""
        self._is_dark = is_dark
        self.pomodoro.set_theme(is_dark)
        self.setStyleSheet(self._get_qss(is_dark))

    def _get_qss(self, is_dark: bool) -> str:
        if is_dark:
            return """
                #pomodoro_dialog {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 12px;
                }
            """
        return """
            #pomodoro_dialog {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """