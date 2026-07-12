"""仪表盘卡片组件 - 卡片容器及TopAppItem"""

from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                              QProgressBar, QSpinBox, QDialog, QDialogButtonBox, QPushButton)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QMouseEvent
from gui.themes import get_colors, apply_card_shadow, AnimatedCard, QSS_STYLES
from utils.time_utils import format_minutes, format_duration
import re

from gui.pages.dashboard_charts import GoalRingWidget, WeekBarWidget, HourlyBarWidget


class MetricCard(AnimatedCard):
    """指标卡片 - 带数字动画过渡 + ripple点击反馈"""

    def __init__(self, title: str, value: str = "0", change: str = "") -> None:
        super().__init__()
        self.setObjectName("metric_card")
        apply_card_shadow(self)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metric_title")
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("metric_value")
        layout.addWidget(self.value_label)

        self.change_label = QLabel(change)
        self.change_label.setObjectName("metric_change_up")
        layout.addWidget(self.change_label)

        # 数字动画 - 增强缓动：先快后慢 + 轻微回弹
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(25)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_current = 0.0
        self._anim_target = 0.0
        self._anim_prefix = ""
        self._anim_suffix = ""
        self._anim_phase = "accel"  # accel / overshoot / settle
        self._anim_overshoot = 0.0

    def set_value(self, value: str, change: str = "", is_up: bool = True) -> None:
        """设置显示值"""
        # 解析数字部分做动画
        match = re.match(r'([^\d]*)(\d+\.?\d*)(.*)', value)
        if match:
            self._anim_prefix = match.group(1)
            try:
                self._anim_target = float(match.group(2))
            except ValueError:
                self._anim_target = 0
            self._anim_suffix = match.group(3)
            self._anim_current = 0.0
            self._anim_phase = "accel"
            self._anim_overshoot = 0.0
            self._anim_timer.start()
        else:
            self.value_label.setText(value)

        if change:
            self.change_label.setText(change)
            self.change_label.setObjectName("metric_change_up" if is_up else "metric_change_down")
            self.change_label.style().unpolish(self.change_label)
            self.change_label.style().polish(self.change_label)
        else:
            self.change_label.setText("")

    def _anim_tick(self) -> None:
        """数字递增动画步进 - 三阶段缓动：加速→轻微回弹→稳定"""
        diff = self._anim_target - self._anim_current

        if self._anim_phase == "accel":
            # 快速接近目标
            self._anim_current += diff * 0.18
            if abs(diff) < self._anim_target * 0.05 + 1:
                # 超过目标5%产生回弹
                self._anim_overshoot = self._anim_target * 0.03
                self._anim_current = self._anim_target + self._anim_overshoot
                self._anim_phase = "overshoot"

        elif self._anim_phase == "overshoot":
            # 回弹阶段
            self._anim_overshoot *= 0.6
            self._anim_current = self._anim_target + self._anim_overshoot
            if self._anim_overshoot < 0.3:
                self._anim_current = self._anim_target
                self._anim_timer.stop()

        # 格式化显示
        if self._anim_target == int(self._anim_target):
            display = f"{self._anim_prefix}{int(self._anim_current)}{self._anim_suffix}"
        else:
            display = f"{self._anim_prefix}{self._anim_current:.1f}{self._anim_suffix}"
        self.value_label.setText(display)


