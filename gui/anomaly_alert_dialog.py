"""异常告警对话框 - 展示异常行为告警列表，支持查看/忽略/全部已读"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from gui.themes import get_colors, HoverButton, QSS_STYLES

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

    def __init__(self, alert: dict, is_dark: bool = False, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.alert_id = alert.get("id", 0)
        self._alert = alert
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        # 存储需在暗色模式更新时重设样式的控件引用
        self._desc_label = None
        self._time_label = None
        self._read_badge = None
        self._dismiss_btn = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
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
            self._desc_label = QLabel(desc)
            self._desc_label.setWordWrap(True)
            self._desc_label.setStyleSheet(QSS_STYLES["section_desc"].format(c=self._colors))
            layout.addWidget(self._desc_label)

        layout.addLayout(self._create_bottom_layout(alert))

    def _create_title_layout(self, alert: dict, type_cfg: dict, sev_cfg: dict, is_read: bool) -> None:
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
            self._read_badge = QLabel("已读")
            self._read_badge.setStyleSheet(
                f"font-size: 11px; color: {self._colors['text_muted']}; "
                f"border: 1px solid {self._colors['border']}; border-radius: 3px; padding: 1px 4px;"
            )
            title_layout.addWidget(self._read_badge)

        return title_layout

    def _create_bottom_layout(self, alert: dict) -> None:
        """创建底部信息行（检测时间+忽略按钮）"""
        bottom_layout = QHBoxLayout()

        detected_at = alert.get("detected_at", "")
        if detected_at:
            self._time_label = QLabel(f"🕐 {detected_at}")
            self._time_label.setStyleSheet(QSS_STYLES["small_text"].format(c=self._colors))
            bottom_layout.addWidget(self._time_label)

        bottom_layout.addStretch()

        self._dismiss_btn = QPushButton("忽略")
        self._dismiss_btn.setFixedSize(60, 26)
        self._dismiss_btn.setStyleSheet(self._get_dismiss_btn_style())
        self._dismiss_btn.clicked.connect(lambda: self.dismissed.emit(self.alert_id))
        bottom_layout.addWidget(self._dismiss_btn)

        return bottom_layout

    def _get_dismiss_btn_style(self) -> str:
        """生成忽略按钮的QSS样式"""
        c = self._colors
        return (
            f"QPushButton {{ background: transparent; border: 1px solid {c['border']}; "
            f"border-radius: 4px; color: {c['text_secondary']}; font-size: 11px; }} "
            f"QPushButton:hover {{ background: {c['bg_sidebar_hover']}; border-color: {c['text_muted']}; }}"
        )

    def set_dark_mode(self, is_dark: bool) -> None:
        """设置暗色模式"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        # 重新应用卡片级别样式
        severity = self._alert.get("severity", "warning")
        sev_cfg = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["warning"])
        if is_dark:
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
        else:
            self.setStyleSheet(f"""
                AlertCard {{
                    background: {sev_cfg['bg']};
                    border: 1px solid {sev_cfg['border']};
                    border-radius: 8px;
                    padding: 12px;
                    margin: 4px 0px;
                }}
            """)
        # 重新应用子控件样式（使用主题色，无需字符串替换）
        if self._desc_label:
            self._desc_label.setStyleSheet(QSS_STYLES["section_desc"].format(c=self._colors))
        if self._time_label:
            self._time_label.setStyleSheet(QSS_STYLES["small_text"].format(c=self._colors))
        if self._read_badge:
            self._read_badge.setStyleSheet(
                f"font-size: 11px; color: {self._colors['text_muted']}; "
                f"border: 1px solid {self._colors['border']}; border-radius: 3px; padding: 1px 4px;"
            )
        if self._dismiss_btn:
            self._dismiss_btn.setStyleSheet(self._get_dismiss_btn_style())


class AnomalyAlertDialog(QDialog):
    """异常告警中心对话框

    展示所有异常行为告警，支持：
    - 查看告警详情
    - 忽略单条告警
    - 全部标记已读
    - 暗色模式
    """

    alerts_changed = pyqtSignal()  # 告警状态变更信号

    def __init__(self, db: DatabaseManager, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.db = db
        self._is_dark = False
        self._colors = get_colors(False)
        self._cards = []
        self._setup_ui()
        self._load_alerts()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
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

    def _create_header(self) -> None:
        """创建标题行"""
        colors = self._colors
        header_layout = QHBoxLayout()
        title = QLabel("🚨 异常行为告警中心")
        title.setStyleSheet(QSS_STYLES["dialog_title"].format(c=colors))
        header_layout.addWidget(title)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(QSS_STYLES["secondary_text"].format(c=colors))
        header_layout.addStretch()
        header_layout.addWidget(self._count_label)
        return header_layout

    def _create_action_bar(self) -> None:
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

    def _create_alert_list(self) -> None:
        """创建告警列表滚动区域"""
        colors = self._colors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {colors['border']}; "
            f"border-radius: 8px; background: {colors['bg_primary']}; }}"
        )

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(4)
        self._list_layout.setContentsMargins(8, 8, 8, 8)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_widget)
        return scroll

    def _set_filter(self, filter_type: str) -> None:
        """设置筛选模式"""
        self._filter_all_btn.setChecked(filter_type == "all")
        self._filter_unread_btn.setChecked(filter_type == "unread")
        self._current_filter = filter_type
        self._load_alerts()

    def _load_alerts(self) -> None:
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
            colors = self._colors
            hint.setStyleSheet(f"font-size: 14px; color: {colors['text_muted']}; padding: 40px;")
            hint.setProperty("empty_hint", True)
            # 插入到stretch之前
            self._list_layout.insertWidget(0, hint)
            return

        for alert in alerts:
            card = AlertCard(alert, is_dark=self._is_dark)
            card.dismissed.connect(self._on_dismiss)
            # 插入到stretch之前
            idx = self._list_layout.count() - 1
            self._list_layout.insertWidget(idx, card)
            self._cards.append(card)

    def _on_dismiss(self, alert_id: int) -> None:
        """忽略告警"""
        self.db.dismiss_alert(alert_id)
        self._load_alerts()
        self.alerts_changed.emit()

    def _mark_all_read(self) -> None:
        """全部标记已读"""
        self.db.mark_all_alerts_read()
        self._load_alerts()
        self.alerts_changed.emit()

    def set_dark_mode(self, is_dark: bool) -> None:
        """设置暗色模式"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        colors = self._colors
        self.setStyleSheet(QSS_STYLES["dialog_base"].format(c=colors))
        for card in self._cards:
            card.set_dark_mode(is_dark)