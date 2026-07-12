"""仪表盘页面 - 核心指标 + 热力图 + Top5（异步数据加载）"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal

from database.db_manager import DatabaseManager
from gui.themes import SkeletonWidget, EmptyStateWidget, apply_card_shadow, AnimatedCard
from gui.pages.dashboard_widgets import (
    MetricCard, HeatmapWidget, GoalProgressCard, GoalRingWidget,
    IdleTimeCard, WeekCompareCard, WeekBarWidget,
    HourlyDistCard, HourlyBarWidget, TopAppItem,
)
from utils.async_loader import MultiDataLoader
from utils.time_utils import format_duration

# Re-export Widget components for backward compatibility
__all__ = [
    "DashboardPage", "MetricCard", "HeatmapWidget", "GoalProgressCard",
    "GoalRingWidget", "IdleTimeCard", "WeekCompareCard", "WeekBarWidget",
    "HourlyDistCard", "HourlyBarWidget", "TopAppItem",
]


class DashboardPage(QWidget):
    """仪表盘页面"""

    # 点击Top5应用时发出，请求跳转到分类管理页
    navigate_to_categories = pyqtSignal(str)  # 应用名

    def __init__(self, db_manager: DatabaseManager, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.db = db_manager
        self._is_dark = False
        self._loader = None  # 异步加载器
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        # 骨架屏层
        self._skeleton = SkeletonWidget(self)
        self._skeleton.setGeometry(0, 0, self.width(), self.height())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 20)

        # ===== 顶部指标卡 =====
        main_layout.addLayout(self._create_metrics_row())

        # ===== 功能卡片 =====
        self._add_feature_cards(main_layout)

        # ===== 本地存储标识 =====
        self.privacy_label = QLabel("🛡 所有数据均存储于本地，未经您允许不会上传")
        self.privacy_label.setObjectName("metric_title")
        self.privacy_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.privacy_label)

        # ===== 空数据状态 =====
        self.empty_state = EmptyStateWidget(
            icon="📊", title="还没有使用数据",
            description="开始记录后，这里将展示您的使用统计"
        )
        self.empty_state.setFixedHeight(300)
        self.empty_state.hide()
        main_layout.addWidget(self.empty_state)

        main_layout.addStretch()
        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _add_feature_cards(self, layout: QVBoxLayout) -> None:
        """添加功能卡片到布局"""
        self.goal_card = GoalProgressCard(db_manager=self.db)
        self.goal_card.goal_changed.connect(self._on_goal_changed)
        layout.addWidget(self.goal_card)

        self.idle_card = IdleTimeCard()
        layout.addWidget(self.idle_card)

        self.week_compare_card = WeekCompareCard()
        layout.addWidget(self.week_compare_card)

        self.hourly_card = HourlyDistCard()
        layout.addWidget(self.hourly_card)

        layout.addWidget(self._create_heatmap_card())
        layout.addWidget(self._create_top5_card())

    def _create_metrics_row(self) -> None:
        """创建顶部指标卡行"""
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)

        self.card_focus = MetricCard("专注时长", "0h 0m")
        self.card_apps = MetricCard("活跃应用", "0")
        self.card_actions = MetricCard("操作次数", "0")
        self.card_screenshots = MetricCard("截图数量", "0")

        for card in [self.card_focus, self.card_apps, self.card_actions, self.card_screenshots]:
            apply_card_shadow(card)

        metrics_layout.addWidget(self.card_focus)
        metrics_layout.addWidget(self.card_apps)
        metrics_layout.addWidget(self.card_actions)
        metrics_layout.addWidget(self.card_screenshots)
        return metrics_layout

    def _create_heatmap_card(self) -> None:
        """创建活跃热力图卡片"""
        heatmap_card = AnimatedCard()
        heatmap_card.setObjectName("card")
        apply_card_shadow(heatmap_card)
        heatmap_layout = QVBoxLayout(heatmap_card)
        heatmap_layout.setSpacing(8)

        heatmap_title = QLabel("活跃热力图")
        heatmap_title.setObjectName("card_title")
        heatmap_layout.addWidget(heatmap_title)

        heatmap_desc = QLabel("颜色深浅表示该时段的活跃程度")
        heatmap_desc.setObjectName("section_desc")
        heatmap_layout.addWidget(heatmap_desc)

        self.heatmap = HeatmapWidget()
        heatmap_layout.addWidget(self.heatmap)
        return heatmap_card

    def _create_top5_card(self) -> None:
        """创建今日Top5应用卡片"""
        top5_card = AnimatedCard()
        top5_card.setObjectName("card")
        apply_card_shadow(top5_card)
        top5_layout = QVBoxLayout(top5_card)
        top5_layout.setSpacing(8)

        top5_title = QLabel("今日 Top 5 应用")
        top5_title.setObjectName("card_title")
        self.top5_title_label = top5_title
        top5_layout.addWidget(top5_title)

        self.top5_container = QVBoxLayout()
        self.top5_container.setSpacing(4)
        top5_layout.addLayout(self.top5_container)
        return top5_card

    def refresh(self, date: str = None, start_date: str = None, is_range: bool = False) -> None:
        """异步刷新仪表盘数据"""
        if date is None:
            date = QDate.currentDate().toString("yyyy-MM-dd")

        # 显示骨架屏
        self._skeleton.show()
        self._skeleton.raise_()

        # 取消上一次加载
        if self._loader:
            self._loader.cancel_all()

        # 获取对比日期
        if is_range and start_date:
            days = (QDate.fromString(date, "yyyy-MM-dd").toJulianDay() -
                    QDate.fromString(start_date, "yyyy-MM-dd").toJulianDay() + 1)
            prev_end = QDate.fromString(start_date, "yyyy-MM-dd").addDays(-1).toString("yyyy-MM-dd")
            prev_start = QDate.fromString(prev_end, "yyyy-MM-dd").addDays(-days + 1).toString("yyyy-MM-dd")
        else:
            prev_end = QDate.fromString(date, "yyyy-MM-dd").addDays(-1).toString("yyyy-MM-dd")
            prev_start = prev_end
            days = 1

        # 并行加载数据
        self._loader = MultiDataLoader(self)
        if is_range:
            self._loader.add("app_summary", lambda: self.db.get_app_usage_summary_range(start_date, date))
        else:
            self._loader.add("app_summary", lambda: self.db.get_app_usage_summary(date))
        self._loader.add("prev_seconds", lambda: self.db.get_range_total_seconds(prev_start, prev_end) if is_range else self.db.get_day_total_seconds(prev_end))
        self._loader.add("prev_app_count", lambda: len(self.db.get_app_usage_summary_range(prev_start, prev_end)) if is_range else self.db.get_day_app_count(prev_end))
        self._loader.add("input_stats", lambda: self.db.get_input_event_count_range(start_date, date) if is_range else self.db.get_input_event_count(date))
        self._loader.add("screenshot_count", lambda: self.db.get_screenshots_count(start_date if is_range else date, end_date=date if is_range else None))
        self._loader.add("heatmap", lambda: self.db.get_heatmap_data(date))
        self._loader.add("sensitive_apps", lambda: self.db.get_sensitive_apps())
        self._loader.add("idle_summary", lambda: self.db.get_idle_summary(date) if not is_range else {"total_idle_minutes": 0, "idle_count": 0, "longest_idle_minutes": 0, "idle_periods": []})
        # 周对比数据 - 本周和上周的7天趋势
        self._loader.add("week_this", lambda: self._get_week_trend(date, 0))
        self._loader.add("week_last", lambda: self._get_week_trend(date, 7))
        # 每小时分布
        self._loader.add("hourly", lambda: self.db.get_hourly_distribution(date) if not is_range else [])

        # 保存上下文用于回调
        self._refresh_ctx = {
            "date": date, "start_date": start_date, "is_range": is_range,
            "prev_seconds_target": "range" if is_range else "day"
        }
        self._loader.all_done.connect(self._on_refresh_done)
        self._loader.start()

    def _on_refresh_done(self, results: dict) -> None:
        """异步数据加载完成，更新UI"""
        ctx = getattr(self, '_refresh_ctx', {})
        is_range = ctx.get("is_range", False)
        date = ctx.get("date", "")
        start_date = ctx.get("start_date", "")

        # 更新指标卡片
        self._update_metric_cards(results, is_range)

        # 更新图表和详情
        self._update_charts_and_details(results, is_range, start_date, date)

        # 空状态
        app_summary = results.get("app_summary") or []
        total_seconds = sum(item.get("total_seconds", 0) or 0 for item in app_summary)
        has_data = total_seconds > 0 or len(app_summary) > 0
        if has_data:
            self.empty_state.hide()
        else:
            self.empty_state.show()
            self.empty_state.set_theme(self._is_dark)

        # 隐藏骨架屏
        self._skeleton.hide()

    def _update_metric_cards(self, results: dict, is_range: bool) -> None:
        """更新指标卡片（专注时长、应用数、操作数、截图数）"""
        app_summary = results.get("app_summary") or []
        prev_seconds = results.get("prev_seconds") or 0
        prev_app_count = results.get("prev_app_count") or 0
        input_stats = results.get("input_stats") or {}
        screenshot_count = results.get("screenshot_count") or 0

        total_seconds = sum(item.get("total_seconds", 0) or 0 for item in app_summary)
        duration_str = format_duration(total_seconds)

        if prev_seconds > 0:
            diff_sec = total_seconds - prev_seconds
            diff_min = int(abs(diff_sec) / 60)
            is_up = diff_sec >= 0
            change_text = f"{'↑' if is_up else '↓'} 较{'上期' if is_range else '昨日'}{diff_min}分钟"
            self.card_focus.set_value(duration_str, change_text, is_up)
        else:
            self.card_focus.set_value(duration_str)

        today_app_count = len(app_summary)
        if prev_app_count > 0:
            diff = today_app_count - prev_app_count
            is_up = diff >= 0
            change_text = f"{'↑' if is_up else '↓'} 较{'上期' if is_range else '昨日'}{abs(diff)}个"
            self.card_apps.set_value(str(today_app_count), change_text, is_up)
        else:
            self.card_apps.set_value(str(today_app_count))

        total_actions = sum(input_stats.values()) if isinstance(input_stats, dict) else 0
        self.card_actions.set_value(f"{total_actions:,}")
        self.card_screenshots.set_value(str(screenshot_count))

        # 每日目标进度
        self.goal_card.set_progress(total_seconds)

    def _update_charts_and_details(self, results: dict, is_range: bool, start_date: str, date: str) -> None:
        """更新图表和详情区域（空闲、周对比、热力图、Top5等）"""
        app_summary = results.get("app_summary") or []
        heatmap_rows = results.get("heatmap") or []
        sensitive_apps = results.get("sensitive_apps") or set()
        idle_summary = results.get("idle_summary") or {"total_idle_minutes": 0, "idle_count": 0, "longest_idle_minutes": 0, "idle_periods": []}
        week_this = results.get("week_this") or []
        week_last = results.get("week_last") or []
        hourly_data = results.get("hourly") or []

        # 空闲时段
        self.idle_card.set_idle_data(idle_summary)

        # 周对比
        self.week_compare_card.set_data(week_this, week_last)

        # 每小时分布
        self.hourly_card.set_data(hourly_data)

        # 热力图
        self._update_heatmap(heatmap_rows)

        # Top 5
        if is_range:
            self.top5_title_label.setText(f"Top 5 应用（{start_date} ~ {date}）")
        else:
            self.top5_title_label.setText("今日 Top 5 应用")
        self._update_top5(app_summary, sensitive_apps)

    def _update_heatmap(self, rows: list) -> None:
        """更新热力图数据"""
        max_seconds = 1
        for row in rows:
            total = row.get("total_sec", 0) or 0
            if total > max_seconds:
                max_seconds = total

        data = {}
        raw_seconds = {}
        for row in rows:
            hour = row.get("hour", 0)
            dow = row.get("day_of_week", 0)
            total = row.get("total_sec", 0) or 0
            day_idx = (dow - 1) % 7
            level = min(4, int((total / max_seconds) * 4)) if max_seconds > 0 else 0
            data[(hour, day_idx)] = level
            raw_seconds[(hour, day_idx)] = total

        self.heatmap.set_data(data, raw_seconds=raw_seconds, is_dark=self._is_dark)

    def _update_top5(self, app_summary: list, sensitive_apps: set) -> None:
        """更新 Top 5 应用"""
        while self.top5_container.count():
            item = self.top5_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        category_colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
        visible_apps = [item for item in app_summary if item.get("app_name", "") not in sensitive_apps]

        if not visible_apps:
            empty_label = QLabel("暂无数据")
            empty_label.setObjectName("empty_hint")
            empty_label.setAlignment(Qt.AlignCenter)
            self.top5_container.addWidget(empty_label)
            return

        top5 = visible_apps[:5]
        max_seconds = max((item.get("total_seconds", 0) or 0) for item in top5) or 1

        for i, item in enumerate(top5):
            seconds = item.get("total_seconds", 0) or 0
            duration_str = format_duration(seconds)
            percentage = seconds / max_seconds if max_seconds > 0 else 0
            color = category_colors[i % len(category_colors)]

            top_item = TopAppItem(
                rank=i + 1,
                name=item.get("app_name", "Unknown"),
                duration=duration_str,
                percentage=percentage,
                color=color,
                is_dark=self._is_dark
            )
            top_item.clicked.connect(self.navigate_to_categories.emit)
            self.top5_container.addWidget(top_item)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """窗口大小变化时调整骨架屏位置"""
        super().resizeEvent(event)
        self._skeleton.setGeometry(0, 0, self.width(), self.height())

    def _on_goal_changed(self, new_minutes: int) -> None:
        """每日目标变更回调"""
        # 目标变更后，如果已有数据则重新计算进度
        # 这里不需要额外操作，因为goal_card内部已更新
        pass

    def _get_week_trend(self, date_str: str, offset_days: int) -> list:
        """获取某日期所在周的7天趋势数据

        Args:
            date_str: 日期字符串 "YYYY-MM-DD"
            offset_days: 0=本周, 7=上周
        Returns:
            [{day: "周一", seconds: int}, ...]
        """
        q_date = QDate.fromString(date_str, "yyyy-MM-dd")
        # 找到该日期所在周的周一
        day_of_week = q_date.dayOfWeek()  # 1=周一, 7=周日
        monday = q_date.addDays(-(day_of_week - 1) + offset_days)

        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        result = []
        for i in range(7):
            d = monday.addDays(i).toString("yyyy-MM-dd")
            total = self.db.get_day_total_seconds(d)
            result.append({"day": day_names[i], "seconds": int(total or 0)})
        return result

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self.heatmap._is_dark = is_dark
        self.heatmap.update()
        self._skeleton.set_theme(is_dark)
        self.empty_state.set_theme(is_dark)
        self.goal_card.set_theme(is_dark)
        self.idle_card.set_theme(is_dark)
        self.week_compare_card.set_theme(is_dark)
        self.hourly_card.set_theme(is_dark)
        # 更新AnimatedCard的ripple主题
        for card in [self.card_focus, self.card_apps, self.card_actions, self.card_screenshots]:
            card.set_theme(is_dark)
        # 更新Top5条目的主题
        for i in range(self.top5_container.count()):
            item = self.top5_container.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TopAppItem):
                item.widget().set_theme(is_dark)