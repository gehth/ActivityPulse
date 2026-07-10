"""应用图标工厂 - 生成应用图标（渐变圆角矩形 + 时钟 + 活动线条）

设计理念：时钟代表时间追踪，三条活动线代表行为记录，
蓝紫渐变体现专业感和科技感。
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QPen, QPainterPath, QFont


def create_app_icon() -> QIcon:
    """生成应用图标 - 渐变圆角矩形 + 时钟+活动线条"""
    sizes = [64, 48, 32, 16]
    icon = QIcon()

    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)

        margin = max(1, size // 16)
        rect_size = size - margin * 2
        radius = max(4, size // 5)

        # 渐变背景 - 蓝紫渐变
        gradient = QLinearGradient(margin, margin, margin + rect_size, margin + rect_size)
        gradient.setColorAt(0.0, QColor("#3B82F6"))  # 蓝
        gradient.setColorAt(1.0, QColor("#8B5CF6"))  # 紫
        p.setBrush(gradient)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(margin, margin, rect_size, rect_size, radius, radius)

        # 根据尺寸决定绘制细节
        center_x = size / 2
        center_y = size / 2

        if size >= 48:
            # 大尺寸：绘制时钟 + 活动线条

            # 时钟外圈
            clock_r = rect_size * 0.30
            p.setPen(QPen(QColor(255, 255, 255, 180), max(1, size // 32)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(center_x - clock_r), int(center_y - clock_r * 0.6),
                          int(clock_r * 2), int(clock_r * 2))

            # 时钟指针 - 时针
            p.setPen(QPen(QColor("#FFFFFF"), max(1, size // 24), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(center_x), int(center_y - clock_r * 0.6),
                       int(center_x), int(center_y - clock_r * 0.6 - clock_r * 0.35))

            # 时钟指针 - 分针
            p.setPen(QPen(QColor("#FFFFFF"), max(1, size // 40), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(center_x), int(center_y - clock_r * 0.6),
                       int(center_x + clock_r * 0.25), int(center_y - clock_r * 0.6 + clock_r * 0.15))

            # 中心点
            p.setBrush(QColor("#FFFFFF"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(center_x - 2), int(center_y - clock_r * 0.6 - 2), 4, 4)

            # 三条活动线 - 代表行为记录
            line_y_start = center_y + rect_size * 0.08
            line_heights = [0.20, 0.12, 0.16]  # 不同高度
            line_width = rect_size * 0.14
            gap = rect_size * 0.04
            total_w = line_width * 3 + gap * 2
            start_x = center_x - total_w / 2

            for i, h in enumerate(line_heights):
                x = start_x + i * (line_width + gap)
                lh = rect_size * h
                # 圆角矩形条
                path = QPainterPath()
                bar_r = max(1, size // 32)
                path.addRoundedRect(float(x), float(line_y_start + (rect_size * 0.20 - lh)),
                                    float(line_width), float(lh), float(bar_r), float(bar_r))
                p.fillPath(path, QColor(255, 255, 255, 200))

        elif size >= 32:
            # 中尺寸：简化时钟 + 活动线
            clock_r = rect_size * 0.25
            p.setPen(QPen(QColor(255, 255, 255, 180), max(1, size // 32)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(center_x - clock_r), int(center_y - clock_r * 0.7),
                          int(clock_r * 2), int(clock_r * 2))

            # 简化指针
            p.setPen(QPen(QColor("#FFFFFF"), max(1, size // 24), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(center_x), int(center_y - clock_r * 0.7),
                       int(center_x), int(center_y - clock_r * 0.7 - clock_r * 0.4))

            # 活动线
            line_y = center_y + rect_size * 0.05
            line_width = rect_size * 0.16
            line_heights = [0.18, 0.10, 0.14]
            gap = rect_size * 0.04
            total_w = line_width * 3 + gap * 2
            start_x = center_x - total_w / 2

            for i, h in enumerate(line_heights):
                x = start_x + i * (line_width + gap)
                lh = rect_size * h
                p.setBrush(QColor(255, 255, 255, 200))
                p.setPen(Qt.NoPen)
                p.drawRoundedRect(int(x), int(line_y + (rect_size * 0.18 - lh)),
                                  int(line_width), int(lh), 2, 2)
        else:
            # 小尺寸：只显示"记"字
            p.setPen(QColor("#FFFFFF"))
            font_size = max(6, int(size * 0.55))
            p.setFont(QFont("Microsoft YaHei", font_size, QFont.Bold))
            p.drawText(pixmap.rect(), Qt.AlignCenter, "记")

        p.end()
        icon.addPixmap(pixmap)

    return icon