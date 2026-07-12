"""关于对话框 - 自定义美化弹窗"""

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont

from gui.themes import get_colors
from gui.components.base_dialog import BaseDialog


class AboutDialog(BaseDialog):
    """关于对话框"""

    # 版本号常量，与main_window.APP_VERSION保持同步
    APP_VERSION = "1.0"

    def __init__(self, parent: QWidget=None, version: str = None) -> None:
        super().__init__(is_dark=False, parent=parent, dialog_style="")
        self._version = version or self.APP_VERSION
        self.setWindowTitle("关于")
        self.setFixedSize(420, 340)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 24)

        layout.addWidget(self._create_icon())
        layout.addWidget(self._create_title_section())
        layout.addWidget(self._create_separator())
        layout.addWidget(self._create_privacy_label())
        layout.addWidget(self._create_tech_label())
        layout.addLayout(self._create_close_button())

    def _create_icon(self) -> QLabel:
        """创建应用图标"""
        colors = self._colors
        icon_label = QLabel()
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(colors["primary"]))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 12, 12)
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        p.drawText(pixmap.rect(), Qt.AlignCenter, "记")
        p.end()
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label = icon_label
        return icon_label

    def _create_title_section(self) -> QWidget:
        """创建标题区域（名称+描述+功能列表）"""
        widget = QWidget()
        vbox = QVBoxLayout(widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)

        name_label = QLabel(f"行为记录 v{self._version}")
        name_label.setObjectName("page_title")
        name_label.setAlignment(Qt.AlignCenter)
        vbox.addWidget(name_label)

        desc_label = QLabel("一款电脑行为记录与分析工具")
        desc_label.setObjectName("section_desc")
        desc_label.setAlignment(Qt.AlignCenter)
        vbox.addWidget(desc_label)

        features = QLabel("应用使用追踪 · 键鼠操作记录 · 屏幕截图")
        features.setObjectName("section_desc")
        features.setAlignment(Qt.AlignCenter)
        vbox.addWidget(features)
        return widget

    def _create_separator(self) -> QFrame:
        """创建分隔线"""
        separator = QFrame()
        separator.setObjectName("separator")
        return separator

    def _create_privacy_label(self) -> QLabel:
        """创建隐私声明标签"""
        privacy_label = QLabel("🛡 所有数据均存储于本地，不会上传至任何服务器")
        privacy_label.setAlignment(Qt.AlignCenter)
        privacy_label.setStyleSheet(f"color: {self._colors['success']}; font-size: 12px; font-weight: bold;")
        self._privacy_label = privacy_label
        return privacy_label

    def _create_tech_label(self) -> QLabel:
        """创建技术信息标签"""
        tech_label = QLabel("基于 Python · PyQt5 · SQLite 构建")
        tech_label.setObjectName("section_desc")
        tech_label.setAlignment(Qt.AlignCenter)
        return tech_label

    def _create_close_button(self) -> QHBoxLayout:
        """创建关闭按钮行"""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("确定")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        btn_layout.addStretch()
        return btn_layout

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        super().set_theme(is_dark)
        colors = self._colors
        # 更新隐私声明颜色
        if hasattr(self, '_privacy_label'):
            self._privacy_label.setStyleSheet(
                f"color: {colors['success']}; font-size: 12px; font-weight: bold;"
            )
        # 重绘图标
        if hasattr(self, '_icon_label'):
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.transparent)
            p = QPainter(pixmap)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor(colors["primary"]))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(4, 4, 56, 56, 12, 12)
            p.setPen(QColor("#FFFFFF"))
            p.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
            p.drawText(pixmap.rect(), Qt.AlignCenter, "记")
            p.end()
            self._icon_label.setPixmap(pixmap)