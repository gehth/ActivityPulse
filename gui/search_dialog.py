"""数据搜索对话框 - 搜索应用使用记录"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QDateEdit, QFrame, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QColor

from database.db_manager import DatabaseManager
from utils.time_utils import format_duration
from gui.themes import get_colors


class SearchDialog(QDialog):
    """数据搜索对话框"""

    # 双击记录时发送信号: (date_str, app_name)
    navigate_to_record = pyqtSignal(str, str)

    def __init__(self, db: DatabaseManager, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("搜索记录")
        self.setMinimumSize(750, 500)
        self.resize(850, 600)
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        layout.addLayout(self._create_search_bar())
        layout.addLayout(self._create_filter_bar())

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("separator")
        layout.addWidget(line)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(
            ["应用名称", "窗口标题", "开始时间", "结束时间", "时长"]
        )
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setShowGrid(False)
        self.result_table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.result_table, 1)

        # 底部提示
        hint = QLabel("双击记录可跳转到对应日期的时间轴查看详情")
        hint.setObjectName("hint_label")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

    def _create_search_bar(self) -> None:
        """创建搜索栏"""
        search_bar = QHBoxLayout()
        search_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入应用名称或窗口标题关键词...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.returnPressed.connect(self._do_search)
        search_bar.addWidget(self.search_input, 1)

        self.btn_search = QPushButton("🔍 搜索")
        self.btn_search.setObjectName("btn_primary")
        self.btn_search.setFixedWidth(100)
        self.btn_search.clicked.connect(self._do_search)
        search_bar.addWidget(self.btn_search)

        return search_bar

    def _create_filter_bar(self) -> None:
        """创建筛选栏"""
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        filter_bar.addWidget(QLabel("日期范围:"))

        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate().addDays(-30))
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setFixedWidth(120)
        filter_bar.addWidget(self.date_start)

        filter_bar.addWidget(QLabel("至"))

        self.date_end = QDateEdit()
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setFixedWidth(120)
        filter_bar.addWidget(self.date_end)

        # 快捷日期按钮
        btn_week = QPushButton("近7天")
        btn_week.setObjectName("btn_filter")
        btn_week.setFixedWidth(60)
        btn_week.clicked.connect(lambda: self._set_date_range(7))
        filter_bar.addWidget(btn_week)

        btn_month = QPushButton("近30天")
        btn_month.setObjectName("btn_filter")
        btn_month.setFixedWidth(60)
        btn_month.clicked.connect(lambda: self._set_date_range(30))
        filter_bar.addWidget(btn_month)

        btn_all = QPushButton("全部")
        btn_all.setObjectName("btn_filter")
        btn_all.setFixedWidth(50)
        btn_all.clicked.connect(self._set_all_dates)
        filter_bar.addWidget(btn_all)

        filter_bar.addStretch()

        self.result_count_label = QLabel("")
        self.result_count_label.setObjectName("result_count")
        filter_bar.addWidget(self.result_count_label)

        return filter_bar

    def _apply_styles(self) -> None:
        """应用QSS样式表"""
        self._is_dark = False
        self.setStyleSheet(self._build_qss(get_colors(False)))

    def _build_qss(self, c: dict) -> str:
        """构建主题QSS样式表"""
        return f"""
            SearchDialog {{
                background-color: {c['bg_card']};
            }}
            QLineEdit {{
                padding: 10px 14px;
                border: 2px solid {c['border']};
                border-radius: 8px;
                font-size: 14px;
                background: {c['bg_primary']};
                color: {c['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {c['primary']};
                background: {c['bg_card']};
            }}
            #btn_primary {{
                background-color: {c['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: bold;
            }}
            #btn_primary:hover {{
                background-color: {c['primary_hover']};
            }}
            #btn_primary:pressed {{
                background-color: {c['primary']};
            }}
            #btn_filter {{
                background-color: {c['bg_sidebar_hover']};
                color: {c['text_secondary']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            #btn_filter:hover {{
                background-color: {c['border']};
                color: {c['text_primary']};
            }}
            #separator {{
                color: {c['border']};
            }}
            QTableWidget {{
                border: 1px solid {c['border']};
                border-radius: 8px;
                background-color: {c['bg_card']};
                gridline-color: {c['bg_sidebar_hover']};
                font-size: 13px;
                color: {c['text_primary']};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {c['bg_sidebar_hover']};
            }}
            QTableWidget::item:selected {{
                background-color: {c['primary_light']};
                color: {c['primary']};
            }}
            QHeaderView::section {{
                background-color: {c['bg_primary']};
                color: {c['text_secondary']};
                padding: 8px 10px;
                border: none;
                border-bottom: 2px solid {c['border']};
                font-weight: bold;
                font-size: 12px;
            }}
            QDateEdit {{
                padding: 4px 8px;
                border: 1px solid {c['border']};
                border-radius: 6px;
                background: {c['bg_primary']};
                color: {c['text_primary']};
                font-size: 13px;
            }}
            QDateEdit:focus {{
                border-color: {c['primary']};
            }}
            QLabel {{
                color: {c['text_secondary']};
                font-size: 13px;
            }}
            #result_count {{
                color: {c['primary']};
                font-weight: bold;
                font-size: 13px;
            }}
            #hint_label {{
                color: {c['text_muted']};
                font-size: 12px;
                padding: 4px;
            }}
        """

    def set_theme(self, is_dark: bool) -> None:
        """设置主题"""
        self._is_dark = is_dark
        self.setStyleSheet(self._build_qss(get_colors(is_dark)))

    def _set_date_range(self, days: int) -> None:
        """设置快捷日期范围"""
        self.date_end.setDate(QDate.currentDate())
        self.date_start.setDate(QDate.currentDate().addDays(-days + 1))

    def _set_all_dates(self) -> None:
        """设置全部日期范围（近1年）"""
        self.date_start.setDate(QDate.currentDate().addYears(-1))
        self.date_end.setDate(QDate.currentDate())

    def _do_search(self) -> None:
        """执行搜索"""
        keyword = self.search_input.text().strip()
        if not keyword:
            self.result_table.setRowCount(0)
            self.result_count_label.setText("")
            return

        date_start = self.date_start.date().toString("yyyy-MM-dd")
        date_end = self.date_end.date().toString("yyyy-MM-dd")

        results = self.db.search_app_usage(
            keyword=keyword,
            date_start=date_start,
            date_end=date_end,
            limit=200,
        )

        self._display_results(results, keyword)

    def _display_results(self, results: list, keyword: str) -> None:
        """显示搜索结果"""
        self.result_table.setRowCount(len(results))

        total_seconds = 0
        for row, record in enumerate(results):
            # 应用名称
            app_item = QTableWidgetItem(record["app_name"])
            app_item.setData(Qt.UserRole, record)
            self.result_table.setItem(row, 0, app_item)

            # 窗口标题
            title_item = QTableWidgetItem(record["window_title"] or "")
            self.result_table.setItem(row, 1, title_item)

            # 开始时间
            start_str = record["start_time"] or ""
            if len(start_str) > 16:
                start_str = start_str[:16]
            start_item = QTableWidgetItem(start_str)
            start_item.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(row, 2, start_item)

            # 结束时间
            end_str = record["end_time"] or ""
            if len(end_str) > 16:
                end_str = end_str[:16]
            end_item = QTableWidgetItem(end_str)
            end_item.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(row, 3, end_item)

            # 时长
            duration = record["duration_seconds"] or 0
            total_seconds += duration
            dur_str = self._format_duration(duration)
            dur_item = QTableWidgetItem(dur_str)
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(row, 4, dur_item)

            # 高亮关键词匹配
            self._highlight_keyword(app_item, keyword)
            self._highlight_keyword(title_item, keyword)

        # 更新结果统计
        count_text = f"共 {len(results)} 条结果"
        if total_seconds > 0:
            count_text += f"  |  累计 {self._format_duration(total_seconds)}"
        self.result_count_label.setText(count_text)

        if results:
            self.result_table.selectRow(0)

    def _highlight_keyword(self, item: QTableWidgetItem, keyword: str) -> str:
        """高亮关键词匹配部分"""
        text = item.text()
        if keyword.lower() in text.lower():
            # 使用蓝色文字标识匹配项
            item.setForeground(QColor("#1e40af"))

    def _format_duration(self, seconds: int) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}分钟"
        else:
            return format_duration(seconds, fmt="long")

    def _on_double_click(self, index: int) -> None:
        """双击记录跳转"""
        row = index.row()
        item = self.result_table.item(row, 0)
        if item:
            record = item.data(Qt.UserRole)
            if record and record.get("start_time"):
                date_str = record["start_time"][:10]
                app_name = record["app_name"]
                self.navigate_to_record.emit(date_str, app_name)
                self.accept()

    def show_and_focus(self) -> None:
        """显示对话框并聚焦搜索框"""
        self.show()
        self.search_input.setFocus()
        self.search_input.selectAll()