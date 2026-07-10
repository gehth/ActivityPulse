"""统计洞察页面 - 环形图 + 折线图 + 柱状图"""

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QToolTip
)
from PyQt5.QtCore import Qt, QDate, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QPen, QPolygon, QMouseEvent

from database.db_manager import DatabaseManager
from gui.themes import get_colors, EmptyStateWidget, apply_card_shadow, AnimatedCard
from utils.async_loader import MultiDataLoader
from utils.time_utils import format_minutes

# 分类颜色
CHART_COLORS = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16",
]


class DonutChartWidget(QWidget):
    """环形图控件 - 支持hover tooltip"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.data = []  # [(name, value, color)]
        self.setFixedSize(220, 220)
        self._is_dark = False
        self._hover_index = -1  # 当前hover的扇区索引
        self._segments = []  # 存储每个扇区的角度范围 [(start_angle, span_angle)]
        self.setMouseTracking(True)

    def set_data(self, data: list, is_dark: bool = False) -> None:
        self.data = data
        self._is_dark = is_dark
        self._hover_index = -1
        self._update_segments()
        self.update()

    def _update_segments(self) -> None:
        """预计算每个扇区的角度范围（从12点方向顺时针，1/16度单位）"""
        self._segments = []
        total = sum(v for _, v, _ in self.data)
        if total == 0:
            return
        accumulated = 0  # 从12点方向顺时针累计
        for _, value, _ in self.data:
            span = int((value / total) * 360 * 16)
            self._segments.append((accumulated, accumulated + span))
            accumulated += span

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动时检测hover的扇区"""
        if not self.data or not self._segments:
            QToolTip.hideText()
            self.update()
            return

        mx, my = event.x(), event.y()
        cx, cy = 110, 100
        outer_r = 85
        inner_r = 55

        # 计算鼠标到中心的距离
        dx = mx - cx
        dy = my - cy
        dist = math.sqrt(dx * dx + dy * dy)

        # 不在环形区域内
        if dist < inner_r or dist > outer_r:
            if self._hover_index != -1:
                self._hover_index = -1
                QToolTip.hideText()
                self.update()
            return

        # 计算角度（从12点方向顺时针，0-360度）
        angle_deg = math.degrees(math.atan2(dx, -dy))
        if angle_deg < 0:
            angle_deg += 360
        angle_16 = int(angle_deg * 16)

        # 查找所在扇区（segments存储的是从12点顺时针的1/16度范围）
        total = sum(v for _, v, _ in self.data)
        found_index = -1
        for i, (start, end) in enumerate(self._segments):
            if start <= angle_16 < end:
                found_index = i
                break

        if found_index != self._hover_index:
            self._hover_index = found_index
            self.update()

        if found_index >= 0:
            name, value, color = self.data[found_index]
            pct = (value / total * 100) if total > 0 else 0
            QToolTip.showText(
                event.globalPos(),
                f"<b style='color:{color}'>{name}</b><br>时长: {value} 分钟<br>占比: {pct:.1f}%",
                self
            )
        else:
            QToolTip.hideText()

    def leaveEvent(self, event) -> None:
        """鼠标离开时清除hover状态"""
        self._hover_index = -1
        QToolTip.hideText()
        self.update()

    def paintEvent(self, event) -> None:
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = get_colors("dark" if self._is_dark else "light")

        cx, cy = 110, 100
        outer_r = 85
        inner_r = 55

        total = sum(v for _, v, _ in self.data)
        if total == 0:
            painter.end()
            return

        start_angle = 90 * 16  # 从12点方向开始
        for i, (name, value, color) in enumerate(self.data):
            span = int((value / total) * 360 * 16)

            # hover时稍微扩大该扇区并偏移
            r = outer_r
            offset_x, offset_y = 0, 0
            if i == self._hover_index:
                r = outer_r + 5
                # 计算扇区中心角度（Qt角度系统：0=3点，正=逆时针）
                mid_qt_angle = start_angle - span / 2  # 1/16度
                mid_rad = math.radians(mid_qt_angle / 16)
                offset_x = int(4 * math.cos(mid_rad))
                offset_y = int(-4 * math.sin(mid_rad))

            painter.setBrush(QBrush(QColor(color)))
            if i == self._hover_index:
                # hover时加亮边框
                painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
            else:
                painter.setPen(Qt.NoPen)
            painter.drawPie(int(cx - r + offset_x), int(cy - r + offset_y),
                          int(r * 2), int(r * 2),
                          start_angle, -span)
            start_angle -= span

        # 中心圆（形成环形）
        painter.setBrush(QBrush(QColor(colors["bg_card"])))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - inner_r), int(cy - inner_r),
                          int(inner_r * 2), int(inner_r * 2))

        # 中心文字
        painter.setPen(QColor(colors["text_primary"]))
        painter.setFont(QFont("Consolas", 16, QFont.Bold))
        painter.drawText(QRect(int(cx - inner_r), int(cy - 20),
                              int(inner_r * 2), 40), Qt.AlignCenter, f"{total:.0f}")

        painter.setPen(QColor(colors["text_secondary"]))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(QRect(int(cx - inner_r), int(cy + 5),
                              int(inner_r * 2), 20), Qt.AlignCenter, "总时长(分)")

        painter.end()


