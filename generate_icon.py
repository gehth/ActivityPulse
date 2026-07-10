"""生成应用图标 - 输出app.ico和各尺寸PNG"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QBuffer, QIODevice
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor, QLinearGradient, QPen, QPainterPath


def create_app_icon() -> QIcon:
    """生成应用图标 - 渐变圆角矩形 + 时钟+活动线条"""
    sizes = [256, 64, 48, 32, 16]
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
        gradient.setColorAt(0.0, QColor("#3B82F6"))
        gradient.setColorAt(1.0, QColor("#8B5CF6"))
        p.setBrush(gradient)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(margin, margin, rect_size, rect_size, radius, radius)

        center_x = size / 2
        center_y = size / 2

        if size >= 48:
            # 时钟外圈
            clock_r = rect_size * 0.30
            p.setPen(QPen(QColor(255, 255, 255, 180), max(1, size // 32)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(center_x - clock_r), int(center_y - clock_r * 0.6),
                          int(clock_r * 2), int(clock_r * 2))

            # 时针
            p.setPen(QPen(QColor("#FFFFFF"), max(1, size // 24), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(center_x), int(center_y - clock_r * 0.6),
                       int(center_x), int(center_y - clock_r * 0.6 - clock_r * 0.35))

            # 分针
            p.setPen(QPen(QColor("#FFFFFF"), max(1, size // 40), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(center_x), int(center_y - clock_r * 0.6),
                       int(center_x + clock_r * 0.25), int(center_y - clock_r * 0.6 + clock_r * 0.15))

            # 中心点
            p.setBrush(QColor("#FFFFFF"))
            p.setPen(Qt.NoPen)
            dot_r = max(2, size // 16)
            p.drawEllipse(int(center_x - dot_r), int(center_y - clock_r * 0.6 - dot_r), dot_r * 2, dot_r * 2)

            # 三条活动线
            line_y_start = center_y + rect_size * 0.08
            line_heights = [0.20, 0.12, 0.16]
            line_width = rect_size * 0.14
            gap = rect_size * 0.04
            total_w = line_width * 3 + gap * 2
            start_x = center_x - total_w / 2

            for i, h in enumerate(line_heights):
                x = start_x + i * (line_width + gap)
                lh = rect_size * h
                path = QPainterPath()
                bar_r = max(1, size // 32)
                path.addRoundedRect(float(x), float(line_y_start + (rect_size * 0.20 - lh)),
                                    float(line_width), float(lh), float(bar_r), float(bar_r))
                p.fillPath(path, QColor(255, 255, 255, 200))

        elif size >= 32:
            clock_r = rect_size * 0.25
            p.setPen(QPen(QColor(255, 255, 255, 180), max(1, size // 32)))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(int(center_x - clock_r), int(center_y - clock_r * 0.7),
                          int(clock_r * 2), int(clock_r * 2))
            p.setPen(QPen(QColor("#FFFFFF"), max(1, size // 24), Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(center_x), int(center_y - clock_r * 0.7),
                       int(center_x), int(center_y - clock_r * 0.7 - clock_r * 0.4))

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
            p.setPen(QColor("#FFFFFF"))
            font_size = max(6, int(size * 0.55))
            p.setFont(QFont("Microsoft YaHei", font_size, QFont.Bold))
            p.drawText(pixmap.rect(), Qt.AlignCenter, "记")

        p.end()
        icon.addPixmap(pixmap)

        # 同时保存PNG
        if size in [256, 64]:
            png_path = os.path.join(os.path.dirname(__file__), f"app_icon_{size}.png")
            pixmap.save(png_path, "PNG")
            print(f"已保存: {png_path}")

    return icon


if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon = create_app_icon()

    # 保存ICO (使用256x256作为最大尺寸)
    ico_path = os.path.join(os.path.dirname(__file__), "app.ico")
    # PyQt5 QIcon不支持直接保存ico，用Pillow转换
    try:
        from PIL import Image
        import io
        # 获取256x256的pixmap
        pixmap256 = icon.pixmap(256, 256)
        buffer = QBuffer()
        buffer.open(QIODevice.ReadWrite)
        pixmap256.save(buffer, "PNG")
        buffer.seek(0)
        # QBuffer -> bytes -> Pillow
        img_data = bytes(buffer.data().data())
        img = Image.open(io.BytesIO(img_data))
        # 生成多尺寸ICO
        sizes_ico = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        imgs = []
        for s in sizes_ico:
            imgs.append(img.resize(s, Image.LANCZOS))
        imgs[0].save(ico_path, format='ICO', sizes=sizes_ico, append_images=imgs[1:])
        print(f"已保存ICO: {ico_path}")
    except ImportError:
        # 没有Pillow，保存为PNG
        png_path = os.path.join(os.path.dirname(__file__), "app.ico.png")
        icon.pixmap(256, 256).save(png_path, "PNG")
        print(f"Pillow未安装，已保存PNG: {png_path}")

    print("图标生成完成！")