class GoalProgressCard(AnimatedCard):
    """每日目标进度卡片 - 环形进度条 + 目标设置"""

    goal_changed = pyqtSignal(int)  # 目标分钟数变更
    goal_achieved = pyqtSignal()  # 目标达成通知

    def __init__(self, db_manager=None, parent=None) -> None:
        super().__init__()
        self.db = db_manager
        self._is_dark = False
        self._colors = get_colors(False)
        self._progress = 0.0  # 0.0 ~ 1.0
        self._current_minutes = 0
        self._goal_minutes = 480  # 默认8小时
        self._anim_progress = 0.0
        self._target_progress = 0.0
        self.setObjectName("card")
        apply_card_shadow(self)

        # 加载已保存的目标
        if self.db:
            saved = self.db.get_config("daily_goal_minutes", "480")
            try:
                self._goal_minutes = int(saved)
            except (ValueError, TypeError):
                self._goal_minutes = 480

        self._init_ui()
        self._apply_styles()

    def _init_ui(self) -> None:
        """初始化UI布局和组件"""
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        # 标题行
        title_row = QHBoxLayout()
        title_label = QLabel("🎯 每日目标")
        title_label.setObjectName("card_title")
        title_row.addWidget(title_label)
        title_row.addStretch()

        self.goal_btn = QPushButton("设置")
        self.goal_btn.setFixedSize(40, 22)
        self.goal_btn.setCursor(Qt.PointingHandCursor)
        self.goal_btn.clicked.connect(self._open_goal_dialog)
        title_row.addWidget(self.goal_btn)
        layout.addLayout(title_row)

        # 环形进度条区域
        self.ring_widget = GoalRingWidget(self)
        layout.addWidget(self.ring_widget, alignment=Qt.AlignCenter)

        # 数字显示
        self.value_label = QLabel("0h 0m / 8h 0m")
        self.value_label.setObjectName("metric_value")
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # 百分比
        self.percent_label = QLabel("0%")
        self.percent_label.setObjectName("metric_change_up")
        self.percent_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.percent_label)

        # 进度动画定时器
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(20)
        self._anim_timer.timeout.connect(self._anim_tick)

    def _apply_styles(self) -> None:
        """应用QSS样式表"""
        colors = self._colors
        self.goal_btn.setStyleSheet(QSS_STYLES["btn_ghost_sm"].format(c=colors))

    def set_progress(self, current_seconds: float) -> None:
        """设置当前进度（秒）"""
        was_achieved = self._target_progress >= 1.0
        self._current_minutes = int(current_seconds / 60)
        self._target_progress = min(1.0, current_seconds / (self._goal_minutes * 60)) if self._goal_minutes > 0 else 0
        self._anim_progress = 0.0
        self._anim_timer.start()
        self._update_labels()
        # 目标刚达成时发出通知（之前未达成，现在达成）
        if not was_achieved and self._target_progress >= 1.0:
            self.goal_achieved.emit()

    def _update_labels(self) -> None:
        """更新文字标签"""
        cur_str = format_minutes(self._current_minutes)
        goal_str = format_minutes(self._goal_minutes)
        self.value_label.setText(f"{cur_str} / {goal_str}")
        pct = int(self._target_progress * 100)
        self.percent_label.setText(f"{pct}%")
        # 根据完成度改变颜色
        if pct >= 100:
            self.percent_label.setText("🎉 已达成!")
            self.percent_label.setStyleSheet(f"color: {self._colors['success']}; font-weight: bold; font-size: 13px;")
        else:
            self.percent_label.setStyleSheet(f"color: {self._colors['primary']}; font-size: 12px;")

    def _anim_tick(self) -> None:
        """环形进度动画步进"""
        diff = self._target_progress - self._anim_progress
        self._anim_progress += diff * 0.15
        if abs(diff) < 0.005:
            self._anim_progress = self._target_progress
            self._anim_timer.stop()
        self.ring_widget.update()

    def _open_goal_dialog(self) -> None:
        """打开目标设置对话框"""
        colors = self._colors
        dialog, spin, btn_box = self._build_goal_dialog(colors)

        def on_accept() -> None:
            """对话框确认回调"""
            new_val = spin.value()
            self._goal_minutes = new_val
            if self.db:
                self.db.save_config("daily_goal_minutes", str(new_val))
            self.goal_changed.emit(new_val)
            # 重新计算进度
            self._target_progress = min(1.0, self._current_minutes / (self._goal_minutes * 60)) if self._goal_minutes > 0 else 0
            self._anim_progress = 0.0
            self._anim_timer.start()
            self._update_labels()
            dialog.accept()

        btn_box.accepted.connect(on_accept)
        btn_box.rejected.connect(dialog.reject)
        dialog.exec_()

    def _build_goal_dialog(self, colors: dict) -> None:
        """构建目标设置对话框UI，返回(dialog, spin_box, btn_box)"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置每日目标")
        dialog.setFixedSize(280, 150)
        dialog.setStyleSheet(QSS_STYLES["dialog_card"].format(c=colors))

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        label = QLabel("每日专注目标（分钟）：")
        layout.addWidget(label)

        spin = QSpinBox()
        spin.setRange(30, 1440)
        spin.setSingleStep(30)
        spin.setValue(self._goal_minutes)
        spin.setSuffix(" 分钟")
        spin.setStyleSheet(QSS_STYLES["spinbox"].format(c=colors))
        layout.addWidget(spin)

        # 快捷按钮
        quick_row = QHBoxLayout()
        for text, val in [("2h", 120), ("4h", 240), ("6h", 360), ("8h", 480)]:
            btn = QPushButton(text)
            btn.setFixedSize(48, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(QSS_STYLES["btn_ghost"].format(c=colors))
            btn.clicked.connect(lambda checked, v=val: spin.setValue(v))
            quick_row.addWidget(btn)
        layout.addLayout(quick_row)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.setStyleSheet(QSS_STYLES["btn_primary_md"].format(c=colors))
        layout.addWidget(btn_box)

        return dialog, spin, btn_box

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        super().set_theme(is_dark)
        self._apply_styles()
        self._update_labels()
        self.ring_widget.update()


class IdleTimeCard(AnimatedCard):
    """空闲时间统计卡片 - 显示空闲时段汇总"""

    def __init__(self, parent=None) -> None:
        super().__init__()
        self._is_dark = False
        self._colors = get_colors(False)
        self._idle_periods = []
        self.setObjectName("card")
        apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        # 标题行
        title_row = QHBoxLayout()
        title_label = QLabel("💤 空闲时段")
        title_label.setObjectName("card_title")
        title_row.addWidget(title_label)
        title_row.addStretch()

        self.count_label = QLabel("0 段")
        self.count_label.setObjectName("metric_change_up")
        title_row.addWidget(self.count_label)
        layout.addLayout(title_row)

        # 汇总行
        summary_row = QHBoxLayout()
        self.total_label = QLabel("总计: 0m")
        self.total_label.setStyleSheet("font-size: 13px;")
        summary_row.addWidget(self.total_label)

        self.longest_label = QLabel("最长: 0m")
        self.longest_label.setStyleSheet("font-size: 13px;")
        summary_row.addWidget(self.longest_label)
        summary_row.addStretch()
        layout.addLayout(summary_row)

        # 空闲时段列表（最多显示5条）
        self.periods_container = QVBoxLayout()
        self.periods_container.setSpacing(2)
        layout.addLayout(self.periods_container)

        # 空状态提示
        self.no_idle_label = QLabel("无空闲时段（最少10分钟间隔）")
        self.no_idle_label.setObjectName("section_desc")
        self.no_idle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.no_idle_label)

        self._apply_styles()

    def _apply_styles(self) -> None:
        """应用QSS样式表"""
        colors = self._colors
        self.total_label.setStyleSheet(QSS_STYLES["secondary_text"].format(c=colors))
        self.longest_label.setStyleSheet(QSS_STYLES["secondary_text"].format(c=colors))

    def set_idle_data(self, idle_summary: dict) -> None:
        """设置空闲时间数据"""
        self._idle_periods = idle_summary.get("idle_periods", [])
        total = idle_summary.get("total_idle_minutes", 0)
        count = idle_summary.get("idle_count", 0)
        longest = idle_summary.get("longest_idle_minutes", 0)

        # 更新汇总
        self.total_label.setText(f"总计: {format_minutes(total)}")
        self.longest_label.setText(f"最长: {format_minutes(longest)}")

        self.count_label.setText(f"{count} 段")

        # 清空旧列表
        while self.periods_container.count():
            item = self.periods_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 显示空闲时段
        if self._idle_periods:
            self.no_idle_label.hide()
            colors = self._colors
            for period in self._idle_periods[:5]:  # 最多显示5条
                start = period.get("start", "")
                end = period.get("end", "")
                dur = period.get("duration_minutes", 0)
                bar_label = QLabel(f"  {start} → {end}  ({dur}m)")
                bar_label.setStyleSheet(f"font-size: 12px; color: {colors['text_muted']}; padding: 2px 0;")
                self.periods_container.addWidget(bar_label)

            if len(self._idle_periods) > 5:
                more = QLabel(f"  ...还有 {len(self._idle_periods) - 5} 段")
                more.setStyleSheet(QSS_STYLES["small_text"].format(c=colors))
                self.periods_container.addWidget(more)
        else:
            self.no_idle_label.show()

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        super().set_theme(is_dark)
        self._apply_styles()
        # 重新渲染时段列表
        if self._idle_periods:
            self.set_idle_data({
                "idle_periods": self._idle_periods,
                "total_idle_minutes": sum(p.get("duration_minutes", 0) for p in self._idle_periods),
                "idle_count": len(self._idle_periods),
                "longest_idle_minutes": max((p.get("duration_minutes", 0) for p in self._idle_periods), default=0)
            })


class WeekCompareCard(AnimatedCard):
    """周对比卡片 - 本周 vs 上周对比柱状图"""

    def __init__(self, parent=None) -> None:
        super().__init__()
        self._is_dark = False
        self._this_week = []  # [{day: str, seconds: int}, ...]
        self._last_week = []
        self.setObjectName("card")
        apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 标题行
        title_row = QHBoxLayout()
        title_label = QLabel("📊 周对比")
        title_label.setObjectName("card_title")
        title_row.addWidget(title_label)
        title_row.addStretch()
        layout.addLayout(title_row)

        # 图例
        legend_row = QHBoxLayout()
        legend_row.setSpacing(16)
        colors = self._colors

        this_indicator = QLabel("■")
        this_indicator.setStyleSheet(f"color: {colors['primary']}; font-size: 12px;")
        this_legend = QLabel("本周")
        this_legend.setStyleSheet(QSS_STYLES["small_text"].format(c=colors))
        legend_row.addWidget(this_indicator)
        legend_row.addWidget(this_legend)

        last_indicator = QLabel("■")
        last_indicator.setStyleSheet(f"color: {colors['border']}; font-size: 12px;")
        last_legend = QLabel("上周")
        last_legend.setStyleSheet(QSS_STYLES["small_text"].format(c=colors))
        legend_row.addWidget(last_indicator)
        legend_row.addWidget(last_legend)
        legend_row.addStretch()

        self._legend_row = legend_row
        layout.addLayout(legend_row)

        # 柱状图绘制区域
        self._bar_widget = WeekBarWidget(self)
        layout.addWidget(self._bar_widget)

        # 汇总行
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("section_desc")
        self._summary_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._summary_label)

    def set_data(self, this_week: list, last_week: list) -> None:
        """设置周数据

        Args:
            this_week: [{day: "周一", seconds: 12345}, ...]
            last_week: [{day: "周一", seconds: 12345}, ...]
        """
        self._this_week = this_week
        self._last_week = last_week
        self._update_summary()
        self._bar_widget.update()

    def _update_summary(self) -> None:
        """更新汇总文字"""
        this_total = sum(d.get("seconds", 0) for d in self._this_week)
        last_total = sum(d.get("seconds", 0) for d in self._last_week)

        this_str = format_duration(this_total)
        last_str = format_duration(last_total)

        if last_total > 0:
            diff = this_total - last_total
            diff_min = int(abs(diff) / 60)
            is_up = diff >= 0
            arrow = "↑" if is_up else "↓"
            pct = int(abs(diff) / last_total * 100) if last_total > 0 else 0
            self._summary_label.setText(
                f"本周 {this_str} vs 上周 {last_str}  {arrow}{pct}%"
            )
            colors = self._colors
            color = colors['success'] if is_up else colors['danger']
            self._summary_label.setStyleSheet(QSS_STYLES["muted_text"].format(c=colors))
        else:
            self._summary_label.setText(f"本周 {this_str}（上周无数据）")

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        super().set_theme(is_dark)
        # 更新图例颜色
        colors = self._colors
        # 重新构建图例
        while self._legend_row.count():
            item = self._legend_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        this_indicator = QLabel("■")
        this_indicator.setStyleSheet(f"color: {colors['primary']}; font-size: 12px;")
        this_legend = QLabel("本周")
        this_legend.setStyleSheet(QSS_STYLES["small_text"].format(c=colors))
        self._legend_row.addWidget(this_indicator)
        self._legend_row.addWidget(this_legend)

        last_indicator = QLabel("■")
        last_indicator.setStyleSheet(f"color: {colors['bg_sidebar_hover']}; font-size: 12px;")
        last_legend = QLabel("上周")
        last_legend.setStyleSheet(QSS_STYLES["small_text"].format(c=colors))
        self._legend_row.addWidget(last_indicator)
        self._legend_row.addWidget(last_legend)
        self._legend_row.addStretch()

        self._update_summary()
        self._bar_widget.update()


class HourlyDistCard(AnimatedCard):
    """每小时活跃分布卡片 - 24小时柱状图"""

    def __init__(self, parent=None) -> None:
        super().__init__()
        self._is_dark = False
        self._hourly_data = []  # [{hour: int, total: int}, ...]
        self.setObjectName("card")
        apply_card_shadow(self)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # 标题行
        title_row = QHBoxLayout()
        title_label = QLabel("📈 每小时活跃分布")
        title_label.setObjectName("card_title")
        title_row.addWidget(title_label)
        title_row.addStretch()

        self.peak_label = QLabel("")
        self.peak_label.setObjectName("section_desc")
        title_row.addWidget(self.peak_label)
        layout.addLayout(title_row)

        # 柱状图
        self._bar_widget = HourlyBarWidget(self)
        layout.addWidget(self._bar_widget)

    def set_data(self, hourly_data: list) -> None:
        """设置每小时分布数据 [{hour: int, total: int}, ...]"""
        self._hourly_data = hourly_data
        # 计算峰值时段
        if hourly_data:
            peak = max(hourly_data, key=lambda x: x.get("total", 0))
            peak_hour = peak.get("hour", 0)
            peak_min = int((peak.get("total", 0) or 0) / 60)
            self.peak_label.setText(f"峰值: {peak_hour:02d}:00 ({peak_min}m)")
        else:
            self.peak_label.setText("")
        self._bar_widget.update()

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        super().set_theme(is_dark)
        self._bar_widget.update()


class TopAppItem(QFrame):
    """Top应用条目 - 可点击跳转分类管理"""
    clicked = pyqtSignal(str)  # 发送应用名

    def __init__(self, rank: int, name: str, duration: str, percentage: float, color: str = "#3B82F6", is_dark: bool = False) -> None:
        super().__init__()
        self._color = color
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        self._app_name = name
        self.setObjectName("card")
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # 排名
        rank_label = QLabel(f"#{rank}")
        rank_label.setFixedWidth(28)
        rank_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {color};")
        layout.addWidget(rank_label)

        # 应用名
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(name_label)

        layout.addStretch()

        # 进度条 - 使用QProgressBar替代硬编码frame
        colors = self._colors
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(percentage * 100))
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            QSS_STYLES["progressbar"].format(c=colors).replace("{c[primary]}", color)
        )
        layout.addWidget(self.progress_bar)

        # 时长
        duration_label = QLabel(duration)
        duration_label.setStyleSheet(f"font-family: Consolas; font-size: 13px; color: {colors['text_secondary']};")
        duration_label.setFixedWidth(70)
        duration_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(duration_label)

    def set_theme(self, is_dark: bool) -> None:
        """更新主题"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        colors = self._colors
        self.progress_bar.setStyleSheet(
            QSS_STYLES["progressbar"].format(c=colors).replace("{c[primary]}", self._color)
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """点击时发出信号，跳转到分类管理"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._app_name)
        super().mousePressEvent(event)