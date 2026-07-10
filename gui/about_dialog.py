"""关于对话框 - 自定义美化弹窗"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont


class AboutDialog(QDialog):
    """关于对话框"""

    # 版本号常量，与main_window.APP_VERSION保持同步
    APP_VERSION = "1.0"

    def __init__(self, parent=None, version: str = None):
        super().__init__(parent)
        self._version = version or self.APP_VERSION
        self.setWindowTitle("关于")
        self.setFixedSize(420, 340)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 24)

        # 应用图标
        icon_label = QLabel()
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#3B82F6"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 12, 12)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        p.drawText(pixmap.rect(), Qt.AlignCenter, "记")
        p.end()
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        # 应用名称
        name_label = QLabel(f"行为记录 v{self._version}")
        name_label.setObjectName("page_title")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        # 描述
        desc_label = QLabel("一款电脑行为记录与分析工具")
        desc_label.setObjectName("section_desc")
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)

        # 功能列表
        features = QLabel("应用使用追踪 · 键鼠操作记录 · 屏幕截图")
        features.setObjectName("section_desc")
        features.setAlignment(Qt.AlignCenter)
        layout.addWidget(features)

        # 分隔线
        separator = QFrame()
        separator.setObjectName("separator")
        layout.addWidget(separator)

        # 隐私声明
        privacy_label = QLabel("🛡 所有数据均存储于本地，不会上传至任何服务器")
        privacy_label.setAlignment(Qt.AlignCenter)
        privacy_label.setStyleSheet("color: #10B981; font-size: 12px; font-weight: bold;")
        layout.addWidget(privacy_label)

        # 技术信息
        tech_label = QLabel("基于 Python · PyQt5 · SQLite 构建")
        tech_label.setObjectName("section_desc")
        tech_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tech_label)

        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("确定")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)