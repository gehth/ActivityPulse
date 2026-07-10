"""异常告警对话框 - 展示异常行为告警列表，支持查看/忽略/全部已读"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from gui.themes import get_colors, HoverButton

# 告警类型图标和颜色
ALERT_TYPE_CONFIG = {
    "continuous_use": {
        "icon": "⏱️",
        "color": "#F59E0B",
        "label": "连续使用超时",
    },
    "late_night": {
        "icon": "🌙",
        "color": "#8B5CF6",
        "label": "深夜异常活跃",
    },
    "daily_deviation": {
        "icon": "📈",
        "color": "#EF4444",
        "label": "使用时长偏离",
    },
    "no_break": {
        "icon": "🧘",
        "color": "#F97316",
        "label": "长时间无休息",
    },
}

SEVERITY_CONFIG = {
    "info": {"icon": "ℹ️", "bg": "#DBEAFE", "border": "#93C5FD"},
    "warning": {"icon": "⚠️", "bg": "#FEF3C7", "border": "#FCD34D"},
    "critical": {"icon": "🚨", "bg": "#FEE2E2", "border": "#FCA5A5"},
}


class AlertCard(QFrame):
    """单条告警卡片"""

    dismissed = pyqtSignal(int)  # alert_id
    read_clicked = pyqtSignal(int)  # alert_id

    def __init__(self, alert: dict, parent=None):
        super().__init__(parent)
        self.alert_id = alert.get("id", 0)
        self._alert = alert
        self._is_dark = False
        self._setup_ui()

    def _setup_ui(self):
        alert = self._alert
        alert_type = alert.get("alert_type", "unknown")
        severity = alert.get("severity", "warning")
        is_read = alert.get("is_read", 0)

        type_cfg = ALERT_TYPE_CONFIG.get(alert_type, {"icon": "❓", "color": "#6B7280", "label": alert_type})
        sev_cfg = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["warning"])

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            AlertCard {{
                background: {sev_cfg['bg']};
                border: 1px solid {sev_cfg['border']};
                border-radius: 8px;
                padding: 12px;
                margin: 4px 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 10, 12, 10)

        layout.addLayout(self._create_title_layout(alert, type_cfg, sev_cfg, is_read))

        # 描述
        desc = alert.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 12px; color: #4B5563; line-height: 1.4;")
            layout.addWidget(desc_label)

        layout.addLayout(self._create_bottom_layout(alert))

    def _create_title_layout(self, alert, type_cfg, sev_cfg, is_read):
        """创建标题行（类型图标+标题+严重程度+已读标记）"""
        title_layout = QHBoxLayout()

        type_icon = QLabel(type_cfg["icon"])
        type_icon.setStyleSheet("font-size: 18px;")
        title_layout.addWidget(type_icon)

        title_text = QLabel(alert.get("title", "异常告警"))
        title_text.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {type_cfg['color']};")
        title_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title_layout.addWidget(title_text)

        sev_label = QLabel(sev_cfg["icon"])
        sev_label.setStyleSheet("font-size: 16px;")
        title_layout.addWidget(sev_label)

        if is_read:
            read_badge = QLabel("已读")
            read_badge.setStyleSheet("font-size: 11px; color: #9CA3AF; border: 1px solid #D1D5DB; border-radius: 3px; padding: 1px 4px;")
            title_layout.addWidget(read_badge)

        return title_layout

    def _create_bottom_layout(self, alert):
        """创建底部信息行（检测时间+忽略按钮）"""
        bottom_layout = QHBoxLayout()

        detected_at = alert.get("detected_at", "")
        if detected_at:
            time_label = QLabel(f"🕐 {detected_at}")
            time_label.setStyleSheet("font-size: 11px; color: #9CA3AF;")
            bottom_layout.addWidget(time_label)

        bottom_layout.addStretch()

        dismiss_btn = QPushButton("忽略")
        dismiss_btn.setFixedSize(60, 26)
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                color: #6B7280;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #F3F4F6;
                border-color: #9CA3AF;
            }
        """)
        dismiss_btn.clicked.connect(lambda: self.dismissed.emit(self.alert_id))
        bottom_layout.addWidget(dismiss_btn)

        return bottom_layout

    def set_dark_mode(self, is_dark: bool):
        """设置暗色模式"""
        self._is_dark = is_dark
        # 暗色模式样式覆盖
        if is_dark:
            severity = self._alert.get("severity", "warning")
            sev_cfg = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["warning"])
            dark_bg = {
                "info": "#1E3A5F",
                "warning": "#3D2E0A",
                "critical": "#3D1A1A",
            }.get(severity, "#2D2D2D")
            dark_border = {
                "info": "#2563EB",
                "warning": "#D97706",
                "critical": "#DC2626",
            }.get(severity, "#4B5563")
            self.setStyleSheet(f"""
                AlertCard {{
                    background: {dark_bg};
                    border: 1px solid {dark_border};
                    border-radius: 8px;
                    padding: 12px;
                    margin: 4px 0px;
                }}
            """)
            # 更新子控件颜色
            for child in self.findChildren(QLabel):
                style = child.styleSheet()
                if "color: #4B5563" in style:
                    style = style.replace("color: #4B5563", "color: #D1D5DB")
                if "color: #9CA3AF" in style:
                    pass  # 保持灰色
                if "color: #6B7280" in style:
                    style = style.replace("color: #6B7280", "color: #9CA3AF")
                child.setStyleSheet(style)


