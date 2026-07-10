"""分类管理页面 - 应用分类 + 敏感标记"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QLineEdit, QMessageBox
)
from PyQt5.QtCore import Qt

import json

from database.db_manager import DatabaseManager
from gui.themes import EmptyStateWidget, apply_card_shadow, AnimatedCard, HoverButton

# 应用分类映射（从timeline_page移到公共位置避免循环导入）
APP_CATEGORIES = {
    # 生产力工具
    "code": "productivity", "devenv": "productivity", "pycharm": "productivity",
    "idea": "productivity", "vscode": "productivity", "word": "productivity",
    "excel": "productivity", "powerpoint": "productivity", "notepad": "productivity",
    "notepad++": "productivity", "sublime": "productivity", "vim": "productivity",
    "terminal": "productivity", "cmd": "productivity", "powershell": "productivity",
    # 浏览器
    "chrome": "browser", "firefox": "browser", "edge": "browser",
    "safari": "browser", "opera": "browser", "brave": "browser",
    # 社交/娱乐
    "wechat": "social", "qq": "social", "dingtalk": "social",
    "steam": "social", "spotify": "social", "music": "social",
    "bilibili": "social", "discord": "social", "telegram": "social",
}


def get_app_category(app_name: str) -> str:
    """根据应用名推断分类"""
    name_lower = app_name.lower().replace(".exe", "").replace(" ", "")
    for key, category in APP_CATEGORIES.items():
        if key in name_lower:
            return category
    return "other"

# 预设分类
PRESET_CATEGORIES = [
    ("生产力工具", "#3B82F6", "productivity"),
    ("浏览器", "#10B981", "browser"),
    ("社交", "#F59E0B", "social"),
    ("娱乐", "#EF4444", "entertainment"),
    ("系统工具", "#8B5CF6", "system"),
    ("其他", "#6B7280", "other"),
]


class CategoryTag(QFrame):
    """分类标签"""

    def __init__(self, name: str, color: str):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color}20;
                border: 1px solid {color};
                border-radius: 12px;
                padding: 4px 12px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 10px;")
        layout.addWidget(dot)

        label = QLabel(name)
        label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; border: none;")
        layout.addWidget(label)


class CategoriesPage(QWidget):
    """分类管理页面"""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._is_dark = False
        self._app_categories = {}  # app_name -> category
        self._sensitive_apps = set()  # 敏感应用集合
        self._custom_categories = []  # 自定义分类列表 [(name, color, key)]
        self._category_color_map = {}  # category_key -> color
        # 从数据库加载自定义分类
        self._load_custom_categories()
        self._setup_ui()

    def _load_custom_categories(self):
        """从数据库加载自定义分类"""
        saved = self.db.get_config("custom_categories")
        if saved:
            try:
                self._custom_categories = json.loads(saved)
            except (json.JSONDecodeError, TypeError):
                self._custom_categories = []

    def _save_custom_categories(self):
        """保存自定义分类到数据库"""
        self.db.save_config("custom_categories", json.dumps(self._custom_categories, ensure_ascii=False))

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 20)

        # 标题
        title = QLabel("分类管理")
        title.setObjectName("page_title")
        main_layout.addWidget(title)

        main_layout.addWidget(self._create_category_card())
        main_layout.addWidget(self._create_table_card())

        # 空数据状态
        self.empty_state = EmptyStateWidget(
            icon="🏷️", title="还没有应用数据",
            description="开始记录后，可以在这里管理应用分类"
        )
        self.empty_state.setFixedHeight(200)
        self.empty_state.hide()
        main_layout.addWidget(self.empty_state)

        main_layout.addStretch()
        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _create_category_card(self):
        """创建预设分类卡片"""
        cat_card = AnimatedCard()
        cat_card.setObjectName("card")
        apply_card_shadow(cat_card)
        cat_layout = QVBoxLayout(cat_card)
        cat_title = QLabel("预设分类")
        cat_title.setObjectName("card_title")
        cat_layout.addWidget(cat_title)

        self._tags_layout = QHBoxLayout()
        self._tags_layout.setSpacing(8)
        self._rebuild_category_tags()
        cat_layout.addLayout(self._tags_layout)

        # 添加自定义分类
        add_layout = QHBoxLayout()
        self.new_category_input = QLineEdit()
        self.new_category_input.setPlaceholderText("输入自定义分类名称...")
        self.new_category_input.setFixedHeight(36)
        add_layout.addWidget(self.new_category_input)

        btn_add = QPushButton("+ 添加分类")
        btn_add.clicked.connect(self._add_category)
        add_layout.addWidget(btn_add)
        cat_layout.addLayout(add_layout)

        return cat_card

    def _create_table_card(self):
        """创建应用分类管理表格卡片"""
        table_card = AnimatedCard()
        table_card.setObjectName("card")
        apply_card_shadow(table_card)
        table_layout = QVBoxLayout(table_card)
        table_title = QLabel("应用分类管理")
        table_title.setObjectName("card_title")
        table_layout.addWidget(table_title)

        desc = QLabel("为已记录的应用分配分类，标记为敏感的应用在统计中将以\"其他\"显示")
        desc.setObjectName("section_desc")
        table_layout.addWidget(desc)

        # 搜索/筛选栏
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        search_label = QLabel("🔍")
        filter_row.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索应用名称...")
        self.search_input.setFixedHeight(32)
        self.search_input.setFixedWidth(220)
        self.search_input.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.search_input)

        filter_label = QLabel("分类:")
        filter_label.setObjectName("card_title")
        filter_row.addWidget(filter_label)

        self.category_filter = QComboBox()
        self.category_filter.setFixedHeight(32)
        self.category_filter.setFixedWidth(140)
        self.category_filter.addItem("全部")
        for name, color, key in PRESET_CATEGORIES:
            self.category_filter.addItem(name)
        self.category_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.category_filter)

        # 应用计数标签
        self.filter_count_label = QLabel("")
        self.filter_count_label.setObjectName("section_desc")
        filter_row.addWidget(self.filter_count_label)

        # 使用限制按钮
        self.btn_app_limit = HoverButton("⏱ 使用限制")
        self.btn_app_limit.setFixedHeight(32)
        self.btn_app_limit.clicked.connect(self._on_open_limit_dialog)
        filter_row.addWidget(self.btn_app_limit)

        filter_row.addStretch()
        table_layout.addLayout(filter_row)

        self.app_table = QTableWidget()
        self.app_table.setColumnCount(4)
        self.app_table.setHorizontalHeaderLabels(["应用名称", "当前分类", "自定义分类", "敏感标记"])
        self.app_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.app_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.app_table)

        return table_card

    def _rebuild_category_tags(self):
        """重建分类标签"""
        # 清除旧标签
        while self._tags_layout.count():
            item = self._tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 初始化颜色映射
        self._category_color_map = {}
        for name, color, key in PRESET_CATEGORIES:
            self._category_color_map[key] = color
            tag = CategoryTag(name, color)
            self._tags_layout.addWidget(tag)

        # 添加自定义分类标签
        custom_colors = ["#EC4899", "#06B6D4", "#84CC16", "#F97316", "#A855F7"]
        for i, (name, color, key) in enumerate(self._custom_categories):
            self._category_color_map[key] = color
            tag = CategoryTag(name, color)
            self._tags_layout.addWidget(tag)

        self._tags_layout.addStretch()

    def _get_all_categories(self):
        """获取所有分类（预设+自定义）"""
        all_cats = list(PRESET_CATEGORIES)
        for name, color, key in self._custom_categories:
            all_cats.append((name, color, key))
        return all_cats

    def refresh(self, date: str = None, start_date: str = None, is_range: bool = False):
        """刷新分类管理数据"""
        # 从数据库加载应用设置
        app_settings = self.db.get_app_settings()
        self._sensitive_apps = {name for name, settings in app_settings.items() if settings.get("is_sensitive")}
        self._app_categories = {name: settings.get("custom_category") for name, settings in app_settings.items() if settings.get("custom_category")}

        # 范围模式下获取所有应用
        if is_range and start_date:
            self._all_app_summary = self.db.get_app_usage_summary_range(start_date, date)
        else:
            self._all_app_summary = self.db.get_app_usage_summary()

        # 更新分类筛选下拉（包含自定义分类）
        self._update_category_filter()

        # 应用筛选并填充表格
        self._apply_filter()

    def _update_category_filter(self):
        """更新分类筛选下拉选项"""
        current_index = self.category_filter.currentIndex()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("全部")
        all_cats = self._get_all_categories()
        for name, color, key in all_cats:
            self.category_filter.addItem(name)
        if current_index >= 0 and current_index <= self.category_filter.count() - 1:
            self.category_filter.setCurrentIndex(current_index)
        self.category_filter.blockSignals(False)

    def _on_filter_changed(self):
        """搜索或分类筛选变化"""
        self._apply_filter()

    def _apply_filter(self):
        """根据搜索文本和分类筛选应用表格"""
        if not hasattr(self, '_all_app_summary'):
            return

        search_text = self.search_input.text().strip().lower()
        filter_cat_index = self.category_filter.currentIndex()

        # 获取筛选分类key
        filter_cat_key = None
        if filter_cat_index > 0:
            all_cats = self._get_all_categories()
            if filter_cat_index - 1 < len(all_cats):
                filter_cat_key = all_cats[filter_cat_index - 1][2]

        # 筛选数据
        filtered = []
        for item in self._all_app_summary:
            app_name = item.get("app_name", "Unknown")

            # 搜索筛选
            if search_text and search_text not in app_name.lower():
                continue

            # 分类筛选
            if filter_cat_key:
                # 优先使用自定义分类，否则使用推断分类
                custom_cat = self._app_categories.get(app_name)
                current_cat = custom_cat if custom_cat else get_app_category(app_name)
                if current_cat != filter_cat_key:
                    continue

            filtered.append(item)

        # 填充表格并更新UI
        self._populate_filtered_table(filtered)
        self._update_filter_status(len(self._all_app_summary), len(filtered), search_text, filter_cat_key)

    def _populate_filtered_table(self, filtered):
        """填充筛选后的应用表格"""
        all_cats = self._get_all_categories()
        cat_keys = [c[2] for c in all_cats]
        cat_names = {c[2]: c[0] for c in all_cats}

        self.app_table.setRowCount(len(filtered))

        for row, item in enumerate(filtered):
            app_name = item.get("app_name", "Unknown")
            # 应用名称
            name_item = QTableWidgetItem(app_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.app_table.setItem(row, 0, name_item)

            # 当前分类（推断）
            current_cat = get_app_category(app_name)
            # 优先显示自定义分类
            custom_cat = self._app_categories.get(app_name)
            display_cat = custom_cat if custom_cat else current_cat
            current_item = QTableWidgetItem(cat_names.get(display_cat, "其他"))
            current_item.setFlags(current_item.flags() & ~Qt.ItemIsEditable)
            self.app_table.setItem(row, 1, current_item)

            # 自定义分类下拉
            combo = QComboBox()
            for name, color, key in all_cats:
                combo.addItem(name)
            # 选择当前分类
            if display_cat in cat_keys:
                combo.setCurrentIndex(cat_keys.index(display_cat))
            combo.currentIndexChanged.connect(
                lambda idx, app=app_name, cats=all_cats: self._on_category_changed(app, cats, idx)
            )
            self.app_table.setCellWidget(row, 2, combo)

            # 敏感标记复选框
            sensitive_cb = QCheckBox()
            sensitive_cb.setChecked(app_name in self._sensitive_apps)
            sensitive_cb.setStyleSheet("margin-left: 20px;")
            sensitive_cb.stateChanged.connect(
                lambda state, app=app_name: self._on_sensitive_changed(app, state)
            )
            self.app_table.setCellWidget(row, 3, sensitive_cb)

    def _update_filter_status(self, total, shown, search_text, filter_cat_key):
        """更新筛选状态标签和空状态显示"""
        if search_text or filter_cat_key:
            self.filter_count_label.setText(f"显示 {shown}/{total} 个应用")
        else:
            self.filter_count_label.setText(f"共 {total} 个应用")

        if shown > 0:
            self.app_table.show()
            self.empty_state.hide()
        else:
            self.app_table.hide()
            self.empty_state.show()
            self.empty_state.set_theme(self._is_dark)

    def _on_category_changed(self, app_name: str, categories: list, index: int):
        """自定义分类变更"""
        if 0 <= index < len(categories):
            _, _, key = categories[index]
            self._app_categories[app_name] = key
            # 持久化到数据库
            is_sensitive = app_name in self._sensitive_apps
            self.db.save_app_setting(app_name, custom_category=key, is_sensitive=is_sensitive)

    def _on_sensitive_changed(self, app_name: str, state: int):
        """敏感标记变更"""
        if state:
            self._sensitive_apps.add(app_name)
        else:
            self._sensitive_apps.discard(app_name)
        # 持久化到数据库
        custom_cat = self._app_categories.get(app_name)
        self.db.save_app_setting(app_name, custom_category=custom_cat, is_sensitive=bool(state))

    def _add_category(self):
        """添加自定义分类"""
        name = self.new_category_input.text().strip()
        if not name:
            return

        # 检查是否已存在
        existing_names = [c[0] for c in PRESET_CATEGORIES] + [c[0] for c in self._custom_categories]
        if name in existing_names:
            QMessageBox.warning(self, "提示", f"分类 \"{name}\" 已存在")
            return

        # 生成key和颜色
        key = f"custom_{name.lower().replace(' ', '_')}"
        custom_colors = ["#EC4899", "#06B6D4", "#84CC16", "#F97316", "#A855F7"]
        color_idx = len(self._custom_categories) % len(custom_colors)
        color = custom_colors[color_idx]

        self._custom_categories.append((name, color, key))
        self._save_custom_categories()
        self._rebuild_category_tags()
        self.new_category_input.clear()
        QMessageBox.information(self, "提示", f"分类 \"{name}\" 已添加")

    def set_theme(self, is_dark: bool):
        self._is_dark = is_dark

    def _on_open_limit_dialog(self):
        """打开应用使用限制设置对话框"""
        from gui.app_limit_dialog import AppLimitDialog
        dialog = AppLimitDialog(self.db, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.set_theme(self._is_dark)
        dialog.limits_changed.connect(self.refresh)
        dialog.exec_()

    def highlight_app(self, app_name: str):
        """高亮指定应用行（从仪表盘Top5跳转过来）"""
        # 刷新数据确保最新
        self.refresh()
        # 在表格中查找并选中该应用
        for row in range(self.app_table.rowCount()):
            item = self.app_table.item(row, 0)
            if item and app_name.lower() in item.text().lower():
                self.app_table.selectRow(row)
                self.app_table.scrollToItem(item)
                # 闪烁高亮效果
                self.app_table.setStyleSheet(
                    self.app_table.styleSheet() + 
                    f"\nQTableWidget::item:selected {{ background-color: #3B82F6; }}"
                )
                break