class LineChartWidget(QWidget):
    """折线图控件 - 支持hover tooltip"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.data = []  # [(label, value)]
        self.setFixedHeight(200)
        self._is_dark = False
        self._hover_index = -1  # 当前hover的数据点索引
        self._points = []  # 缓存绘制后的像素坐标
        self._margin_left = 50
        self._margin_right = 20
        self._margin_top = 20
        self._margin_bottom = 35
        self.setMouseTracking(True)

    def set_data(self, data: list, is_dark: bool = False) -> None:
        self.data = data
        self._is_dark = is_dark
        self._hover_index = -1
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动时检测最近的数据点"""
        if not self.data or not self._points:
            QToolTip.hideText()
            self.update()
            return

        mx, my = event.x(), event.y()
        # 查找最近的数据点（基于X距离）
        min_dist = float('inf')
        nearest = -1
        for i, (px, py) in enumerate(self._points):
            dist = abs(mx - px)
            if dist < min_dist:
                min_dist = dist
                nearest = i

        # 只在合理距离内触发
        if min_dist > 30:
            nearest = -1

        if nearest != self._hover_index:
            self._hover_index = nearest
            self.update()

        if nearest >= 0:
            label, value = self.data[nearest]
            QToolTip.showText(
                event.globalPos(),
                f"<b>{label}</b><br>活跃: {value:.0f} 分钟",
                self
            )
        else:
            QToolTip.hideText()

    def leaveEvent(self, event) -> None:
        """鼠标离开时清除hover状态"""
        self._hover_index = -1
        QToolTip.hideText()
        self.update()

    def paintEvent(self, event) -> None:
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = get_colors("dark" if self._is_dark else "light")

        margin_left = self._margin_left
        margin_right = self._margin_right
        margin_top = self._margin_top
        margin_bottom = self._margin_bottom
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        # Y轴刻度
        max_val = max(v for _, v in self.data) or 1
        painter.setPen(QColor(colors["text_muted"]))
        painter.setFont(QFont("Consolas", 8))
        for i in range(5):
            y = margin_top + h - (h * i / 4)
            val = max_val * i / 4
            painter.drawText(0, int(y - 4), margin_left - 5, 16, Qt.AlignRight, f"{val:.0f}")
            # 网格线
            pen = QPen(QColor(colors["border"]))
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(margin_left, int(y), self.width() - margin_right, int(y))

        # X轴标签
        painter.setPen(QColor(colors["text_muted"]))
        painter.setFont(QFont("Microsoft YaHei", 8))
        n = len(self.data)
        for i, (label, _) in enumerate(self.data):
            x = margin_left + (w * i / max(n - 1, 1))
            painter.drawText(int(x - 20), self.height() - 10, 40, 20, Qt.AlignCenter, label)

        # 绘制折线
        points = []
        for i, (_, value) in enumerate(self.data):
            x = margin_left + (w * i / max(n - 1, 1))
            y = margin_top + h - (h * value / max_val)
            points.append((int(x), int(y)))

        # 缓存点坐标供hover使用
        self._points = points

        # 填充区域
        if len(points) >= 2:
            fill_color = QColor(colors["primary"])
            fill_color.setAlpha(30)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.NoPen)
            polygon_points = [QPoint(points[0][0], margin_top + h)]
            for px, py in points:
                polygon_points.append(QPoint(px, py))
            polygon_points.append(QPoint(points[-1][0], margin_top + h))
            painter.drawPolygon(QPolygon(polygon_points))

        # 绘制线条
        pen = QPen(QColor(colors["primary"]))
        pen.setWidth(2)
        painter.setPen(pen)
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1],
                           points[i + 1][0], points[i + 1][1])

        # 绘制数据点 + hover高亮
        for i, (x, y) in enumerate(points):
            if i == self._hover_index:
                # hover: 垂直参考线
                pen = QPen(QColor(colors["primary"]))
                pen.setStyle(Qt.DashLine)
                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawLine(x, margin_top, x, margin_top + h)

                # hover: 大圆点 + 光晕
                painter.setPen(Qt.NoPen)
                glow = QColor(colors["primary"])
                glow.setAlpha(40)
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(x - 10, y - 10, 20, 20)

                painter.setBrush(QBrush(QColor(colors["primary"])))
                painter.drawEllipse(x - 5, y - 5, 10, 10)

                # hover: 白色内圆
                painter.setBrush(QBrush(QColor(colors["bg_card"])))
                painter.drawEllipse(x - 2, y - 2, 4, 4)
            else:
                painter.setBrush(QBrush(QColor(colors["primary"])))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x - 4, y - 4, 8, 8)

        painter.end()


