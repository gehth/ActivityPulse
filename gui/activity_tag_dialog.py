"""活动标签对话框 - 添加/管理活动标签和备注"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QTimeEdit,
    QColorDialog, QFrame, QScrollArea, QWidget,
    QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTime, pyqtSignal
from PyQt5.QtGui import QColor

from database.db_manager import DatabaseManager
from gui.themes import get_colors

# 预定义标签颜色
TAG_COLORS = [
    "#3B82F6",  # 蓝色
    "#10B981",  # 绿色
    "#F59E0B",  # 黄色
    "#EF4444",  # 红色
    "#8B5CF6",  # 紫色
    "#EC4899",  # 粉色
    "#06B6D4",  # 青色
    "#F97316",  # 橙色
]

# 预定义标签
PRESET_TAGS = ["工作", "学习", "休息", "娱乐", "会议", "开发", "阅读", "运动"]


class TagItemWidget(QFrame):
    """单个标签条目"""

    deleted = pyqtSignal(int)  # tag_id
    edited = pyqtSignal(int)  # tag_id

    def __init__(self, tag_data: dict, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._tag_id = tag_data.get("id", 0)
        self._color = tag_data.get("color", "#3B82F6")
        self.setObjectName("card")
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # 颜色指示条
        color_bar = QFrame()
        color_bar.setFixedWidth(4)
        color_bar.setStyleSheet(f"background-color: {self._color}; border-radius: 2px;")
        layout.addWidget(color_bar)

        # 标签信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        tag_label = QLabel(tag_data.get("tag", ""))
        tag_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout_tag = tag_label  # keep reference
        info_layout.addWidget(tag_label)

        time_str = ""
        if tag_data.get("start_time") and tag_data.get("end_time"):
            time_str = f"{tag_data['start_time']} - {tag_data['end_time']}"
        note = tag_data.get("note", "")
        detail_parts = [p for p in [time_str, note] if p]
        detail_text = " | ".join(detail_parts) if detail_parts else "无备注"
        detail_label = QLabel(detail_text)
        detail_label.setStyleSheet("font-size: 11px;")
        info_layout.addWidget(detail_label)

        layout.addLayout(info_layout, 1)

        # 编辑按钮
        btn_edit = QPushButton("✏️")
        btn_edit.setFixedSize(28, 28)
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.setToolTip("编辑")
        btn_edit.clicked.connect(lambda: self.edited.emit(self._tag_id))
        layout.addWidget(btn_edit)

        # 删除按钮
        btn_del = QPushButton("🗑️")
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setToolTip("删除")
        btn_del.clicked.connect(self._confirm_delete)
        layout.addWidget(btn_del)

        self._apply_styles()

    def _confirm_delete(self):
        reply = QMessageBox.question(self, "删除标签", "确定删除此标签？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.deleted.emit(self._tag_id)

    def _apply_styles(self):
        colors = get_colors("dark" if self._is_dark else "light")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {colors['bg_card']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
            }}
        """)

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark
        self._apply_styles()


