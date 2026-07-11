"""截图浏览页面 - 查看已保存的截图缩略图，支持日期范围筛选和分页"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QGridLayout,
    QDateEdit
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap

from database.db_manager import DatabaseManager
from gui.themes import get_colors, QSS_STYLES, EmptyStateWidget, apply_card_shadow, AnimatedCard, HoverButton


class ThumbnailLoadWorker(QThread):
    """异步缩略图加载Worker"""
    loaded = pyqtSignal(str, QPixmap)  # (path, pixmap)

    def __init__(self, paths: list, size: tuple = (188, 106), parent: QWidget=None) -> None:
        super().__init__(parent)
        self._paths = paths
        self._size = size
        self._cancelled = False

    def run(self) -> None:
        """执行任务"""
        for path in self._paths:
            if self._cancelled:
                break
            if path and os.path.exists(path):
                try:
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(
                            self._size[0], self._size[1],
                            Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                        self.loaded.emit(path, scaled)
                except Exception:
                    pass

    def cancel(self) -> None:
        """取消操作"""
        self._cancelled = True


class ScreenshotThumbnail(QFrame):
    """截图缩略图卡片 - 支持异步加载"""

    # 类级别缓存：path -> QPixmap
    _pixmap_cache = {}

    # 点击信号
    clicked = pyqtSignal(str, list, int)  # (file_path, image_list, index)

    def __init__(self, file_path: str, thumbnail_path: str, timestamp: str,
                 app_name: str = "", index: int = 0, image_list: list = None, parent: QWidget=None) -> None:
        super().__init__(parent)
        self._file_path = file_path
        self._thumbnail_path = thumbnail_path
        self._timestamp = timestamp
        self._app_name = app_name
        self._index = index
        self._image_list = image_list or [file_path]
        self._is_dark = False
        self._colors = get_colors(False)
        self.setObjectName("card")
        apply_card_shadow(self)
        self.setFixedSize(200, 170)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # 缩略图
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(188, 106)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet(f"background-color: {self._colors['border']}; border-radius: 4px;")
        self._load_thumbnail()
        layout.addWidget(self.thumb_label)

        # 时间
        time_label = QLabel(self._timestamp.split(" ")[1][:8] if " " in self._timestamp else self._timestamp)
        time_label.setObjectName("metric_title")
        time_label.setStyleSheet(QSS_STYLES["small_text"].format(c=self._colors))
        layout.addWidget(time_label)

        # 应用名
        if self._app_name:
            app_label = QLabel(self._app_name)
            app_label.setObjectName("section_desc")
            app_label.setStyleSheet(f"font-size: 10px; color: {self._colors['text_muted']};")
            layout.addWidget(app_label)

    def _load_thumbnail(self) -> str:
        """异步加载缩略图（优先使用缓存）"""
        thumb_path = self._thumbnail_path or self._file_path

        # 1. 检查缓存
        if thumb_path in ScreenshotThumbnail._pixmap_cache:
            self.thumb_label.setPixmap(ScreenshotThumbnail._pixmap_cache[thumb_path])
            self.thumb_label.setStyleSheet("border-radius: 4px;")
            return

        # 2. 快速同步加载（缩略图文件通常很小）
        if thumb_path and os.path.exists(thumb_path):
            try:
                pixmap = QPixmap(thumb_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(188, 106, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    ScreenshotThumbnail._pixmap_cache[thumb_path] = scaled
                    self.thumb_label.setPixmap(scaled)
                    self.thumb_label.setStyleSheet("border-radius: 4px;")
                    return
            except Exception:
                pass

        # 3. 加载失败显示占位
        self.thumb_label.setText("📷")
        self.thumb_label.setStyleSheet(
            f"background-color: {self._colors['border']}; border-radius: 4px; "
            f"font-size: 32px; color: {self._colors['text_muted']};"
        )

    @classmethod
    def clear_cache(cls) -> None:
        """清空缩略图缓存"""
        cls._pixmap_cache.clear()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """点击缩略图 - 发送点击信号"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._file_path, self._image_list, self._index)

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        # 重新应用缩略图占位符样式（已加载图片的不需要更新）
        if not self.thumb_label.pixmap():
            self.thumb_label.setStyleSheet(
                f"background-color: {self._colors['border']}; border-radius: 4px;"
            )