class BarChartWidget(QWidget):
    """柱状图控件 - 支持hover tooltip"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.data = []  # [(label, value)]
        self.setFixedHeight(200)
        self._is_dark = False
        self._hover_index = -1  # 当前hover的柱子索引
        self._bar_rects = []  # 缓存每个柱子的QRect
        self._margin_left = 40
        self._margin_right = 20
        self._margin_top = 20
        self._margin_bottom = 35
        self.setMouseTracking(True)

    def set_data(self, data: list, is_dark: bool = False) -> None:
        self.data = data
        self._is_dark = is_dark
        self._hover_index = -1
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动时检测hover的柱子"""
        if not self.data or not self._bar_rects:
            QToolTip.hideText()
            self.update()
            return

        mx, my = event.x(), event.y()
        found = -1
        for i, rect in enumerate(self._bar_rects):
            if rect.contains(mx, my):
                found = i
                break

        if found != self._hover_index:
            self._hover_index = found
            self.update()

        if found >= 0:
            label, value = self.data[found]
            time_str = format_minutes(value, fmt="long")
            QToolTip.showText(
                event.globalPos(),
                f"<b>{label}:00</b><br>活跃: {time_str}<br>操作: {value:.0f}次",
                self
            )
        else:
            QToolTip.hideText()

    def leaveEvent(self, event) -> None:
        """鼠标离开时清除hover状态"""
        self._hover_index = -1
        QToolTip.hideText()
        self.update()

    def paintEvent(self, event) -> None:
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = get_colors("dark" if self._is_dark else "light")

        margin_left = self._margin_left
        margin_right = self._margin_right
        margin_top = self._margin_top
        margin_bottom = self._margin_bottom
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        max_val = max(v for _, v in self.data) or 1
        n = len(self.data)
        bar_width = max(w / n - 4, 8)

        # Y轴刻度
        painter.setPen(QColor(colors["text_muted"]))
        painter.setFont(QFont("Consolas", 8))
        for i in range(5):
            y = margin_top + h - (h * i / 4)
            val = max_val * i / 4
            painter.drawText(0, int(y - 4), margin_left - 5, 16, Qt.AlignRight, f"{val:.0f}")

        # 缓存柱子矩形
        self._bar_rects = []

        # 绘制柱子
        for i, (label, value) in enumerate(self.data):
            x = margin_left + (w * i / n) + 2
            bar_h = h * value / max_val if max_val > 0 else 0
            y = margin_top + h - bar_h

            bar_rect = QRect(int(x), int(y), int(bar_width), max(int(bar_h), 1))
            self._bar_rects.append(bar_rect)

            # 柱子颜色 - hover时高亮
            color = QColor(colors["primary"])
            if i == self._hover_index:
                color = QColor(colors["primary"]).lighter(130)
                color.setAlpha(220)
                # hover: 绘制背景高亮条
                painter.setPen(Qt.NoPen)
                bg_color = QColor(colors["primary"])
                bg_color.setAlpha(15)
                painter.setBrush(QBrush(bg_color))
                painter.drawRect(int(x - 1), margin_top, int(bar_width + 2), h)
            else:
                color.setAlpha(180)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_h), 3, 3)

            # hover: 在柱子顶部显示数值
            if i == self._hover_index and value > 0:
                painter.setPen(QColor(colors["text_primary"]))
                painter.setFont(QFont("Consolas", 9, QFont.Bold))
                val_text = f"{value:.0f}"
                painter.drawText(int(x - 5), int(y - 18), int(bar_width + 10), 16,
                               Qt.AlignCenter, val_text)

            # X轴标签
            painter.setPen(QColor(colors["text_muted"]))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(x - 5), self.height() - 10, int(bar_width + 10), 20,
                           Qt.AlignCenter, label)

        painter.end()


