"""仪表盘图表组件 - 纯绘制控件（热力图、环形图、柱状图等）"""

from PyQt5.QtWidgets import QWidget, QToolTip
from PyQt5.QtCore import Qt, QRectF, QEvent
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QPen, QPaintEvent, QMouseEvent
from gui.themes import get_colors


class HeatmapWidget(QWidget):
    """活跃热力图 - 类GitHub贡献图，hover显示时长"""

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setMouseTracking(True)
        self.data = {}  # {(hour, day): level}  level: 0-4
        self.raw_seconds = {}  # {(hour, day): seconds} 原始秒数用于tooltip
        self.colors_light = ["#E5E7EB", "#BBF7D0", "#86EFAC", "#34D399", "#10B981"]
        self.colors_dark = ["#374151", "#064E3B", "#065F46", "#047857", "#10B981"]
        self._is_dark = False
        self._colors = get_colors(False)
        self._cell_size = 20
        self._gap = 3
        self._margin_left = 40
        self._margin_top = 25

    def set_data(self, data: dict, raw_seconds: dict = None, is_dark: bool = False) -> None:
        """设置数据并更新显示"""
        self.data = data
        self.raw_seconds = raw_seconds or {}
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        colors = self.colors_dark if self._is_dark else self.colors_light
        cell_size = self._cell_size
        gap = self._gap
        margin_left = self._margin_left
        margin_top = self._margin_top
        hours = 24
        days = 7
        day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        # 绘制小时标签
        font = QFont("Consolas", 8)
        painter.setFont(font)
        painter.setPen(QColor(self._colors["text_muted"]))
        for h in range(0, hours, 3):
            x = margin_left + h * (cell_size + gap)
            painter.drawText(x, margin_top - 8, f"{h:02d}")

        # 绘制热力图格子
        for day in range(days):
            # 日标签
            y = margin_top + day * (cell_size + gap)
            painter.setFont(QFont("Microsoft YaHei", 8))
            painter.drawText(0, y + cell_size - 4, day_labels[day])

            for hour in range(hours):
                x = margin_left + hour * (cell_size + gap)
                level = self.data.get((hour, day), 0)
                color = QColor(colors[min(level, 4)])
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(x, y, cell_size, cell_size, 3, 3)

        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """hover显示时长tooltip"""
        mx, my = event.x(), event.y()
        cell_size = self._cell_size
        gap = self._gap
        margin_left = self._margin_left
        margin_top = self._margin_top
        day_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        for day in range(7):
            for hour in range(24):
                x = margin_left + hour * (cell_size + gap)
                y = margin_top + day * (cell_size + gap)
                if x <= mx <= x + cell_size and y <= my <= y + cell_size:
                    secs = self.raw_seconds.get((hour, day), 0)
                    m = int(secs // 60)
                    level = self.data.get((hour, day), 0)
                    level_names = ["无活动", "轻度", "中度", "高度", "极高"]
                    QToolTip.showText(
                        event.globalPos(),
                        f"<b>{day_labels[day]} {hour:02d}:00</b><br>"
                        f"活跃时长: {m}分钟<br>"
                        f"活跃度: {level_names[min(level, 4)]}"
                    )
                    return
        QToolTip.hideText()

    def sizeHint(self) -> "QSize":
        """返回组件推荐尺寸"""
        return self.minimumSizeHint()


class GoalRingWidget(QWidget):
    """环形进度条绘制组件"""

    def __init__(self, parent_card: QWidget=None) -> None:
        super().__init__(parent_card)
        self._card = parent_card
        self.setFixedSize(120, 120)

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        if not self._card:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        size = 100
        pen_width = 10
        margin = 10
        rect = QRectF(margin, margin, size, size)

        # 背景环
        colors = self._card._colors
        bg_pen = QPen(QColor(colors['bg_sidebar_hover']), pen_width)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # 进度环
        progress = self._card._anim_progress
        if progress > 0:
            # 颜色根据进度变化
            if progress >= 1.0:
                ring_color = QColor(colors['success'])
            elif progress >= 0.7:
                ring_color = QColor(colors['primary'])
            elif progress >= 0.4:
                ring_color = QColor(colors['warning'])
            else:
                ring_color = QColor(colors['danger'])

            progress_pen = QPen(ring_color, pen_width)
            progress_pen.setCapStyle(Qt.RoundCap)
            painter.setPen(progress_pen)
            start_angle = 90 * 16  # 从顶部开始
            span_angle = int(-progress * 360 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # 中心文字 - 百分比
        painter.setPen(QColor(colors['text_primary']))
        font = QFont("Microsoft YaHei", 16, QFont.Bold)
        painter.setFont(font)
        pct = int(progress * 100)
        painter.drawText(rect, Qt.AlignCenter, f"{pct}%")

        painter.end()


class WeekBarWidget(QWidget):
    """周对比柱状图绘制组件"""

    def __init__(self, parent_card: QWidget=None) -> None:
        super().__init__(parent_card)
        self._card = parent_card
        self.setFixedHeight(140)

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        if not self._card:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = self._card._colors

        this_week = self._card._this_week
        last_week = self._card._last_week
        if not this_week and not last_week:
            painter.end()
            return

        n = max(len(this_week), len(last_week), 1)
        margin_left = 5
        margin_right = 5
        margin_top = 18
        margin_bottom = 25
        bar_area_width = self.width() - margin_left - margin_right
        group_width = bar_area_width / n
        bar_width = max(group_width * 0.3, 4)
        gap = max(group_width * 0.1, 2)

        # 找最大值
        max_seconds = 1
        for d in this_week + last_week:
            s = d.get("seconds", 0)
            if s > max_seconds:
                max_seconds = s

        chart_height = self.height() - margin_top - margin_bottom

        # 绘制柱状图
        for i in range(n):
            group_x = margin_left + i * group_width
            self._draw_bar_group(painter, colors, i, group_x, group_width,
                                 bar_width, gap, margin_top, chart_height,
                                 max_seconds, this_week, last_week)

        painter.end()

    def _draw_bar_group(self, painter: QPainter, colors: dict, index: int,
                        group_x: float, group_width: float, bar_width: float,
                        gap: float, margin_top: int, chart_height: int,
                        max_seconds: int, this_week: list, last_week: list) -> None:
        """绘制一组柱状图（上周柱 + 本周柱 + 日标签）"""
        # 上周柱
        if index < len(last_week):
            s = last_week[index].get("seconds", 0)
            h = (s / max_seconds) * chart_height if max_seconds > 0 else 0
            x = group_x + group_width / 2 - bar_width - gap / 2
            y = margin_top + chart_height - h
            color = QColor(colors['bg_sidebar_hover'])
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(h), 2, 2)
            if h > 12:
                painter.setPen(QColor(colors['text_muted']))
                painter.setFont(QFont("Consolas", 7))
                val_min = int(s / 60)
                painter.drawText(int(x - 2), int(y - 3), int(bar_width + 4), 12,
                                 Qt.AlignCenter, f"{val_min}m")

        # 本周柱
        if index < len(this_week):
            s = this_week[index].get("seconds", 0)
            h = (s / max_seconds) * chart_height if max_seconds > 0 else 0
            x = group_x + group_width / 2 + gap / 2
            y = margin_top + chart_height - h
            color = QColor(colors['primary'])
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(h), 2, 2)
            if h > 12:
                painter.setPen(QColor(colors['primary']))
                painter.setFont(QFont("Consolas", 7))
                val_min = int(s / 60)
                painter.drawText(int(x - 2), int(y - 3), int(bar_width + 4), 12,
                                 Qt.AlignCenter, f"{val_min}m")

        # 日标签
        day_name = this_week[index].get("day", "") if index < len(this_week) else ""
        if day_name:
            painter.setPen(QColor(colors['text_muted']))
            painter.setFont(QFont("Microsoft YaHei", 8))
            label_x = group_x + group_width / 2
            painter.drawText(int(label_x - 10), self.height() - 5, day_name)


