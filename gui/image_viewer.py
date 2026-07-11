"""图片大图查看器 - 支持缩放、拖拽、前后翻页"""

import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QCursor


class ImageViewerDialog(QDialog):
    """图片大图查看器
    
    支持功能：
    - 鼠标滚轮缩放
    - 拖拽平移
    - 左右翻页浏览同组截图
    - ESC关闭
    """

    def __init__(self, image_path: str, image_list: list = None, current_index: int = 0, parent: QWidget=None) -> None:
        """
        Args:
            image_path: 当前图片路径
            image_list: 同组图片路径列表（用于翻页）
            current_index: 当前图片在列表中的索引
            parent: 父窗口
        """
        super().__init__(parent)
        self._image_list = image_list or [image_path]
        self._current_index = current_index
        self._is_dark = False
        self._colors = get_colors(False)

        # 缩放状态
        self._scale = 1.0
        self._min_scale = 0.1
        self._max_scale = 5.0
        self._drag_start = None
        self._drag_offset = (0, 0)

        self.setWindowTitle("图片查看")
        self.setMinimumSize(800, 600)
        self.setWindowState(Qt.WindowMaximized)

        self._setup_ui()
        self._load_image(image_path)

    def _setup_ui(self) -> None:
        """构建UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._create_toolbar())
        layout.addWidget(self._create_image_area())
        layout.addWidget(self._create_status_bar())

    def _create_toolbar(self) -> None:
        """创建顶部工具栏"""
        toolbar = QWidget()
        toolbar.setFixedHeight(48)
        toolbar.setObjectName("toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)

        # 图片信息
        self.info_label = QLabel("")
        self.info_label.setObjectName("metric_title")
        toolbar_layout.addWidget(self.info_label)
        toolbar_layout.addStretch()

        # 缩放控制
        self.btn_zoom_out = QPushButton("➖")
        self.btn_zoom_out.setFixedSize(32, 32)
        self.btn_zoom_out.setObjectName("btn_outline")
        self.btn_zoom_out.setToolTip("缩小")
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        toolbar_layout.addWidget(self.btn_zoom_out)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(60)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setObjectName("metric_title")
        toolbar_layout.addWidget(self.zoom_label)

        self.btn_zoom_in = QPushButton("➕")
        self.btn_zoom_in.setFixedSize(32, 32)
        self.btn_zoom_in.setObjectName("btn_outline")
        self.btn_zoom_in.setToolTip("放大")
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        toolbar_layout.addWidget(self.btn_zoom_in)

        self.btn_fit = QPushButton("🔲 适应窗口")
        self.btn_fit.setFixedHeight(32)
        self.btn_fit.setObjectName("btn_outline")
        self.btn_fit.setToolTip("适应窗口大小")
        self.btn_fit.clicked.connect(self._fit_to_window)
        toolbar_layout.addWidget(self.btn_fit)

        # 翻页按钮
        if len(self._image_list) > 1:
            self.btn_prev = QPushButton("◀ 上一张")
            self.btn_prev.setFixedHeight(32)
            self.btn_prev.setObjectName("btn_outline")
            self.btn_prev.clicked.connect(self._show_prev)
            toolbar_layout.addWidget(self.btn_prev)

            self.btn_next = QPushButton("下一张 ▶")
            self.btn_next.setFixedHeight(32)
            self.btn_next.setObjectName("btn_outline")
            self.btn_next.clicked.connect(self._show_next)
            toolbar_layout.addWidget(self.btn_next)

        self.btn_close = QPushButton("✕ 关闭")
        self.btn_close.setFixedHeight(32)
        self.btn_close.setObjectName("btn_outline")
        self.btn_close.clicked.connect(self.close)
        toolbar_layout.addWidget(self.btn_close)

        return toolbar

    def _create_image_area(self) -> None:
        """创建图片显示区域"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setCursor(QCursor(Qt.OpenHandCursor))
        self.scroll_area.setWidget(self.image_label)

        return self.scroll_area

    def _create_status_bar(self) -> None:
        """创建底部状态栏"""
        self.status_label = QLabel("")
        self.status_label.setFixedHeight(28)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("section_desc")
        self.status_label.setStyleSheet("font-size: 11px; padding: 4px;")
        return self.status_label

    def _load_image(self, image_path: str) -> None:
        """加载图片"""
        self._current_path = image_path
        self._original_pixmap = QPixmap(image_path)

        if self._original_pixmap.isNull():
            self.image_label.setText("📷 无法加载图片")
            colors = self._colors
            self.image_label.setStyleSheet(
                f"font-size: 48px; color: {colors['text_muted']}; background-color: {colors['bg_primary']}; "
                f"min-width: 600px; min-height: 400px;"
            )
            return

        # 更新信息
        filename = os.path.basename(image_path)
        w, h = self._original_pixmap.width(), self._original_pixmap.height()
        size_kb = os.path.getsize(image_path) / 1024

        self.info_label.setText(f"📷 {filename}")
        self.status_label.setText(
            f"{w} × {h} | {size_kb:.0f} KB | "
            f"{'第 %d/%d 张' % (self._current_index + 1, len(self._image_list)) if len(self._image_list) > 1 else ''}"
            f" | 滚轮缩放 | 拖拽平移 | ESC关闭"
        )

        # 适应窗口
        self._fit_to_window()

        # 更新翻页按钮状态
        if len(self._image_list) > 1:
            self.btn_prev.setEnabled(self._current_index > 0)
            self.btn_next.setEnabled(self._current_index < len(self._image_list) - 1)

    def _update_display(self) -> None:
        """根据当前缩放比例更新显示"""
        if not hasattr(self, '_original_pixmap') or self._original_pixmap.isNull():
            return

        new_w = int(self._original_pixmap.width() * self._scale)
        new_h = int(self._original_pixmap.height() * self._scale)

        scaled = self._original_pixmap.scaled(
            new_w, new_h,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())
        self.zoom_label.setText(f"{int(self._scale * 100)}%")

    def _fit_to_window(self) -> None:
        """适应窗口大小"""
        if not hasattr(self, '_original_pixmap') or self._original_pixmap.isNull():
            return

        viewport_w = self.scroll_area.viewport().width() - 20
        viewport_h = self.scroll_area.viewport().height() - 20
        img_w = self._original_pixmap.width()
        img_h = self._original_pixmap.height()

        if img_w <= 0 or img_h <= 0:
            return

        scale_w = viewport_w / img_w
        scale_h = viewport_h / img_h
        self._scale = min(scale_w, scale_h, 1.0)  # 不超过100%
        self._scale = max(self._scale, self._min_scale)
        self._update_display()

    def _zoom_in(self) -> None:
        """放大"""
        self._scale = min(self._scale * 1.25, self._max_scale)
        self._update_display()

    def _zoom_out(self) -> None:
        """缩小"""
        self._scale = max(self._scale / 1.25, self._min_scale)
        self._update_display()

    def _show_prev(self) -> None:
        """显示上一张"""
        if self._current_index > 0:
            self._current_index -= 1
            self._load_image(self._image_list[self._current_index])

    def _show_next(self) -> None:
        """显示下一张"""
        if self._current_index < len(self._image_list) - 1:
            self._current_index += 1
            self._load_image(self._image_list[self._current_index])

    def wheelEvent(self, event: QEvent) -> None:
        """鼠标滚轮缩放"""
        delta = event.angleDelta().y()
        if delta > 0:
            self._zoom_in()
        else:
            self._zoom_out()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下 - 开始拖拽"""
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()
            self.image_label.setCursor(QCursor(Qt.ClosedHandCursor))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动 - 拖拽平移"""
        if self._drag_start and event.buttons() & Qt.LeftButton:
            delta = event.pos() - self._drag_start
            self._drag_start = event.pos()
            h_bar = self.scroll_area.horizontalScrollBar()
            v_bar = self.scroll_area.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放 - 结束拖拽"""
        if event.button() == Qt.LeftButton:
            self._drag_start = None
            self.image_label.setCursor(QCursor(Qt.OpenHandCursor))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """键盘事件"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Left and len(self._image_list) > 1:
            self._show_prev()
        elif event.key() == Qt.Key_Right and len(self._image_list) > 1:
            self._show_next()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self._zoom_in()
        elif event.key() == Qt.Key_Minus:
            self._zoom_out()
        elif event.key() == Qt.Key_0:
            self._fit_to_window()
        else:
            super().keyPressEvent(event)

    def set_theme(self, is_dark: bool) -> None:
        """设置主题"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        colors = self._colors
        self.setStyleSheet(f"""
            QDialog {{ background-color: {colors['bg_primary']}; }}
            #toolbar {{ background-color: {colors['bg_card']}; border-bottom: 1px solid {colors['border']}; }}
            QScrollArea {{ background-color: {colors['bg_primary']}; }}
        """)


from gui.themes import get_colors