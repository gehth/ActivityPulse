"""首次使用引导页 - 欢迎界面 + 快速设置"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from gui.themes import HoverButton


class WelcomePage(QWidget):
    """首次使用引导页

    显示欢迎信息、功能介绍、快速设置选项。
    点击"开始使用"后关闭，不再显示。
    """

    start_clicked = pyqtSignal(dict)  # 快速设置参数 {"auto_monitor": bool, "screenshot": bool, ...}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dark = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(24)

        # 顶部装饰
        layout.addStretch(1)

        # 欢迎标题
        layout.addLayout(self._create_header())
        layout.addSpacing(16)

        # 功能介绍卡片
        layout.addLayout(self._create_features_section())
        layout.addSpacing(16)

        # 快速设置
        layout.addWidget(self._create_settings_card())
        layout.addSpacing(16)

        # 开始按钮
        layout.addLayout(self._create_start_button())

        layout.addStretch(1)

    def _create_header(self):
        """创建欢迎标题区域"""
        vbox = QVBoxLayout()

        title = QLabel("👋 欢迎使用行为记录")
        title.setObjectName("page_title")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        vbox.addWidget(title)

        subtitle = QLabel("自动追踪您的电脑使用习惯，帮助您更好地管理时间")
        subtitle.setObjectName("section_desc")
        subtitle.setStyleSheet("font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        vbox.addWidget(subtitle)

        return vbox

    def _create_features_section(self):
        """创建功能介绍卡片区域"""
        features_layout = QHBoxLayout()
        features_layout.setSpacing(16)

        features = [
            ("📊", "智能仪表盘", "一目了然查看今日\n专注时长和活跃应用"),
            ("🕐", "时间轴视图", "按时间段查看应用\n使用分布和切换记录"),
            ("📈", "统计洞察", "环形图、折线图、\n柱状图多维度分析"),
            ("📸", "截图浏览", "自动截屏记录\n支持日期范围筛选"),
        ]

        for icon, title_text, desc_text in features:
            card = QFrame()
            card.setObjectName("metric_card")
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            card_layout.setContentsMargins(16, 16, 16, 16)

            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 32px;")
            icon_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(icon_label)

            card_title = QLabel(title_text)
            card_title.setObjectName("card_title")
            card_title.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(card_title)

            card_desc = QLabel(desc_text)
            card_desc.setObjectName("section_desc")
            card_desc.setStyleSheet("font-size: 12px;")
            card_desc.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(card_desc)

            features_layout.addWidget(card)

        return features_layout

    def _create_settings_card(self):
        """创建快速设置卡片"""
        settings_card = QFrame()
        settings_card.setObjectName("card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setSpacing(12)
        settings_layout.setContentsMargins(24, 16, 24, 16)

        settings_title = QLabel("⚡ 快速设置")
        settings_title.setObjectName("card_title")
        settings_title.setStyleSheet("font-size: 16px;")
        settings_layout.addWidget(settings_title)

        # 自动开始记录
        self.cb_auto_monitor = QCheckBox("启动时自动开始记录")
        self.cb_auto_monitor.setChecked(True)
        settings_layout.addWidget(self.cb_auto_monitor)

        # 截图功能
        self.cb_screenshot = QCheckBox("启用自动截图（每60秒）")
        self.cb_screenshot.setChecked(True)
        settings_layout.addWidget(self.cb_screenshot)

        # 开机自启
        self.cb_autostart = QCheckBox("开机自动启动")
        self.cb_autostart.setChecked(False)
        settings_layout.addWidget(self.cb_autostart)

        # 久坐提醒
        sedentary_row = QHBoxLayout()
        sedentary_label = QLabel("久坐提醒间隔")
        sedentary_label.setObjectName("card_title")
        sedentary_row.addWidget(sedentary_label)
        self.spin_sedentary = QSpinBox()
        self.spin_sedentary.setRange(0, 240)
        self.spin_sedentary.setSuffix(" 分钟")
        self.spin_sedentary.setSpecialValueText("禁用")
        self.spin_sedentary.setValue(60)
        self.spin_sedentary.setFixedWidth(100)
        sedentary_row.addWidget(self.spin_sedentary)
        sedentary_row.addStretch()
        settings_layout.addLayout(sedentary_row)

        return settings_card

    def _create_start_button(self):
        """创建开始按钮区域"""
        vbox = QVBoxLayout()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_start = HoverButton("🚀 开始使用")
        self.btn_start.setStyleSheet("""
            QPushButton {
                padding: 12px 48px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
        """)
        self.btn_start.clicked.connect(self._on_start)
        btn_layout.addWidget(self.btn_start)

        btn_layout.addStretch()
        vbox.addLayout(btn_layout)

        # 提示
        hint = QLabel("您可以随时在设置中修改这些选项")
        hint.setObjectName("section_desc")
        hint.setStyleSheet("font-size: 12px;")
        hint.setAlignment(Qt.AlignCenter)
        vbox.addWidget(hint)

        return vbox

    def _on_start(self):
        """点击开始使用"""
        settings = {
            "auto_monitor": self.cb_auto_monitor.isChecked(),
            "screenshot_enabled": self.cb_screenshot.isChecked(),
            "autostart": self.cb_autostart.isChecked(),
            "sedentary_reminder_minutes": self.spin_sedentary.value(),
        }
        self.start_clicked.emit(settings)

    def set_theme(self, is_dark: bool):
        """更新主题"""
        self._is_dark = is_dark
        self.btn_start.set_theme(is_dark)