class AnomalyAlertDialog(QDialog):
    """异常告警中心对话框

    展示所有异常行为告警，支持：
    - 查看告警详情
    - 忽略单条告警
    - 全部标记已读
    - 暗色模式
    """

    alerts_changed = pyqtSignal()  # 告警状态变更信号

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._is_dark = False
        self._cards = []
        self._setup_ui()
        self._load_alerts()

    def _setup_ui(self):
        self.setWindowTitle("异常行为告警中心")
        self.setMinimumSize(520, 480)
        self.resize(560, 560)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 16, 20, 16)

        main_layout.addLayout(self._create_header())
        main_layout.addLayout(self._create_action_bar())
        main_layout.addWidget(self._create_alert_list(), 1)

        # 底部关闭按钮
        close_btn = HoverButton("关闭")
        close_btn.setFixedHeight(34)
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn, 0, Qt.AlignRight)

    def _create_header(self):
        """创建标题行"""
        header_layout = QHBoxLayout()
        title = QLabel("🚨 异常行为告警中心")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("font-size: 12px; color: #6B7280;")
        header_layout.addStretch()
        header_layout.addWidget(self._count_label)
        return header_layout

    def _create_action_bar(self):
        """创建操作按钮行（全部已读+刷新+筛选）"""
        btn_layout = QHBoxLayout()

        self._mark_all_read_btn = HoverButton("✓ 全部已读")
        self._mark_all_read_btn.setFixedHeight(30)
        self._mark_all_read_btn.clicked.connect(self._mark_all_read)
        btn_layout.addWidget(self._mark_all_read_btn)

        self._refresh_btn = HoverButton("🔄 刷新")
        self._refresh_btn.setFixedHeight(30)
        self._refresh_btn.clicked.connect(self._load_alerts)
        btn_layout.addWidget(self._refresh_btn)

        btn_layout.addStretch()

        self._filter_all_btn = HoverButton("全部")
        self._filter_all_btn.setFixedHeight(28)
        self._filter_all_btn.setCheckable(True)
        self._filter_all_btn.setChecked(True)
        self._filter_all_btn.clicked.connect(lambda: self._set_filter("all"))
        btn_layout.addWidget(self._filter_all_btn)

        self._filter_unread_btn = HoverButton("未读")
        self._filter_unread_btn.setFixedHeight(28)
        self._filter_unread_btn.setCheckable(True)
        self._filter_unread_btn.clicked.connect(lambda: self._set_filter("unread"))
        btn_layout.addWidget(self._filter_unread_btn)

        return btn_layout

    def _create_alert_list(self):
        """创建告警列表滚动区域"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: 1px solid #E5E7EB; border-radius: 8px; background: #F9FAFB; }
        """)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(4)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        return scroll

    def _set_filter(self, filter_type: str):
        """设置筛选模式"""
        self._filter_all_btn.setChecked(filter_type == "all")
        self._filter_unread_btn.setChecked(filter_type == "unread")
        self._current_filter = filter_type
        self._load_alerts()

    def _load_alerts(self):
        """加载告警列表"""
        # 清空现有卡片
        for card in self._cards:
            self._list_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # 移除空提示
        for i in range(self._list_layout.count()):
            item = self._list_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, QLabel) and w.property("empty_hint"):
                    self._list_layout.removeWidget(w)
                    w.deleteLater()

        unread_only = getattr(self, '_current_filter', 'all') == 'unread'
        alerts = self.db.get_anomaly_alerts(limit=50, unread_only=unread_only)
        unread_count = self.db.get_unread_alert_count()

        self._count_label.setText(f"未读: {unread_count}  |  总计: {len(alerts)}")

        if not alerts:
            hint = QLabel("✅ 暂无异常告警，一切正常！")
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet("font-size: 14px; color: #9CA3AF; padding: 40px;")
            hint.setProperty("empty_hint", True)
            # 插入到stretch之前
            self._list_layout.insertWidget(0, hint)
            return

        for alert in alerts:
            card = AlertCard(alert)
            card.dismissed.connect(self._on_dismiss)
            card.set_dark_mode(self._is_dark)
            # 插入到stretch之前
            idx = self._list_layout.count() - 1
            self._list_layout.insertWidget(idx, card)
            self._cards.append(card)

    def _on_dismiss(self, alert_id: int):
        """忽略告警"""
        self.db.dismiss_alert(alert_id)
        self._load_alerts()
        self.alerts_changed.emit()

    def _mark_all_read(self):
        """全部标记已读"""
        self.db.mark_all_alerts_read()
        self._load_alerts()
        self.alerts_changed.emit()

    def set_dark_mode(self, is_dark: bool):
        """设置暗色模式"""
        self._is_dark = is_dark
        colors = get_colors(is_dark)
        self.setStyleSheet(f"""
            QDialog {{ background: {colors['bg_primary']}; }}
            QLabel {{ color: {colors['text_primary']}; }}
        """)
        for card in self._cards:
            card.set_dark_mode(is_dark)