class ScreenshotsPage(QWidget):
    """截图浏览页面 - 支持日期范围筛选和分页"""

    PAGE_SIZE = 20  # 每页显示数量

    def __init__(self, db_manager: DatabaseManager, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.db = db_manager
        self._is_dark = False
        self._colors = get_colors(False)
        self._current_page = 1
        self._total_count = 0
        self._total_pages = 1
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setSpacing(16)
        self._main_layout.setContentsMargins(24, 20, 24, 20)

        self._main_layout.addLayout(self._create_header())
        self._main_layout.addWidget(self._create_date_filter_card())
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("metric_title")
        self._main_layout.addWidget(self.stats_label)
        self._main_layout.addWidget(self._create_grid_area())
        self.empty_state = EmptyStateWidget(
            icon="📸", title="还没有截图数据",
            description="开启截图监控后，这里将展示屏幕快照"
        )
        self.empty_state.setFixedHeight(300)
        self.empty_state.hide()
        self._main_layout.addWidget(self.empty_state)
        self._main_layout.addWidget(self._create_page_bar())
        self._main_layout.addStretch()

        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _create_header(self) -> None:
        """创建标题行"""
        header_layout = QHBoxLayout()
        title = QLabel("截图浏览")
        title.setObjectName("page_title")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # 屏幕回放按钮
        self.btn_playback = HoverButton("🎬 屏幕回放")
        self.btn_playback.setObjectName("btn_primary")
        self.btn_playback.clicked.connect(self._open_playback)
        header_layout.addWidget(self.btn_playback)

        # 截图目录按钮
        self.btn_open_dir = HoverButton("📂 打开截图目录")
        self.btn_open_dir.setObjectName("btn_outline")
        self.btn_open_dir.clicked.connect(self._open_screenshot_dir)
        header_layout.addWidget(self.btn_open_dir)

        # 描述
        desc = QLabel("查看监控期间自动截取的屏幕快照，点击可查看原图")
        desc.setObjectName("section_desc")
        # 将描述也加入header_layout下方（通过返回包含两者的布局）
        vbox = QVBoxLayout()
        vbox.addLayout(header_layout)
        vbox.addWidget(desc)
        return vbox

    def _create_date_filter_card(self) -> None:
        """创建日期范围筛选卡片"""
        date_card = AnimatedCard()
        date_card.setObjectName("card")
        apply_card_shadow(date_card)
        date_layout = QHBoxLayout(date_card)
        date_layout.setContentsMargins(16, 12, 16, 12)
        date_layout.setSpacing(12)

        date_label = QLabel("日期范围：")
        date_label.setObjectName("metric_title")
        date_layout.addWidget(date_label)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.setDate(QDate.currentDate().addDays(-7))
        self.date_start.setFixedWidth(130)
        date_layout.addWidget(self.date_start)

        sep_label = QLabel("至")
        sep_label.setObjectName("section_desc")
        date_layout.addWidget(sep_label)

        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setFixedWidth(130)
        date_layout.addWidget(self.date_end)

        date_layout.addStretch()

        self.btn_query = HoverButton("查询")
        self.btn_query.setObjectName("btn_primary")
        self.btn_query.setFixedWidth(80)
        self.btn_query.clicked.connect(self._on_query)
        date_layout.addWidget(self.btn_query)

        self.btn_today = HoverButton("今天")
        self.btn_today.setObjectName("btn_outline")
        self.btn_today.setFixedWidth(60)
        self.btn_today.clicked.connect(self._on_today)
        date_layout.addWidget(self.btn_today)

        self.btn_recent7 = HoverButton("近7天")
        self.btn_recent7.setObjectName("btn_outline")
        self.btn_recent7.setFixedWidth(60)
        self.btn_recent7.clicked.connect(self._on_recent7)
        date_layout.addWidget(self.btn_recent7)

        return date_card

    def _create_grid_area(self) -> None:
        """创建截图网格区域"""
        self.grid_card = AnimatedCard()
        self.grid_card.setObjectName("card")
        apply_card_shadow(self.grid_card)
        self.grid_layout = QGridLayout(self.grid_card)
        self.grid_layout.setSpacing(12)

        return self.grid_card

    def _create_page_bar(self) -> None:
        """创建分页控件"""
        self._page_bar = QFrame()
        self._page_bar.setObjectName("card")
        apply_card_shadow(self._page_bar)
        page_layout = QHBoxLayout(self._page_bar)
        page_layout.setContentsMargins(16, 8, 16, 8)
        page_layout.setSpacing(8)

        page_layout.addStretch()

        self.btn_prev = HoverButton("◀ 上一页")
        self.btn_prev.setObjectName("btn_outline")
        self.btn_prev.setFixedWidth(100)
        self.btn_prev.clicked.connect(self._on_prev_page)
        self.btn_prev.setEnabled(False)
        page_layout.addWidget(self.btn_prev)

        self.page_label = QLabel("1 / 1")
        self.page_label.setObjectName("metric_title")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setFixedWidth(80)
        page_layout.addWidget(self.page_label)

        self.btn_next = HoverButton("下一页 ▶")
        self.btn_next.setObjectName("btn_outline")
        self.btn_next.setFixedWidth(100)
        self.btn_next.clicked.connect(self._on_next_page)
        self.btn_next.setEnabled(False)
        page_layout.addWidget(self.btn_next)

        page_layout.addStretch()

        self._page_bar.hide()
        return self._page_bar

    def _on_query(self) -> None:
        """查询按钮点击"""
        self._current_page = 1
        self.refresh()

    def _on_today(self) -> None:
        """快捷：今天"""
        self.date_start.setDate(QDate.currentDate())
        self.date_end.setDate(QDate.currentDate())
        self._current_page = 1
        self.refresh()

    def _on_recent7(self) -> None:
        """快捷：近7天"""
        self.date_start.setDate(QDate.currentDate().addDays(-6))
        self.date_end.setDate(QDate.currentDate())
        self._current_page = 1
        self.refresh()

    def _on_prev_page(self) -> None:
        """上一页"""
        if self._current_page > 1:
            self._current_page -= 1
            self.refresh()

    def _on_next_page(self) -> None:
        """下一页"""
        if self._current_page < self._total_pages:
            self._current_page += 1
            self.refresh()

    def refresh(self) -> None:
        """刷新截图列表（使用日期范围+分页）"""
        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")

        # 清除旧的缩略图
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 清理缩略图缓存（防止内存泄漏，保留最近3页）
        if self._current_page == 1:
            ScreenshotThumbnail.clear_cache()

        if not screenshots:
            self.grid_card.hide()
            self.empty_state.show()
            self.empty_state.set_theme(self._is_dark)
            self.stats_label.setText("")
            self._page_bar.hide()
            return

        self.grid_card.show()
        self.empty_state.hide()
        self.stats_label.setText(
            f"共 {self._total_count} 张截图（第 {self._current_page}/{self._total_pages} 页）"
        )

        # 按网格排列（每行4个）
        cols = 4
        # 构建图片路径列表（用于大图翻页）
        image_list = [shot.get("file_path", "") for shot in screenshots if shot.get("file_path")]
        for i, shot in enumerate(screenshots):
            row = i // cols
            col = i % cols
            thumb = ScreenshotThumbnail(
                file_path=shot.get("file_path", ""),
                thumbnail_path=shot.get("thumbnail_path", ""),
                timestamp=shot.get("timestamp", ""),
                app_name=shot.get("app_name", ""),
                index=i,
                image_list=image_list
            )
            thumb.clicked.connect(self._on_thumbnail_clicked)
            thumb.set_theme(self._is_dark)
            self.grid_layout.addWidget(thumb, row, col)

        # 更新分页控件
        self._update_page_bar()

    def _update_page_bar(self) -> None:
        """更新分页控件状态"""
        if self._total_pages <= 1:
            self._page_bar.hide()
            return

        self._page_bar.show()
        self.btn_prev.setEnabled(self._current_page > 1)
        self.btn_next.setEnabled(self._current_page < self._total_pages)
        self.page_label.setText(f"{self._current_page} / {self._total_pages}")

    def set_theme(self, is_dark: bool) -> None:
        """更新主题"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        # 更新已有缩略图的主题
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().set_theme(is_dark)

        # 更新日期选择器样式
        colors = self._colors
        date_qss = f"""
            QDateEdit {{
                background-color: {colors['bg_card']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }}
            QDateEdit::drop-down {{
                border: none;
                width: 24px;
            }}
            QDateEdit QCalendarWidget QToolButton {{
                color: {colors['text_primary']};
                background-color: {colors['bg_card']};
            }}
            QDateEdit QCalendarWidget QMenu {{
                background-color: {colors['bg_card']};
                color: {colors['text_primary']};
            }}
        """
        self.date_start.setStyleSheet(date_qss)
        self.date_end.setStyleSheet(date_qss)

        # 更新HoverButton阴影主题
        for btn in [self.btn_playback, self.btn_query, self.btn_today, self.btn_recent7, self.btn_open_dir,
                     self.btn_prev, self.btn_next]:
            if hasattr(btn, 'set_theme'):
                btn.set_theme(is_dark)

    def _on_thumbnail_clicked(self, file_path: str, image_list: list, index: int) -> None:
        """缩略图点击 - 打开大图查看器"""
        from gui.image_viewer import ImageViewerDialog
        if not os.path.exists(file_path):
            return
        viewer = ImageViewerDialog(file_path, image_list, index, self)
        viewer.setStyleSheet(self.styleSheet())
        viewer.set_theme(self._is_dark)
        viewer.exec_()

    def _open_playback(self) -> None:
        """打开屏幕回放对话框"""
        from gui.screen_playback import ScreenPlaybackDialog

        start_date = self.date_start.date().toString("yyyy-MM-dd")
        end_date = self.date_end.date().toString("yyyy-MM-dd")

        # 获取当前日期范围内的所有截图（用于回放）
        screenshots = self.db.get_screenshots_for_playback(start_date, end_date)
        if not screenshots:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "屏幕回放",
                f"在 {start_date} 至 {end_date} 范围内没有截图数据，无法回放。"
            )
            return

        dialog = ScreenPlaybackDialog(screenshots, self.db, self)
        dialog.set_theme(self._is_dark)
        dialog.exec_()

    def _open_screenshot_dir(self) -> None:
        """打开截图保存目录"""
        screenshot_dir = os.path.join(
            os.path.expanduser("~"), ".computer_monitor", "screenshots"
        )
        if os.path.exists(screenshot_dir):
            try:
                os.startfile(screenshot_dir)
            except Exception:
                pass
        else:
            os.makedirs(screenshot_dir, exist_ok=True)
            try:
                os.startfile(screenshot_dir)
            except Exception:
                pass