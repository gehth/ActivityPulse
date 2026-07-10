"""久坐提醒对话框 - 系统通知 + 声音提示 + 休息建议 + 暂停"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal

from gui.themes import HoverButton
from utils.time_utils import format_minutes
import random


# 休息建议列表
REST_SUGGESTIONS = [
    ("🧘", "颈部伸展", "缓慢转动头部，左右各5次"),
    ("🤸", "肩部放松", "耸肩5秒后放松，重复5次"),
    ("👀", "眼部休息", "远眺20秒，闭眼休息10秒"),
    ("🚶", "起身走动", "走动3-5分钟，活动腿部"),
    ("💪", "手腕活动", "旋转手腕各10次，预防腕管综合征"),
    ("🧍", "站立伸展", "站立双手上举，全身伸展10秒"),
]


class SedentaryDialog(QDialog):
    """久坐提醒对话框

    显示连续使用时长、休息建议、暂停按钮。
    播放系统提示音。
    """

    snoozed = pyqtSignal()  # 暂停15分钟

    def __init__(self, continuous_minutes: int, parent=None) -> None:
        super().__init__(parent)
        self._is_dark = False
        self._continuous_minutes = continuous_minutes
        self._setup_ui()
        self._play_notification_sound()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        self.setWindowTitle("久坐提醒")
        self.setFixedSize(420, 380)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        layout.addLayout(self._create_header())
        layout.addWidget(self._create_separator())
        self._add_suggestions(layout)
        layout.addStretch()
        layout.addLayout(self._create_buttons())

    def _create_header(self) -> None:
        """创建标题和时长信息"""
        header = QVBoxLayout()
        header.setSpacing(4)

        title = QLabel("⚠️ 久坐提醒")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #F59E0B;")
        title.setAlignment(Qt.AlignCenter)
        header.addWidget(title)

        time_text = f"您已连续使用电脑 {format_minutes(self._continuous_minutes, fmt='long')}"
        info = QLabel(time_text)
        info.setStyleSheet("font-size: 15px; color: #374151;")
        info.setAlignment(Qt.AlignCenter)
        header.addWidget(info)

        warning = QLabel("长时间久坐可能影响健康，建议适当休息")
        warning.setStyleSheet("font-size: 13px; color: #6B7280;")
        warning.setAlignment(Qt.AlignCenter)
        header.addWidget(warning)

        return header

    def _create_separator(self) -> None:
        """创建分隔线"""
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E5E7EB;")
        return sep

    def _add_suggestions(self, layout) -> None:
        """添加随机休息建议"""
        suggest_label = QLabel("💡 休息建议")
        suggest_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #3B82F6;")
        layout.addWidget(suggest_label)

        suggestions = random.sample(REST_SUGGESTIONS, min(2, len(REST_SUGGESTIONS)))
        for icon, name, desc in suggestions:
            row = QHBoxLayout()
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 24px;")
            icon_label.setFixedWidth(36)
            row.addWidget(icon_label)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            name_label = QLabel(name)
            name_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #111827;")
            text_layout.addWidget(name_label)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("font-size: 12px; color: #6B7280;")
            text_layout.addWidget(desc_label)
            row.addLayout(text_layout)
            row.addStretch()
            layout.addLayout(row)

    def _create_buttons(self) -> None:
        """创建操作按钮"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_snooze = HoverButton("😴 暂停提醒15分钟")
        self.btn_snooze.setObjectName("btn_outline")
        self.btn_snooze.clicked.connect(self._on_snooze)
        btn_layout.addWidget(self.btn_snooze)

        self.btn_ok = HoverButton("👍 知道了，去休息")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        return btn_layout

    def _on_snooze(self) -> None:
        """暂停提醒15分钟"""
        self.snoozed.emit()
        self.accept()

    def _play_notification_sound(self) -> None:
        """播放系统提示音"""
        try:
            from PyQt5.QtWidgets import QApplication
            QApplication.beep()
        except Exception:
            pass

    def set_theme(self, is_dark: bool) -> None:
        """更新主题"""
        self._is_dark = is_dark
        self.btn_snooze.set_theme(is_dark)
        self.btn_ok.set_theme(is_dark)