class AddTagDialog(QDialog):
    """添加标签对话框"""

    tag_added = pyqtSignal(dict)  # {tag, note, start_time, end_time, color}

    def __init__(self, date: str, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._date = date
        self._selected_color = TAG_COLORS[0]
        self.setWindowTitle("添加活动标签")
        self.setFixedSize(360, 400)
        self._setup_ui()

    def _setup_ui(self):
        colors = get_colors("dark" if self._is_dark else "light")
        self.setStyleSheet(f"background-color: {colors['bg_card']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 日期显示
        date_label = QLabel(f"📅 {self._date}")
        date_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 12px;")
        layout.addWidget(date_label)

        # 标签名
        layout.addWidget(QLabel("标签名称："))
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入标签名称...")
        self.tag_input.setStyleSheet(f"""
            QLineEdit {{
                background: {colors['bg_sidebar_hover']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 6px;
                font-size: 13px;
            }}
        """)
        layout.addWidget(self.tag_input)
        layout.addLayout(self._create_preset_tags(colors))

        # 时间范围
        layout.addWidget(QLabel("时间范围："))
        layout.addLayout(self._create_time_range(colors))

        # 备注
        layout.addWidget(QLabel("备注："))
        self.note_input = QTextEdit()
        self.note_input.setFixedHeight(60)
        self.note_input.setPlaceholderText("添加备注...")
        self.note_input.setStyleSheet(f"""
            QTextEdit {{
                background: {colors['bg_sidebar_hover']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.note_input)

        # 颜色选择
        layout.addWidget(QLabel("标签颜色："))
        layout.addLayout(self._create_color_picker(colors))

        # 确认按钮
        btn_add = QPushButton("✅ 添加标签")
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {colors['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {colors['primary_hover']};
            }}
        """)
        btn_add.clicked.connect(self._on_add)
        layout.addWidget(btn_add)

    def _create_preset_tags(self, colors):
        """创建快捷标签行"""
        preset_row = QHBoxLayout()
        preset_row.setSpacing(4)
        for tag in PRESET_TAGS:
            btn = QPushButton(tag)
            btn.setFixedSize(48, 26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {colors['border']};
                    border-radius: 4px;
                    background: transparent;
                    color: {colors['text_secondary']};
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {colors['primary_light']};
                    color: {colors['primary']};
                    border-color: {colors['primary']};
                }}
            """)
            btn.clicked.connect(lambda checked, t=tag: self.tag_input.setText(t))
            preset_row.addWidget(btn)
        return preset_row

    def _create_time_range(self, colors):
        """创建时间范围选择行"""
        time_row = QHBoxLayout()
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setTime(QTime.currentTime().addSecs(-3600))
        self.start_time.setStyleSheet(f"""
            QTimeEdit {{
                background: {colors['bg_sidebar_hover']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        time_row.addWidget(self.start_time)

        time_to = QLabel("→")
        time_to.setStyleSheet(f"color: {colors['text_muted']};")
        time_row.addWidget(time_to)

        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setTime(QTime.currentTime())
        self.end_time.setStyleSheet(f"""
            QTimeEdit {{
                background: {colors['bg_sidebar_hover']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        time_row.addWidget(self.end_time)
        return time_row

    def _create_color_picker(self, colors):
        """创建颜色选择行"""
        color_row = QHBoxLayout()
        color_row.setSpacing(6)
        self._color_btns = []
        for i, c in enumerate(TAG_COLORS):
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c};
                    border: 2px solid {'white' if i == 0 else 'transparent'};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border: 2px solid {colors['primary']};
                }}
            """)
            btn.clicked.connect(lambda checked, color=c, idx=i: self._select_color(color, idx))
            color_row.addWidget(btn)
            self._color_btns.append(btn)
        return color_row

    def _select_color(self, color, idx):
        self._selected_color = color
        colors = get_colors("dark" if self._is_dark else "light")
        for i, btn in enumerate(self._color_btns):
            border = "white" if i == idx else "transparent"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {TAG_COLORS[i]};
                    border: 2px solid {border};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border: 2px solid {colors['primary']};
                }}
            """)

    def _on_add(self):
        tag = self.tag_input.text().strip()
        if not tag:
            return
        self.tag_added.emit({
            "tag": tag,
            "note": self.note_input.toPlainText().strip(),
            "start_time": self.start_time.time().toString("HH:mm"),
            "end_time": self.end_time.time().toString("HH:mm"),
            "color": self._selected_color
        })
        self.accept()


class ActivityTagDialog(QDialog):
    """活动标签管理对话框"""

    tags_changed = pyqtSignal()  # 标签变更信号

    def __init__(self, db_manager: DatabaseManager, date: str, is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._date = date
        self._is_dark = is_dark
        self._tag_widgets = []
        self.setWindowTitle(f"活动标签 - {date}")
        self.setFixedSize(420, 520)
        self._setup_ui()
        self._load_tags()

    def _setup_ui(self):
        colors = get_colors("dark" if self._is_dark else "light")
        self.setStyleSheet(f"background-color: {colors['bg_primary']};")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel(f"🏷️ 活动标签")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {colors['text_primary']};")
        title_row.addWidget(title)
        title_row.addStretch()

        btn_add = QPushButton("➕ 添加")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {colors['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {colors['primary_hover']};
            }}
        """)
        btn_add.clicked.connect(self._open_add_dialog)
        title_row.addWidget(btn_add)
        layout.addLayout(title_row)

        # 标签列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet(f"background: transparent;")

        self._tags_container = QWidget()
        self._tags_layout = QVBoxLayout(self._tags_container)
        self._tags_layout.setSpacing(6)
        self._tags_layout.addStretch()

        scroll.setWidget(self._tags_container)
        layout.addWidget(scroll, 1)

        # 空状态
        self._empty_label = QLabel("暂无标签，点击右上角添加")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"color: {colors['text_muted']}; font-size: 13px; padding: 40px;")
        layout.addWidget(self._empty_label)

        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {colors['bg_sidebar_hover']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {colors['border']};
            }}
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _load_tags(self):
        """加载标签列表"""
        # 清空旧标签
        for w in self._tag_widgets:
            w.deleteLater()
        self._tag_widgets.clear()

        tags = self.db.get_activity_tags(self._date)

        if not tags:
            self._empty_label.show()
            return

        self._empty_label.hide()

        for tag_data in tags:
            item = TagItemWidget(tag_data, self._is_dark)
            item.deleted.connect(self._on_delete_tag)
            item.edited.connect(self._on_edit_tag)
            self._tags_layout.insertWidget(self._tags_layout.count() - 1, item)
            self._tag_widgets.append(item)

    def _open_add_dialog(self):
        """打开添加标签对话框"""
        dialog = AddTagDialog(self._date, self._is_dark, self)
        dialog.tag_added.connect(self._on_tag_added)
        dialog.exec_()

    def _on_tag_added(self, data: dict):
        """添加标签回调"""
        self.db.add_activity_tag(
            date=self._date,
            tag=data["tag"],
            note=data.get("note", ""),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            color=data.get("color", "#3B82F6")
        )
        self._load_tags()
        self.tags_changed.emit()

    def _on_delete_tag(self, tag_id: int):
        """删除标签回调"""
        self.db.delete_activity_tag(tag_id)
        self._load_tags()
        self.tags_changed.emit()

    def _on_edit_tag(self, tag_id: int):
        """编辑标签回调"""
        tags = self.db.get_activity_tags(self._date)
        tag_data = None
        for t in tags:
            if t.get("id") == tag_id:
                tag_data = t
                break
        if not tag_data:
            return

        # 使用简单的输入对话框编辑标签名和备注
        new_tag, ok = QInputDialog.getText(self, "编辑标签", "标签名称：",
                                           text=tag_data.get("tag", ""))
        if ok and new_tag.strip():
            self.db.update_activity_tag(tag_id, tag=new_tag.strip())
            self._load_tags()
            self.tags_changed.emit()

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark