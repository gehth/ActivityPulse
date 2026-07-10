"""工具栏构建器 - 创建顶部工具栏（时间选择器 + 操作按钮）"""

from types import SimpleNamespace

from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QComboBox,
    QDateEdit, QPushButton
)
from PyQt5.QtCore import QDate

from gui.themes import HoverButton


def create_toolbar(callbacks: dict) -> tuple:
    """创建顶部工具栏

    Args:
        callbacks: 回调函数字典，支持以下键：
            - on_time_range_changed: 时间范围变更回调
            - on_refresh: 刷新回调
            - on_search: 搜索回调
            - on_pomodoro: 番茄钟回调
            - on_tags: 标签管理回调
            - on_alert: 告警回调
            - on_playback: 屏幕回放回调
            - on_export_csv: 导出CSV回调
            - on_export_pdf: 导出PDF回调
            - on_toggle_theme: 主题切换回调

    Returns:
        (toolbar_frame, widgets) 元组
        widgets 是 SimpleNamespace，包含需要外部访问的控件：
            time_combo, date_edit, date_start_label, date_start_edit,
            date_end_label, date_end_edit, btn_alert, btn_theme
    """
    toolbar = QFrame()
    toolbar.setObjectName("toolbar")
    layout = QHBoxLayout(toolbar)
    layout.setContentsMargins(20, 8, 20, 8)

    # 时间选择器
    time_widgets = _create_time_selector(callbacks)
    for w in time_widgets["layout_widgets"]:
        layout.addWidget(w)

    # 操作按钮
    action_widgets = _create_action_buttons(callbacks)
    for w in action_widgets:
        layout.addWidget(w)

    layout.addStretch()

    # 导出按钮
    layout.addWidget(_make_btn("📥 导出CSV", "btn_outline", callbacks.get("on_export_csv")))
    btn_export_pdf = HoverButton("📄 导出PDF")
    btn_export_pdf.setObjectName("btn_outline")
    btn_export_pdf.clicked.connect(callbacks.get("on_export_pdf"))
    layout.addWidget(btn_export_pdf)

    # 主题切换
    btn_theme = HoverButton("🌙 深色")
    btn_theme.setObjectName("btn_outline")
    btn_theme.clicked.connect(callbacks.get("on_toggle_theme"))
    layout.addWidget(btn_theme)

    # 返回工具栏和需要外部访问的控件
    widgets = SimpleNamespace(
        time_combo=time_widgets["time_combo"],
        date_edit=time_widgets["date_edit"],
        date_start_label=time_widgets["date_start_label"],
        date_start_edit=time_widgets["date_start_edit"],
        date_end_label=time_widgets["date_end_label"],
        date_end_edit=time_widgets["date_end_edit"],
        btn_alert=action_widgets[4],  # 告警按钮是第5个
        btn_theme=btn_theme,
    )

    return toolbar, widgets


def _create_time_selector(callbacks: dict) -> dict:
    """创建时间选择器区域"""
    layout_widgets = []

    layout_widgets.append(QLabel("📅"))

    time_combo = QComboBox()
    time_combo.addItems(["今日", "昨日", "近7天", "近30天", "自定义"])
    time_combo.setFixedWidth(100)
    time_combo.currentTextChanged.connect(callbacks.get("on_time_range_changed"))
    layout_widgets.append(time_combo)

    date_edit = QDateEdit()
    date_edit.setDate(QDate.currentDate())
    date_edit.setCalendarPopup(True)
    date_edit.setDisplayFormat("yyyy-MM-dd")
    date_edit.setFixedWidth(120)
    layout_widgets.append(date_edit)

    # 自定义日期范围 - 开始日期
    date_start_label = QLabel("从")
    date_start_label.setObjectName("metric_title")
    layout_widgets.append(date_start_label)
    date_start_edit = QDateEdit()
    date_start_edit.setDate(QDate.currentDate().addDays(-7))
    date_start_edit.setCalendarPopup(True)
    date_start_edit.setDisplayFormat("yyyy-MM-dd")
    date_start_edit.setFixedWidth(120)
    date_start_edit.hide()
    layout_widgets.append(date_start_edit)

    # 自定义日期范围 - 结束日期
    date_end_label = QLabel("至")
    date_end_label.setObjectName("metric_title")
    layout_widgets.append(date_end_label)
    date_end_edit = QDateEdit()
    date_end_edit.setDate(QDate.currentDate())
    date_end_edit.setCalendarPopup(True)
    date_end_edit.setDisplayFormat("yyyy-MM-dd")
    date_end_edit.setFixedWidth(120)
    date_end_edit.hide()
    layout_widgets.append(date_end_edit)

    return {
        "layout_widgets": layout_widgets,
        "time_combo": time_combo,
        "date_edit": date_edit,
        "date_start_label": date_start_label,
        "date_start_edit": date_start_edit,
        "date_end_label": date_end_label,
        "date_end_edit": date_end_edit,
    }


def _create_action_buttons(callbacks: dict) -> list:
    """创建操作按钮列表"""
    buttons = []
    buttons.append(_make_btn("🔄 刷新", "btn_outline", callbacks.get("on_refresh")))
    buttons.append(_make_btn("🔍 搜索", "btn_outline", callbacks.get("on_search")))
    buttons.append(_make_btn("🍅 专注", "btn_outline", callbacks.get("on_pomodoro")))
    buttons.append(_make_btn("🏷️ 标签", "btn_outline", callbacks.get("on_tags")))
    buttons.append(_make_btn("🚨 告警", "btn_outline", callbacks.get("on_alert")))
    buttons.append(_make_btn("🎬 回放", "btn_outline", callbacks.get("on_playback")))
    return buttons


def _make_btn(text: str, object_name: str, callback) -> QPushButton:
    """创建一个带样式的按钮"""
    btn = QPushButton(text)
    btn.setObjectName(object_name)
    if callback:
        btn.clicked.connect(callback)
    return btn