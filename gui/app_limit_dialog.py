"""应用使用限制对话框 - 设置每日使用时间限制"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QSpinBox, QCheckBox, QComboBox,
    QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from database.db_manager import DatabaseManager
from gui.themes import get_colors, HoverButton


class AppLimitDialog(QDialog):
    """应用使用限制设置对话框"""
    
    limits_changed = pyqtSignal()  # 限制变更信号
    
    def __init__(self, db_manager: DatabaseManager, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.db = db_manager
        self._is_dark = False
        self.setWindowTitle("应用使用限制")
        self.setMinimumSize(520, 420)
        self._setup_ui()
        self._load_limits()
    
    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 说明
        desc = QLabel("为应用设置每日使用时间限制，达到限制后将收到提醒通知。")
        desc.setObjectName("section_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(self._create_list_group())
        layout.addWidget(self._create_add_group())

        # 关闭按钮
        row_close = QHBoxLayout()
        row_close.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.setObjectName("btn_outline")
        btn_close.clicked.connect(self.accept)
        row_close.addWidget(btn_close)
        layout.addLayout(row_close)

        # 加载应用列表
        self._load_app_names()

    def _create_list_group(self) -> "QGroupBox":
        """创建当前限制列表"""
        list_group = QGroupBox("已设置的限制")
        list_group.setObjectName("card")
        list_layout = QVBoxLayout(list_group)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["应用名称", "每日限制", "状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 80)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        list_layout.addWidget(self.table)

        return list_group

    def _create_add_group(self) -> "QGroupBox":
        """创建添加限制表单"""
        add_group = QGroupBox("添加限制")
        add_group.setObjectName("card")
        add_layout = QVBoxLayout(add_group)

        # 应用选择行
        row_app = QHBoxLayout()
        label_app = QLabel("应用名称")
        label_app.setObjectName("card_title")
        label_app.setFixedWidth(70)
        row_app.addWidget(label_app)

        self.combo_app = QComboBox()
        self.combo_app.setEditable(True)
        self.combo_app.setPlaceholderText("输入或选择应用名称")
        row_app.addWidget(self.combo_app)
        add_layout.addLayout(row_app)

        # 限制时间行
        row_limit = QHBoxLayout()
        label_limit = QLabel("每日限制")
        label_limit.setObjectName("card_title")
        label_limit.setFixedWidth(70)
        row_limit.addWidget(label_limit)

        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(5, 720)
        self.spin_limit.setSuffix(" 分钟")
        self.spin_limit.setValue(60)
        row_limit.addWidget(self.spin_limit)

        self.cb_enabled = QCheckBox("启用")
        self.cb_enabled.setChecked(True)
        row_limit.addWidget(self.cb_enabled)

        row_limit.addStretch()
        add_layout.addLayout(row_limit)

        # 添加按钮
        row_btn = QHBoxLayout()
        row_btn.addStretch()
        btn_add = HoverButton("➕ 添加限制")
        btn_add.clicked.connect(self._on_add_limit)
        row_btn.addWidget(btn_add)
        add_layout.addLayout(row_btn)

        return add_group
    
    def _load_app_names(self) -> None:
        """加载已知应用名称到下拉框"""
        self.combo_app.clear()
        # 从app_usage获取所有已知应用
        try:
            app_summary = self.db.get_app_usage_summary()
            for item in app_summary:
                self.combo_app.addItem(item.get("app_name", ""))
        except Exception:
            pass
    
    def _load_limits(self) -> None:
        """加载已有限制列表"""
        self.table.setRowCount(0)
        colors = get_colors("dark" if self._is_dark else "light")
        limits = self.db.get_all_limits()
        
        for i, lim in enumerate(limits):
            self.table.insertRow(i)
            
            # 应用名称
            name_item = QTableWidgetItem(lim["app_name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 0, name_item)
            
            # 限制时间
            limit_item = QTableWidgetItem(f"{lim['daily_limit_minutes']} 分钟")
            limit_item.setFlags(limit_item.flags() & ~Qt.ItemIsEditable)
            limit_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, limit_item)
            
            # 状态
            status_item = QTableWidgetItem("启用" if lim.get("enabled") else "禁用")
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            status_item.setTextAlignment(Qt.AlignCenter)
            if lim.get("enabled"):
                status_item.setForeground(QColor(colors["success"]))
            else:
                status_item.setForeground(QColor(colors["text_muted"]))
            self.table.setItem(i, 2, status_item)
            
            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            
            btn_toggle = QPushButton("切换" if lim.get("enabled") else "启用")
            btn_toggle.setFixedHeight(26)
            btn_toggle.setObjectName("btn_outline")
            btn_toggle.clicked.connect(lambda checked, app=lim["app_name"]: self._on_toggle(app))
            btn_layout.addWidget(btn_toggle)
            
            btn_remove = QPushButton("删除")
            btn_remove.setFixedHeight(26)
            btn_remove.setObjectName("btn_outline")
            btn_remove.clicked.connect(lambda checked, app=lim["app_name"]: self._on_remove(app))
            btn_layout.addWidget(btn_remove)
            
            self.table.setCellWidget(i, 3, btn_widget)
    
    def _on_add_limit(self) -> None:
        """添加限制"""
        app_name = self.combo_app.currentText().strip()
        if not app_name:
            QMessageBox.warning(self, "提示", "请输入应用名称")
            return
        
        limit_minutes = self.spin_limit.value()
        enabled = self.cb_enabled.isChecked()
        
        # 检查是否已存在
        existing = self.db.get_app_limit(app_name)
        if existing:
            reply = QMessageBox.question(
                self, "确认覆盖",
                f"应用 \"{app_name}\" 已有限制（{existing['daily_limit_minutes']}分钟），是否覆盖？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        self.db.set_app_limit(app_name, limit_minutes, enabled)
        self._load_limits()
        self.limits_changed.emit()
        self.statusBar().showMessage(f"已设置 {app_name} 每日限制 {limit_minutes} 分钟") if hasattr(self, 'statusBar') else None
    
    def _on_toggle(self, app_name: str) -> None:
        """切换启用/禁用"""
        limit_info = self.db.get_app_limit(app_name)
        if limit_info:
            new_enabled = not limit_info.get("enabled", True)
            self.db.set_app_limit(app_name, limit_info["daily_limit_minutes"], new_enabled)
            self._load_limits()
            self.limits_changed.emit()
    
    def _on_remove(self, app_name: str) -> None:
        """删除限制"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定删除 \"{app_name}\" 的使用限制？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.remove_app_limit(app_name)
            self._load_limits()
            self.limits_changed.emit()
    
    def set_theme(self, is_dark: bool) -> None:
        """设置主题"""
        self._is_dark = is_dark
        colors = get_colors(is_dark)
        # 更新表格样式
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {colors['bg_card']};
                alternate-background-color: {colors['bg_sidebar_hover']};
                gridline-color: {colors['border']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
            }}
            QTableWidget::item {{
                padding: 6px;
            }}
            QHeaderView::section {{
                background-color: {colors['bg_sidebar']};
                color: {colors['text_secondary']};
                padding: 6px;
                border: none;
                border-bottom: 1px solid {colors['border']};
                font-weight: bold;
            }}
        """)
        # 刷新表格以更新状态颜色
        self._load_limits()