class HourlyBarWidget(QWidget):
    """每小时分布柱状图绘制组件"""

    def __init__(self, parent_card: QWidget=None) -> None:
        super().__init__(parent_card)
        self._card = parent_card
        self._hover_hour = -1  # 当前hover的小时
        self.setFixedHeight(100)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动时显示tooltip"""
        if not self._card or not self._card._hourly_data:
            QToolTip.hideText()
            return

        # 构建24小时数据映射
        hour_map = {}
        for d in self._card._hourly_data:
            hour_map[d.get("hour", 0)] = d.get("total", 0) or 0

        margin_left = 30
        margin_right = 10
        chart_width = self.width() - margin_left - margin_right
        bar_total_width = chart_width / 24

        mx = event.x()
        my = event.y()

        # 计算hover的小时
        if mx < margin_left or mx > self.width() - margin_right:
            if self._hover_hour != -1:
                self._hover_hour = -1
                QToolTip.hideText()
                self.update()
            return

        hour = int((mx - margin_left) / bar_total_width)
        if 0 <= hour < 24:
            if hour != self._hover_hour:
                self._hover_hour = hour
                self.update()
            total = hour_map.get(hour, 0)
            minutes = int(total / 60)
            QToolTip.showText(
                event.globalPos(),
                f"<b>{hour:02d}:00 - {hour+1:02d}:00</b><br>活跃: {minutes} 分钟"
            )
        else:
            if self._hover_hour != -1:
                self._hover_hour = -1
                QToolTip.hideText()
                self.update()

    def leaveEvent(self, event: QEvent) -> None:
        """鼠标离开事件重写"""
        self._hover_hour = -1
        QToolTip.hideText()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        if not self._card:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = self._card._colors

        data = self._card._hourly_data
        if not data:
            painter.setPen(QColor(colors['text_muted']))
            font = QFont("Microsoft YaHei", 10)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            painter.end()
            return

        # 构建24小时数据映射
        hour_map = {}
        for d in data:
            hour_map[d.get("hour", 0)] = d.get("total", 0) or 0

        margin_left = 30
        margin_right = 10
        margin_top = 5
        margin_bottom = 20
        chart_width = self.width() - margin_left - margin_right
        chart_height = self.height() - margin_top - margin_bottom
        bar_width = max(chart_width / 24 - 2, 3)

        max_total = max(hour_map.values()) if hour_map else 1
        if max_total == 0:
            max_total = 1

        # Y轴标签
        painter.setPen(QColor(colors['text_muted']))
        font = QFont("Consolas", 7)
        painter.setFont(font)
        max_min = int(max_total / 60)
        for i, val in enumerate([0, max_min // 2, max_min]):
            y = margin_top + chart_height - (val * 60 / max_total) * chart_height if max_total > 0 else margin_top + chart_height
            painter.drawText(0, int(y) + 4, f"{val}m")

        # 绘制柱状图
        for h in range(24):
            total = hour_map.get(h, 0)
            x = margin_left + h * (chart_width / 24)
            bar_h = (total / max_total) * chart_height if max_total > 0 else 0
            y = margin_top + chart_height - bar_h

            # 根据活跃度渐变色
            intensity = total / max_total if max_total > 0 else 0
            if intensity > 0.7:
                bar_color = QColor(colors['primary'])
            elif intensity > 0.3:
                bar_color = QColor(colors['success'])
            else:
                bar_color = QColor(colors['primary'])
                bar_color.setAlpha(int(40 + intensity * 215))

            # hover高亮效果
            if h == self._hover_hour:
                bar_color = bar_color.lighter(130)

            painter.setBrush(QBrush(bar_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_h), 1, 1)

            # X轴标签（每3小时）
            if h % 3 == 0:
                painter.setPen(QColor(colors['text_muted']))
                painter.setFont(QFont("Consolas", 7))
                painter.drawText(int(x - 4), self.height() - 4, f"{h:02d}")

        painter.end()