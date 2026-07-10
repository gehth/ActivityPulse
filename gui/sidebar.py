"""侧边栏导航组件"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from gui.themes import HoverButton, get_colors


class StatusIndicator(QWidget):
    """带呼吸动画的状态指示灯"""

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(24)
        self._recording = False
        self._opacity = 1.0
        self._breathing_in = True
        self._is_dark = False

        # 呼吸动画定时器
        self._breath_timer = QTimer(self)
        self._breath_timer.timeout.connect(self._breath_tick)
        self._breath_timer.setInterval(50)  # 50ms刷新

    def set_recording(self, recording: bool) -> None:
        """设置录制状态指示"""
        self._recording = recording
        self.update()
        if recording:
            self._breath_timer.start()
        else:
            self._breath_timer.stop()
            self._opacity = 1.0
            self.update()

    def set_theme(self, is_dark: bool) -> None:
        """设置主题"""
        self._is_dark = is_dark
        self.update()

    def _breath_tick(self) -> None:
        """呼吸动画步进"""
        step = 0.03
        if self._breathing_in:
            self._opacity += step
            if self._opacity >= 1.0:
                self._opacity = 1.0
                self._breathing_in = False
        else:
            self._opacity -= step
            if self._opacity <= 0.3:
                self._opacity = 0.3
                self._breathing_in = True
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        from PyQt5.QtGui import QPainter, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = get_colors("dark" if self._is_dark else "light")

        # 状态文字
        if self._recording:
            color = QColor(colors["success"])
            color.setAlphaF(self._opacity)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(8, 5, 14, 14)

            painter.setPen(QColor(colors["success"]))
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(28, 17, "记录中")
        else:
            painter.setBrush(QBrush(QColor(colors["text_muted"])))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(8, 5, 14, 14)

            painter.setPen(QColor(colors["text_muted"]))
            painter.setFont(QFont("Microsoft YaHei", 11))
            painter.drawText(28, 17, "已暂停")

        painter.end()


class NavButton(QPushButton):
    """侧边栏导航按钮"""

    def __init__(self, icon_text: str, label: str, page_index: int) -> None:
        super().__init__()
        self.page_index = page_index
        self.icon_text = icon_text
        self.label_text = label
        self._active = False
        self._collapsed = False

        self.setObjectName("nav_button")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(42)
        self._update_text()

    def _update_text(self) -> None:
        """更新显示文本"""
        if self._collapsed:
            self.setText(self.icon_text)
            self.setToolTip(self.label_text)
        else:
            self.setText(f"  {self.icon_text}  {self.label_text}")
            self.setToolTip("")

    @property
    def active(self) -> bool:
        """获取按钮激活状态"""
        return self._active

    def set_active(self, active: bool) -> None:
        """设置激活状态"""
        self._active = active
        self.setObjectName("nav_button_active" if active else "nav_button")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_collapsed(self, collapsed: bool) -> None:
        """设置折叠/展开状态"""
        self._collapsed = collapsed
        self._update_text()
        if collapsed:
            self.setFixedWidth(44)
        else:
            self.setFixedWidth(200)


class Sidebar(QFrame):
    """侧边栏导航"""

    page_changed = pyqtSignal(int)
    toggle_monitor = pyqtSignal(bool)
    toggle_privacy = pyqtSignal(bool)
    settings_clicked = pyqtSignal()
    alert_clicked = pyqtSignal()

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self._collapsed = False
        self._monitoring = False
        self._privacy_mode = False
        self._nav_buttons = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        self.setObjectName("sidebar")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._create_brand_area())
        layout.addWidget(self._create_nav_area())

        # 分隔线
        separator = QFrame()
        separator.setObjectName("separator")
        layout.addWidget(separator)

        layout.addWidget(self._create_bottom_area())

    def _create_brand_area(self) -> None:
        """创建品牌区"""
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(16, 20, 16, 16)
        self.brand_icon = QLabel("📊")
        self.brand_icon.setStyleSheet("font-size: 24px;")
        brand_layout.addWidget(self.brand_icon)

        self.brand_label = QLabel("行为记录")
        self.brand_label.setObjectName("brand_label")
        brand_layout.addWidget(self.brand_label)
        brand_layout.addStretch()

        # 折叠按钮
        self.btn_collapse = HoverButton("◀")
        self.btn_collapse.setObjectName("btn_outline")
        self.btn_collapse.setFixedSize(28, 28)
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        brand_layout.addWidget(self.btn_collapse)

        brand_container = QWidget()
        brand_container.setObjectName("brand_area")
        brand_container.setLayout(brand_layout)
        return brand_container

    def _create_nav_area(self) -> None:
        """创建导航按钮区"""
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(2)

        pages = [
            ("📊", "仪表盘", 0),
            ("🕐", "时间轴", 1),
            ("📈", "统计洞察", 2),
            ("🏷️", "分类管理", 3),
            ("📸", "截图浏览", 4),
        ]

        for icon, label, idx in pages:
            btn = NavButton(icon, label, idx)
            btn.clicked.connect(lambda checked, i=idx: self._on_nav_clicked(i))
            self._nav_buttons.append(btn)
            nav_layout.addWidget(btn)

        # 默认选中第一个
        self._nav_buttons[0].set_active(True)
        nav_layout.addStretch()
        return nav_container

    def _create_bottom_area(self) -> None:
        """创建底部操作区"""
        bottom_container = QWidget()
        bottom_container.setObjectName("sidebar_bottom")
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.setSpacing(8)

        # 状态指示
        self.status_indicator = StatusIndicator()
        bottom_layout.addWidget(self.status_indicator)

        # 暂停/恢复按钮
        self.btn_toggle_monitor = HoverButton("▶ 开始记录")
        self.btn_toggle_monitor.setObjectName("btn_outline")
        self.btn_toggle_monitor.clicked.connect(self._on_toggle_monitor)
        bottom_layout.addWidget(self.btn_toggle_monitor)

        # 隐私模式按钮
        self.btn_privacy = HoverButton("🔒 隐私模式")
        self.btn_privacy.setObjectName("btn_outline")
        self.btn_privacy.clicked.connect(self._on_toggle_privacy)
        bottom_layout.addWidget(self.btn_privacy)

        # 设置按钮
        self.btn_settings = HoverButton("⚙ 设置")
        self.btn_settings.setObjectName("btn_outline")
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        bottom_layout.addWidget(self.btn_settings)

        # 告警指示器
        self._alert_badge = QLabel("")
        self._alert_badge.setObjectName("alert_badge")
        self._alert_badge.hide()
        self._alert_btn = HoverButton("🚨 告警")
        self._alert_btn.setObjectName("btn_outline")
        self._alert_btn.clicked.connect(self.alert_clicked.emit)
        alert_row = QHBoxLayout()
        alert_row.addWidget(self._alert_btn)
        alert_row.addWidget(self._alert_badge)
        alert_row.addStretch()
        bottom_layout.addLayout(alert_row)

        return bottom_container

    def _on_nav_clicked(self, index: int) -> None:
        """导航按钮点击回调"""
        for btn in self._nav_buttons:
            btn.set_active(btn.page_index == index)
        self.page_changed.emit(index)

    def _set_active(self, index: int) -> None:
        """程序化设置活动页面（不触发信号，用于跳转）"""
        for btn in self._nav_buttons:
            btn.set_active(btn.page_index == index)

    def _on_toggle_monitor(self) -> None:
        """切换监控状态回调"""
        self._monitoring = not self._monitoring
        self._update_monitor_ui()
        self.toggle_monitor.emit(self._monitoring)

    def _on_toggle_privacy(self) -> None:
        """切换隐私模式回调"""
        self._privacy_mode = not self._privacy_mode
        if self._privacy_mode:
            self.btn_privacy.setText("🔓 退出隐私")
            self.btn_privacy.setObjectName("btn_danger")
        else:
            self.btn_privacy.setText("🔒 隐私模式")
            self.btn_privacy.setObjectName("btn_outline")
        self.btn_privacy.style().unpolish(self.btn_privacy)
        self.btn_privacy.style().polish(self.btn_privacy)
        self.toggle_privacy.emit(self._privacy_mode)

    def _update_monitor_ui(self) -> None:
        """更新监控状态UI"""
        if self._monitoring:
            self.status_indicator.set_recording(True)
            self.btn_toggle_monitor.setText("⏸ 暂停记录")
        else:
            self.status_indicator.set_recording(False)
            self.btn_toggle_monitor.setText("▶ 开始记录")

    def toggle_collapse(self) -> None:
        """切换折叠/展开状态"""
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.setObjectName("sidebar_collapsed")
            self.brand_label.hide()
            self.btn_collapse.setText("▶")
            # 折叠时隐藏底部按钮文字，只显示图标
            self.btn_toggle_monitor.setText("▶")
            self.btn_privacy.setText("🔒")
            self.btn_settings.setText("⚙")
            self._alert_btn.setText("🚨")
            self._alert_badge.hide()
        else:
            self.setObjectName("sidebar")
            self.brand_label.show()
            self.btn_collapse.setText("◀")
            # 展开时恢复按钮文字
            self.btn_toggle_monitor.setText("⏸ 暂停记录" if self._monitoring else "▶ 开始记录")
            self.btn_privacy.setText("🔓 退出隐私" if self._privacy_mode else "🔒 隐私模式")
            self.btn_settings.setText("⚙ 设置")
            self._alert_btn.setText("🚨 告警")
            # 恢复badge显示（如果有未读告警）
            if self._alert_badge.text():
                self._alert_badge.show()

        for btn in self._nav_buttons:
            btn.set_collapsed(self._collapsed)

        self.style().unpolish(self)
        self.style().polish(self)

    def set_monitoring(self, monitoring: bool) -> None:
        """设置监控运行状态"""
        self._monitoring = monitoring
        self._update_monitor_ui()

    def update_anomaly_badge(self, count: int) -> None:
        """更新告警badge数量"""
        if count > 0:
            self._alert_badge.setText(str(count) if count < 100 else "99+")
            self._alert_badge.show()
        else:
            self._alert_badge.hide()

    def set_theme(self, is_dark: bool) -> None:
        """主题切换时更新HoverButton阴影"""
        c = get_colors(is_dark)
        # 更新告警badge样式
        self._alert_badge.setStyleSheet(f"""
            QLabel {{
                background: {c['danger']};
                color: white;
                border-radius: 9px;
                font-size: 11px;
                font-weight: bold;
                padding: 1px 5px;
                min-width: 18px;
                max-height: 18px;
                qproperty-alignment: AlignCenter;
            }}
        """)
        # 更新状态指示器主题
        self.status_indicator.set_theme(is_dark)
        for btn in [self.btn_collapse, self.btn_toggle_monitor,
                     self.btn_privacy, self.btn_settings, self._alert_btn]:
            if hasattr(btn, 'set_theme'):
                btn.set_theme(is_dark)