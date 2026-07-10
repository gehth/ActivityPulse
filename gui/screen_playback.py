"""屏幕回放对话框 - 按时间顺序播放截图序列，支持速度控制和时间轴导航

功能：
- 自动/手动播放截图序列
- 多档播放速度（0.5x/1x/2x/4x/8x/16x）
- 时间轴滑块导航
- 当前时间+截图信息显示
- 键盘快捷键（空格播放/暂停，左右切换，上下调速）
- 深色模式支持
"""

import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSlider, QWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from gui.themes import get_colors, QSS_STYLES


class ScreenPlaybackDialog(QDialog):
    """屏幕回放对话框"""

    # 播放速度选项
    SPEED_OPTIONS = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]

    def __init__(self, screenshots: list, db_manager: DatabaseManager=None, parent: QWidget=None) -> None:
        """
        Args:
            screenshots: 截图记录列表，每项含file_path/thumbnail_path/app_name/timestamp
            db_manager: 数据库管理器（用于获取关联的应用使用记录）
            parent: 父窗口
        """
        super().__init__(parent)
        self._screenshots = screenshots
        self._db = db_manager
        self._current_index = 0
        self._is_playing = False
        self._speed_index = 2  # 默认1x (SPEED_OPTIONS[2]=1.0... 不对，index 1才是1.0)
        self._speed_index = 1  # 默认1x
        self._is_dark = False
        self._colors = get_colors(False)

        # 播放定时器
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._on_play_tick)

        # 图片缓存（最近10张）
        self._pixmap_cache = {}
        self._cache_max = 10

        # 过滤有效截图
        self._valid_screenshots = [
            s for s in screenshots
            if s.get("file_path") and os.path.exists(s.get("file_path", ""))
        ]

        if not self._valid_screenshots:
            self._valid_screenshots = [
                s for s in screenshots
                if s.get("thumbnail_path") and os.path.exists(s.get("thumbnail_path", ""))
            ]

        self.setWindowTitle("屏幕回放")
        self.setMinimumSize(900, 650)
        self.resize(1100, 750)
        self._setup_ui()
        self._load_current_frame()

    def _setup_ui(self) -> None:
        """构建UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self._create_top_bar())
        layout.addWidget(self._create_image_area(), 1)
        layout.addWidget(self._create_control_bar())

        # 初始化显示
        self._update_speed_display()
        self._update_count_display()

        # 设置时间轴标签
        if self._valid_screenshots:
            first_ts = self._valid_screenshots[0].get("timestamp", "")
            last_ts = self._valid_screenshots[-1].get("timestamp", "")
            self._start_time_label.setText(self._format_time(first_ts))
            self._end_time_label.setText(self._format_time(last_ts))

    def _create_top_bar(self) -> None:
        """创建顶部信息栏"""
        top_bar = QFrame()
        top_bar.setObjectName("toolbar")
        top_bar.setFixedHeight(44)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)

        self._title_label = QLabel("🎬 屏幕回放")
        self._title_label.setObjectName("page_title")
        self._title_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        top_layout.addWidget(self._title_label)

        top_layout.addStretch()

        self._count_label = QLabel("")
        self._count_label.setObjectName("metric_title")
        self._count_label.setStyleSheet("font-size: 12px; font-weight: 500;")
        top_layout.addWidget(self._count_label)

        self._time_label = QLabel("")
        self._time_label.setObjectName("metric_title")
        self._time_label.setStyleSheet("font-size: 12px; font-weight: 500; margin-left: 16px;")
        top_layout.addWidget(self._time_label)

        return top_bar

    def _create_image_area(self) -> None:
        """创建中间图片显示区"""
        self._image_container = QWidget()
        self._image_container.setObjectName("playback_image_area")
        image_layout = QVBoxLayout(self._image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._image_label.setMinimumSize(640, 360)
        self._image_label.setStyleSheet("background-color: #F3F4F6;")  # 浅色默认，set_theme会覆盖
        image_layout.addWidget(self._image_label)

        # 应用名叠加层
        self._app_overlay = QLabel("")
        self._app_overlay.setObjectName("app_overlay")
        self._app_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 160);
                color: #F9FAFB;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
            }
        """)  # overlay白色文字在半透明黑底上，暗色模式无需变更
        self._app_overlay.setParent(self._image_label)
        self._app_overlay.move(12, 12)
        self._app_overlay.hide()

        return self._image_container

    def _create_control_bar(self) -> None:
        """创建底部控制栏"""
        control_frame = QFrame()
        control_frame.setObjectName("toolbar")
        control_frame.setFixedHeight(120)
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(16, 8, 16, 8)
        control_layout.setSpacing(6)

        # --- 时间轴滑块行 ---
        timeline_row = QHBoxLayout()
        timeline_row.setSpacing(8)

        self._start_time_label = QLabel("--:--")
        self._start_time_label.setObjectName("section_desc")
        self._start_time_label.setFixedWidth(50)
        self._start_time_label.setStyleSheet("font-size: 11px; font-weight: 400;")
        timeline_row.addWidget(self._start_time_label)

        self._timeline_slider = QSlider(Qt.Horizontal)
        self._timeline_slider.setObjectName("timeline_slider")
        self._timeline_slider.setMinimum(0)
        self._timeline_slider.setMaximum(max(0, len(self._valid_screenshots) - 1))
        self._timeline_slider.setValue(0)
        self._timeline_slider.setTracking(True)
        self._timeline_slider.valueChanged.connect(self._on_slider_changed)
        timeline_row.addWidget(self._timeline_slider, 1)

        self._end_time_label = QLabel("--:--")
        self._end_time_label.setObjectName("section_desc")
        self._end_time_label.setFixedWidth(50)
        self._end_time_label.setStyleSheet("font-size: 11px; font-weight: 400;")
        timeline_row.addWidget(self._end_time_label)

        control_layout.addLayout(timeline_row)

        # --- 播放控制行 ---
        play_row = QHBoxLayout()
        play_row.setSpacing(8)

        # 上一张
        self._btn_prev = QPushButton("⏮")
        self._btn_prev.setFixedSize(36, 36)
        self._btn_prev.setObjectName("btn_outline")
        self._btn_prev.setToolTip("上一张 (←)")
        self._btn_prev.clicked.connect(self._show_prev)
        play_row.addWidget(self._btn_prev)

        # 播放/暂停
        self._btn_play = QPushButton("▶")
        self._btn_play.setFixedSize(44, 44)
        self._btn_play.setObjectName("btn_primary")
        self._btn_play.setToolTip("播放/暂停 (空格)")
        self._btn_play.clicked.connect(self._toggle_play)
        play_row.addWidget(self._btn_play)

        # 下一张
        self._btn_next = QPushButton("⏭")
        self._btn_next.setFixedSize(36, 36)
        self._btn_next.setObjectName("btn_outline")
        self._btn_next.setToolTip("下一张 (→)")
        self._btn_next.clicked.connect(self._show_next)
        play_row.addWidget(self._btn_next)

        # 停止
        self._btn_stop = QPushButton("⏹")
        self._btn_stop.setFixedSize(36, 36)
        self._btn_stop.setObjectName("btn_outline")
        self._btn_stop.setToolTip("停止并回到开头")
        self._btn_stop.clicked.connect(self._stop_playback)
        play_row.addWidget(self._btn_stop)

        play_row.addSpacing(16)

        # 速度控制
        speed_label = QLabel("速度：")
        speed_label.setObjectName("metric_title")
        speed_label.setStyleSheet("font-size: 12px; font-weight: 500;")
        play_row.addWidget(speed_label)

        self._btn_speed_down = QPushButton("➖")
        self._btn_speed_down.setFixedSize(28, 28)
        self._btn_speed_down.setObjectName("btn_outline")
        self._btn_speed_down.setToolTip("减速 (↓)")
        self._btn_speed_down.clicked.connect(self._speed_down)
        play_row.addWidget(self._btn_speed_down)

        self._speed_label = QLabel("1x")
        self._speed_label.setFixedWidth(40)
        self._speed_label.setAlignment(Qt.AlignCenter)
        self._speed_label.setObjectName("metric_title")
        self._speed_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        play_row.addWidget(self._speed_label)

        self._btn_speed_up = QPushButton("➕")
        self._btn_speed_up.setFixedSize(28, 28)
        self._btn_speed_up.setObjectName("btn_outline")
        self._btn_speed_up.setToolTip("加速 (↑)")
        self._btn_speed_up.clicked.connect(self._speed_up)
        play_row.addWidget(self._btn_speed_up)

        play_row.addStretch()

        # 进度信息
        self._progress_label = QLabel("")
        self._progress_label.setObjectName("section_desc")
        self._progress_label.setStyleSheet("font-size: 11px; font-weight: 400;")
        play_row.addWidget(self._progress_label)

        # 关闭按钮
        self._btn_close = QPushButton("✕ 关闭")
        self._btn_close.setFixedHeight(32)
        self._btn_close.setObjectName("btn_outline")
        self._btn_close.clicked.connect(self._on_close)
        play_row.addWidget(self._btn_close)

        control_layout.addLayout(play_row)

        # --- 快捷键提示 ---
        hint_label = QLabel("空格：播放/暂停  |  ←→：切换截图  |  ↑↓：调速  |  Home/End：首尾跳转")
        hint_label.setObjectName("section_desc")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet("font-size: 10px; color: #9CA3AF;")  # muted灰色，由set_theme统一覆盖
        control_layout.addWidget(hint_label)

        return control_frame

    def _format_time(self, timestamp: str) -> str:
        """格式化时间戳为HH:MM"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%H:%M")
        except (ValueError, TypeError):
            return "--:--"

    def _format_datetime(self, timestamp: str) -> str:
        """格式化时间戳为HH:MM:SS"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            return "--:--:--"

    def _get_play_interval(self) -> int:
        """获取当前播放间隔（毫秒）"""
        speed = self.SPEED_OPTIONS[self._speed_index]
        # 基础间隔1000ms，按速度倒数缩放
        base_ms = 1000
        return max(50, int(base_ms / speed))

    def _load_current_frame(self) -> None:
        """加载当前帧截图"""
        if not self._valid_screenshots:
            self._image_label.setText("📷 没有可播放的截图")
            img_bg = "#111827" if self._is_dark else "#F3F4F6"
            self._image_label.setStyleSheet(
                f"font-size: 48px; color: {self._colors['text_muted']}; "
                f"background-color: {img_bg}; min-width: 640px; min-height: 360px;"
            )
            return

        shot = self._valid_screenshots[self._current_index]
        file_path = shot.get("file_path", "")
        thumb_path = shot.get("thumbnail_path", "")
        app_name = shot.get("app_name", "")
        timestamp = shot.get("timestamp", "")

        # 加载并显示图片
        self._display_frame_image(file_path, thumb_path)

        # 更新界面信息
        self._update_frame_info(app_name, timestamp)

    def _display_frame_image(self, file_path: str, thumb_path: str) -> None:
        """加载并显示帧图片（带缓存）"""
        load_path = file_path if os.path.exists(file_path) else thumb_path
        img_bg = "#111827" if self._is_dark else "#F3F4F6"

        if load_path and os.path.exists(load_path):
            # 检查缓存
            if load_path in self._pixmap_cache:
                pixmap = self._pixmap_cache[load_path]
            else:
                pixmap = QPixmap(load_path)
                if not pixmap.isNull():
                    # 管理缓存大小
                    if len(self._pixmap_cache) >= self._cache_max:
                        oldest_key = next(iter(self._pixmap_cache))
                        del self._pixmap_cache[oldest_key]
                    self._pixmap_cache[load_path] = pixmap

            if not pixmap.isNull():
                label_size = self._image_label.size()
                scaled = pixmap.scaled(
                    label_size.width() - 20, label_size.height() - 20,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self._image_label.setPixmap(scaled)
                self._image_label.setStyleSheet(f"background-color: {img_bg};")
            else:
                self._image_label.setText("📷 无法加载图片")
                self._image_label.setStyleSheet(
                    f"font-size: 32px; color: {self._colors['text_muted']}; background-color: {img_bg};"
                )
        else:
            self._image_label.setText("📷 文件不存在")
            self._image_label.setStyleSheet(
                f"font-size: 32px; color: {self._colors['text_muted']}; background-color: {img_bg};"
            )

    def _update_frame_info(self, app_name: str, timestamp: str) -> None:
        """更新帧信息（应用名、时间、进度、滑块、按钮）"""
        # 更新应用名叠加层
        if app_name:
            self._app_overlay.setText(f"  {app_name}  ")
            self._app_overlay.adjustSize()
            self._app_overlay.show()
        else:
            self._app_overlay.hide()

        # 更新时间显示
        self._time_label.setText(f"🕐 {self._format_datetime(timestamp)}")

        # 更新进度
        total = len(self._valid_screenshots)
        self._progress_label.setText(f"第 {self._current_index + 1} / {total} 张")

        # 更新滑块（不触发信号）
        self._timeline_slider.blockSignals(True)
        self._timeline_slider.setValue(self._current_index)
        self._timeline_slider.blockSignals(False)

        # 更新按钮状态
        self._btn_prev.setEnabled(self._current_index > 0)
        self._btn_next.setEnabled(self._current_index < total - 1)

    def _update_speed_display(self) -> None:
        """更新速度显示"""
        speed = self.SPEED_OPTIONS[self._speed_index]
        if speed == int(speed):
            self._speed_label.setText(f"{int(speed)}x")
        else:
            self._speed_label.setText(f"{speed}x")

        self._btn_speed_down.setEnabled(self._speed_index > 0)
        self._btn_speed_up.setEnabled(self._speed_index < len(self.SPEED_OPTIONS) - 1)

    def _update_count_display(self) -> None:
        """更新截图计数"""
        total = len(self._valid_screenshots)
        all_total = len(self._screenshots)
        if total == all_total:
            self._count_label.setText(f"📸 {total} 张截图")
        else:
            self._count_label.setText(f"📸 {total} / {all_total} 张可播放")

    # === 播放控制 ===

    def _toggle_play(self) -> None:
        """切换播放/暂停"""
        if self._is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        """开始播放"""
        if not self._valid_screenshots:
            return

        # 如果已到末尾，从头开始
        if self._current_index >= len(self._valid_screenshots) - 1:
            self._current_index = 0
            self._load_current_frame()

        self._is_playing = True
        self._btn_play.setText("⏸")
        self._btn_play.setToolTip("暂停 (空格)")
        interval = self._get_play_interval()
        self._play_timer.start(interval)

    def _pause_playback(self) -> None:
        """暂停播放"""
        self._is_playing = False
        self._btn_play.setText("▶")
        self._btn_play.setToolTip("播放 (空格)")
        self._play_timer.stop()

    def _stop_playback(self) -> None:
        """停止播放并回到开头"""
        self._pause_playback()
        self._current_index = 0
        self._load_current_frame()

    def _on_play_tick(self) -> None:
        """播放定时器回调"""
        if self._current_index < len(self._valid_screenshots) - 1:
            self._current_index += 1
            self._load_current_frame()
        else:
            # 播放完毕，暂停
            self._pause_playback()

    def _show_prev(self) -> None:
        """显示上一张"""
        if self._current_index > 0:
            self._current_index -= 1
            self._load_current_frame()

    def _show_next(self) -> None:
        """显示下一张"""
        if self._current_index < len(self._valid_screenshots) - 1:
            self._current_index += 1
            self._load_current_frame()

    def _speed_up(self) -> None:
        """加速"""
        if self._speed_index < len(self.SPEED_OPTIONS) - 1:
            self._speed_index += 1
            self._update_speed_display()
            if self._is_playing:
                self._play_timer.setInterval(self._get_play_interval())

    def _speed_down(self) -> None:
        """减速"""
        if self._speed_index > 0:
            self._speed_index -= 1
            self._update_speed_display()
            if self._is_playing:
                self._play_timer.setInterval(self._get_play_interval())

    def _on_slider_changed(self, value: int) -> None:
        """时间轴滑块变化"""
        if 0 <= value < len(self._valid_screenshots):
            self._current_index = value
            self._load_current_frame()

    def _on_close(self) -> None:
        """关闭对话框"""
        self._pause_playback()
        self._pixmap_cache.clear()
        self.accept()

    def reject(self) -> None:
        """ESC关闭"""
        self._pause_playback()
        self._pixmap_cache.clear()
        super().reject()

    # === 键盘控制 ===

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """键盘快捷键"""
        key = event.key()
        if key == Qt.Key_Space:
            self._toggle_play()
        elif key == Qt.Key_Left:
            self._show_prev()
        elif key == Qt.Key_Right:
            self._show_next()
        elif key == Qt.Key_Up:
            self._speed_up()
        elif key == Qt.Key_Down:
            self._speed_down()
        elif key == Qt.Key_Home:
            self._current_index = 0
            self._load_current_frame()
        elif key == Qt.Key_End:
            self._current_index = len(self._valid_screenshots) - 1
            self._load_current_frame()
        elif key == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    # === 窗口事件 ===

    def resizeEvent(self, event: QResizeEvent) -> None:
        """窗口大小变化时重新加载当前帧"""
        super().resizeEvent(event)
        # 延迟重新加载，避免频繁刷新
        if hasattr(self, '_resize_timer'):
            self._resize_timer.stop()
        else:
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._load_current_frame)
        self._resize_timer.start(200)

    # === 主题 ===

    def set_theme(self, is_dark: bool) -> None:
        """设置深色/浅色主题"""
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        colors = self._colors

        # 图片区域背景
        img_bg = "#111827" if is_dark else "#F3F4F6"
        self._image_label.setStyleSheet(f"background-color: {img_bg};")

        # 控制栏样式
        toolbar_bg = colors['bg_card']
        toolbar_border = colors['border']
        text_color = colors['text_primary']
        text_secondary = colors['text_secondary']

        control_qss = f"""
            QFrame#toolbar {{
                background-color: {toolbar_bg};
                border-top: 1px solid {toolbar_border};
            }}
            QLabel {{
                color: {text_color};
            }}
            QLabel#section_desc {{
                color: {text_secondary};
            }}
            QLabel#metric_title {{
                color: {text_color};
            }}
            QSlider#timeline_slider::groove:horizontal {{
                background: {toolbar_border};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider#timeline_slider::handle:horizontal {{
                background: {colors['primary']};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider#timeline_slider::sub-page:horizontal {{
                background: {colors['primary']};
                border-radius: 3px;
            }}
            QPushButton#btn_primary {{
                background-color: {colors['primary']};
                color: white;
                border: none;
                border-radius: 22px;
                font-size: 18px;
            }}
            QPushButton#btn_primary:hover {{
                background-color: {colors['primary_hover']};
            }}
            QPushButton#btn_outline {{
                background-color: transparent;
                color: {text_color};
                border: 1px solid {toolbar_border};
                border-radius: 18px;
                font-size: 14px;
            }}
            QPushButton#btn_outline:hover {{
                background-color: {toolbar_border};
            }}
            QPushButton#btn_outline:disabled {{
                color: {text_secondary};
                border-color: {toolbar_border};
            }}
        """
        self.setStyleSheet(control_qss)