class InsightsPage(QWidget):
    """统计洞察页面"""

    def __init__(self, db_manager: DatabaseManager, parent=None) -> None:
        super().__init__(parent)
        self.db = db_manager
        self._is_dark = False
        self._loader = None  # 异步加载器
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 20)

        # 标题
        title = QLabel("统计洞察")
        title.setObjectName("page_title")
        main_layout.addWidget(title)

        main_layout.addLayout(self._create_top_charts())
        main_layout.addWidget(self._create_bar_chart_card())

        # 空数据状态
        self.empty_state = EmptyStateWidget(
            icon="📈", title="还没有统计数据",
            description="使用一段时间后，这里将展示详细的分析图表"
        )
        self.empty_state.setFixedHeight(300)
        self.empty_state.hide()
        main_layout.addWidget(self.empty_state)

        main_layout.addStretch()
        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _create_top_charts(self) -> None:
        """创建上半部分图表区域（环形图+折线图）"""
        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        # 环形图卡片
        donut_card = AnimatedCard()
        donut_card.setObjectName("card")
        apply_card_shadow(donut_card)
        donut_layout = QVBoxLayout(donut_card)
        donut_title = QLabel("应用使用占比")
        donut_title.setObjectName("card_title")
        donut_layout.addWidget(donut_title)

        donut_row = QHBoxLayout()
        self.donut_chart = DonutChartWidget()
        donut_row.addWidget(self.donut_chart)

        # 图例
        self.legend_container = QVBoxLayout()
        self.legend_container.setSpacing(4)
        donut_row.addLayout(self.legend_container)
        donut_row.addStretch()
        donut_layout.addLayout(donut_row)
        top_layout.addWidget(donut_card, 1)

        # 折线图卡片
        line_card = AnimatedCard()
        line_card.setObjectName("card")
        apply_card_shadow(line_card)
        line_layout = QVBoxLayout(line_card)
        line_title = QLabel("7日活跃趋势")
        line_title.setObjectName("card_title")
        line_layout.addWidget(line_title)
        self.line_chart = LineChartWidget()
        line_layout.addWidget(self.line_chart)
        top_layout.addWidget(line_card, 2)

        return top_layout

    def _create_bar_chart_card(self) -> None:
        """创建柱状图卡片"""
        bar_card = AnimatedCard()
        bar_card.setObjectName("card")
        apply_card_shadow(bar_card)
        bar_layout = QVBoxLayout(bar_card)
        bar_title = QLabel("时段分布（按小时统计活跃度）")
        bar_title.setObjectName("card_title")
        bar_layout.addWidget(bar_title)
        self.bar_chart = BarChartWidget()
        bar_layout.addWidget(self.bar_chart)
        return bar_card

    def refresh(self, date: str = None, start_date: str = None, is_range: bool = False) -> None:
        """异步刷新统计数据"""
        if date is None:
            date = QDate.currentDate().toString("yyyy-MM-dd")

        # 取消上一次加载
        if self._loader:
            self._loader.cancel_all()

        # 并行加载3个图表数据
        self._loader = MultiDataLoader(self)
        if is_range and start_date:
            self._loader.add("donut_data", lambda: self.db.get_app_usage_summary_range(start_date, date))
        else:
            self._loader.add("donut_data", lambda: self.db.get_app_usage_summary(date))
        self._loader.add("sensitive_apps", lambda: self.db.get_sensitive_apps())

        if is_range and start_date:
            start = QDate.fromString(start_date, "yyyy-MM-dd")
            end = QDate.fromString(date, "yyyy-MM-dd")
            days = start.daysTo(end) + 1
            self._loader.add("trend_data", lambda: self.db.get_n_day_trend(date, days))
        else:
            self._loader.add("trend_data", lambda: self.db.get_7day_trend(date))

        self._loader.add("hourly_data", lambda: self.db.get_hourly_distribution(date))

        self._refresh_ctx = {"date": date, "start_date": start_date, "is_range": is_range}
        self._loader.all_done.connect(self._on_data_loaded)
        self._loader.start()

    def _on_data_loaded(self, results: dict) -> None:
        """异步数据加载完成，更新图表"""
        ctx = getattr(self, '_refresh_ctx', {})
        is_range = ctx.get("is_range", False)

        donut_data = results.get("donut_data") or []
        sensitive_apps = results.get("sensitive_apps") or set()
        trend_data = results.get("trend_data") or []
        hourly_data = results.get("hourly_data") or []

        # 环形图
        self._update_donut(donut_data, sensitive_apps)

        # 折线图
        line_data = []
        for row in trend_data:
            total = row.get("total_seconds", 0) or 0
            minutes = int(total / 60)
            days_ago = row.get("days_ago", 0)
            d = QDate.currentDate().addDays(-days_ago)
            label = d.toString("MM/dd")
            line_data.append((label, minutes))
        self.line_chart.set_data(line_data, self._is_dark)

        # 柱状图
        hourly_map = {row.get("hour", 0): (row.get("total", 0) or 0) / 60 for row in hourly_data}
        bar_data = [(f"{h:02d}", hourly_map.get(h, 0)) for h in range(24)]
        self.bar_chart.set_data(bar_data, self._is_dark)

        # 空状态
        has_data = bool(donut_data) or bool(trend_data) or bool(hourly_data)
        if has_data:
            self.empty_state.hide()
        else:
            self.empty_state.show()
            self.empty_state.set_theme(self._is_dark)

    def _update_donut(self, app_summary: list, sensitive_apps: set) -> None:
        """更新环形图"""
        chart_data = []
        other_minutes = 0
        for i, item in enumerate(app_summary[:8]):
            seconds = item.get("total_seconds", 0) or 0
            minutes = int(seconds / 60)
            if minutes > 0:
                app_name = item.get("app_name", "Unknown")
                if app_name in sensitive_apps:
                    other_minutes += minutes
                else:
                    chart_data.append((
                        app_name,
                        minutes,
                        CHART_COLORS[len(chart_data) % len(CHART_COLORS)]
                    ))

        if other_minutes > 0:
            chart_data.append(("其他(含敏感)", other_minutes, "#6B7280"))

        self.donut_chart.set_data(chart_data, self._is_dark)

        while self.legend_container.count():
            item = self.legend_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name, value, color in chart_data:
            label = QLabel(f"● {name}: {value}分钟")
            label.setObjectName("legend_text")
            label.setStyleSheet(f"color: {color};")
            self.legend_container.addWidget(label)

    def set_theme(self, is_dark: bool) -> None:
        self._is_dark = is_dark
        self.donut_chart._is_dark = is_dark
        self.line_chart._is_dark = is_dark
        self.bar_chart._is_dark = is_dark
        self.donut_chart.update()
        self.line_chart.update()
        self.bar_chart.update()
        self.empty_state.set_theme(is_dark)