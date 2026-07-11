"""时间轴页面 - 甘特图样式行为流 + 语义化配色"""

from dataclasses import dataclass, field

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QToolTip, QMenu, QMessageBox
)
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QPen

from database.db_manager import DatabaseManager
from gui.themes import get_colors, EmptyStateWidget, apply_card_shadow, AnimatedCard
from gui.pages.categories_page import get_app_category
from utils.async_loader import DataLoadWorker
from datetime import datetime

# 语义化配色
CATEGORY_COLORS = {
    "productivity": "#3B82F6",   # 生产力工具 - 蓝色
    "browser": "#10B981",        # 浏览器 - 绿色
    "social": "#F59E0B",         # 社交/娱乐 - 橙色
    "idle": "#9CA3AF",           # 系统空闲 - 灰色
    "other": "#8B5CF6",          # 其他 - 紫色
}


@dataclass
class TimelineBlock:
    """时间轴色块数据"""
    app_name: str
    window_title: str
    start_hour: float
    duration_hours: float
    category: str
    record_id: int = -1
    color: str = ""
    tags: list = field(default_factory=list)

    def __post_init__(self):
        if not self.color:
            self.color = CATEGORY_COLORS.get(self.category, CATEGORY_COLORS["other"])


class TimelineWidget(QWidget):
    """甘特图时间轴控件"""

    # 右键菜单操作信号
    mark_sensitive = pyqtSignal(str)   # 标记敏感应用
    set_category = pyqtSignal(str, str)  # 设置分类(应用名, 分类key)
    block_split = pyqtSignal(int, float)   # 拆分色块(record_id, split_offset_hours)
    block_merge = pyqtSignal(int, int)     # 合并色块(record_id1, record_id2)

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.blocks = []
        self.idle_blocks = []  # 空闲时段色块
        self._is_dark = False
        self._colors = get_colors(False)
        self.hovered_block = None
        self.setMouseTracking(True)
        self.setMinimumHeight(500)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_blocks(self, blocks: list, is_dark: bool = False, idle_blocks: list = None) -> None:
        """设置时间轴色块数据"""
        self.blocks = blocks
        self.idle_blocks = idle_blocks or []
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = self._colors

        margin_left = 55
        margin_top = 30
        margin_right = 20
        row_height = 36
        row_gap = 4
        hour_width = (self.width() - margin_left - margin_right) / 24

        # 绘制时间刻度
        self._draw_time_scale(painter, colors, margin_left, margin_top, hour_width)

        # 绘制时间轴色块
        total_height = self._draw_blocks(painter, margin_left, margin_top, row_height, row_gap, hour_width)
        self.setMinimumHeight(max(total_height, 500))

        # 绘制空闲时段
        self._draw_idle_blocks(painter, margin_left, margin_top, total_height, hour_width)

        # 绘制当前时间指示线
        self._draw_current_time_line(painter, colors, margin_left, margin_top, hour_width)

        painter.end()

    def _draw_time_scale(self, painter: QPainter, colors: dict,
                         margin_left: int, margin_top: int, hour_width: float) -> None:
        """绘制时间刻度和垂直网格线"""
        font = QFont("Consolas", 9)
        painter.setFont(font)
        painter.setPen(QColor(colors["text_muted"]))
        for h in range(0, 25, 2):
            x = margin_left + h * hour_width
            painter.drawText(int(x - 12), 18, f"{h:02d}:00")
            pen = QPen(QColor(colors["border"]))
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(int(x), margin_top, int(x), self.height())

    def _draw_blocks(self, painter: QPainter, margin_left: int, margin_top: int,
                     row_height: int, row_gap: int, hour_width: float) -> int:
        """绘制时间轴色块，返回总高度"""
        current_y = margin_top
        for block in self.blocks:
            x = margin_left + block.start_hour * hour_width
            w = max(block.duration_hours * hour_width, 4)
            y = current_y
            h = row_height

            # 色块
            color = QColor(block.color)
            color.setAlpha(180)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(w), int(h), 4, 4)

            # 色块内文字
            if w > 60:
                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(QFont("Microsoft YaHei", 9))
                text = block.app_name
                if w > 150 and block.window_title:
                    text = f"{block.app_name} - {block.window_title[:20]}"
                painter.drawText(int(x + 8), int(y + h // 2 + 4), text)

            # 活动标签指示器（右上角彩色圆点）
            if block.tags:
                tag_size = 8
                tag_gap = 3
                tag_start_x = int(x + w - tag_size - 4)
                tag_y = int(y + 4)
                for ti, tag_info in enumerate(block.tags[:4]):
                    tx = tag_start_x - ti * (tag_size + tag_gap)
                    if tx < int(x) + 4:
                        break
                    tag_color = QColor(tag_info.get("color", self._colors["primary"]))
                    painter.setBrush(QBrush(tag_color))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(tx, tag_y, tag_size, tag_size)

            current_y += row_height + row_gap

        return margin_top + len(self.blocks) * (row_height + row_gap) + 20

    def _draw_idle_blocks(self, painter: QPainter, margin_left: int, margin_top: int,
                          total_height: int, hour_width: float) -> None:
        """绘制空闲时段（半透明斜线纹理灰色块）"""
        for idle_block in self.idle_blocks:
            ix = margin_left + idle_block.start_hour * hour_width
            iw = max(idle_block.duration_hours * hour_width, 4)
            iy = margin_top
            ih = max(total_height - margin_top - 20, 100)

            # 半透明灰色背景
            idle_color = QColor(CATEGORY_COLORS["idle"])
            idle_color.setAlpha(30)
            painter.setBrush(QBrush(idle_color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(ix), int(iy), int(iw), int(ih))

            # 斜线纹理
            stripe_color = QColor(CATEGORY_COLORS["idle"])
            stripe_color.setAlpha(60)
            stripe_pen = QPen(stripe_color)
            stripe_pen.setStyle(Qt.DiagLinePattern)
            stripe_pen.setWidth(1)
            painter.setPen(stripe_pen)
            step = 8
            for sx in range(int(ix), int(ix + iw), step):
                painter.drawLine(sx, int(iy), sx + int(ih * 0.3), int(iy + min(ih, iw - (sx - int(ix)))))
                painter.drawLine(sx, int(iy), sx + 20, int(iy) + 20)

            # 空闲标签
            if iw > 30:
                painter.setPen(QColor(CATEGORY_COLORS["idle"]))
                painter.setFont(QFont("Microsoft YaHei", 8))
                idle_min = int(idle_block.duration_hours * 60)
                painter.drawText(int(ix + 4), int(iy + 14), f"空闲 {idle_min}m")

    def _draw_current_time_line(self, painter: QPainter, colors: dict,
                                margin_left: int, margin_top: int, hour_width: float) -> None:
        """绘制当前时间指示线（红色虚线）"""
        now = datetime.now()
        current_hour = now.hour + now.minute / 60
        if 0 <= current_hour <= 24:
            x_now = margin_left + current_hour * hour_width
            pen = QPen(QColor(colors["danger"]))
            pen.setStyle(Qt.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(int(x_now), margin_top, int(x_now), self.height())
            painter.setPen(QColor(colors["danger"]))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(int(x_now - 20), margin_top - 5, 40, 14,
                           Qt.AlignCenter, f"{now.hour:02d}:{now.minute:02d}")

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动事件重写"""
        margin_left = 55
        margin_top = 30
        margin_right = 20
        row_height = 36
        row_gap = 4
        hour_width = (self.width() - margin_left - margin_right) / 24

        mx, my = event.x(), event.y()
        found = None
        current_y = margin_top
        for block in self.blocks:
            x = margin_left + block.start_hour * hour_width
            w = max(block.duration_hours * hour_width, 4)
            y = current_y
            h = row_height

            if x <= mx <= x + w and y <= my <= y + h:
                found = block
                break
            current_y += row_height + row_gap

        if found:
            duration_min = int(found.duration_hours * 60)
            tooltip = f"<b>{found.app_name}</b><br>窗口: {found.window_title}<br>时长: {duration_min}分钟<br>分类: {found.category}"
            # 添加标签信息
            if found.tags:
                tag_texts = []
                for t in found.tags:
                    tag_texts.append(f"<span style='color:{t.get('color',self._colors['primary'])}'>●</span> {t.get('tag','')}")
                tooltip += f"<br>标签: {' '.join(tag_texts)}"
            QToolTip.showText(event.globalPos(), tooltip)
        else:
            QToolTip.hideText()

    def _get_block_at(self, x: int, y: int) -> object:
        """获取指定坐标处的色块"""
        margin_left = 55
        margin_top = 30
        margin_right = 20
        row_height = 36
        row_gap = 4
        hour_width = (self.width() - margin_left - margin_right) / 24

        current_y = margin_top
        for block in self.blocks:
            bx = margin_left + block.start_hour * hour_width
            bw = max(block.duration_hours * hour_width, 4)
            by = current_y
            bh = row_height

            if bx <= x <= bx + bw and by <= y <= by + bh:
                return block
            current_y += row_height + row_gap
        return None

    def _show_context_menu(self, pos: QPoint) -> None:
        """右键菜单 - 快速标记分类/敏感/拆分/合并"""
        block = self._get_block_at(pos.x(), pos.y())
        if not block:
            return

        menu = QMenu(self)
        app_name = block.app_name

        # 标记/取消敏感
        sensitive_action = menu.addAction("🔒 标记为敏感应用")
        sensitive_action.triggered.connect(lambda: self.mark_sensitive.emit(app_name))

        menu.addSeparator()

        # 分类子菜单
        category_menu = menu.addMenu("🏷 设置分类")
        category_map = {
            "生产力工具": "productivity",
            "浏览器": "browser",
            "社交/娱乐": "social",
            "系统/空闲": "idle",
            "其他": "other",
        }
        for cat_name, cat_key in category_map.items():
            action = category_menu.addAction(cat_name)
            action.triggered.connect(
                lambda checked, a=app_name, k=cat_key: self.set_category.emit(a, k)
            )

        menu.addSeparator()

        # 拆分色块（仅时长>2分钟的记录可拆分，且record_id有效）
        if block.record_id > 0 and block.duration_hours * 60 >= 2:
            split_action = menu.addAction("✂ 拆分此段")
            split_action.triggered.connect(
                lambda: self._show_split_dialog(block)
            )

        # 合并色块（查找相邻同应用色块）
        merge_target = self._find_merge_target(block)
        if merge_target and block.record_id > 0 and merge_target.record_id > 0:
            merge_action = menu.addAction("🔗 与下一段合并")
            merge_action.triggered.connect(
                lambda: self.block_merge.emit(block.record_id, merge_target.record_id)
            )

        menu.exec_(self.mapToGlobal(pos))

    def _find_merge_target(self, block: object) -> object:
        """查找可合并的相邻同应用色块"""
        block_end = block.start_hour + block.duration_hours
        for other in self.blocks:
            if other is block:
                continue
            # 检查是否相邻（时间连续）且同应用
            if (other.app_name == block.app_name and
                abs(other.start_hour - block_end) < 0.02):  # 约1分钟容差
                return other
        return None

    def _show_split_dialog(self, block: object) -> None:
        """显示拆分对话框"""
        from PyQt5.QtWidgets import QSlider, QDialog, QVBoxLayout, QLabel, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("拆分时间轴段")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)

        # 信息标签
        duration_min = block.duration_hours * 60
        start_h = int(block.start_hour)
        start_m = int((block.start_hour - start_h) * 60)
        end_hour = block.start_hour + block.duration_hours
        end_h = int(end_hour)
        end_m = int((end_hour - end_h) * 60)

        info_label = QLabel(
            f"<b>{block.app_name}</b><br>"
            f"时间段: {start_h:02d}:{start_m:02d} → {end_h:02d}:{end_m:02d}<br>"
            f"时长: {duration_min:.0f} 分钟"
        )
        layout.addWidget(info_label)

        # 滑块选择拆分点
        slider_label = QLabel("拖动滑块选择拆分位置:")
        layout.addWidget(slider_label)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(10)  # 最少10%位置
        slider.setMaximum(90)  # 最多90%位置
        slider.setValue(50)
        layout.addWidget(slider)

        # 拆分点时间显示
        split_time_label = QLabel()
        layout.addWidget(split_time_label)

        def update_split_label(val: float) -> None:
            """更新拆分标签显示"""
            pct = val / 100.0
            split_hour = block.start_hour + block.duration_hours * pct
            sh = int(split_hour)
            sm = int((split_hour - sh) * 60)
            front_min = block.duration_hours * pct * 60
            back_min = block.duration_hours * (1 - pct) * 60
            split_time_label.setText(
                f"拆分点: {sh:02d}:{sm:02d}  |  "
                f"前段: {front_min:.0f}分钟  |  后段: {back_min:.0f}分钟"
            )

        slider.valueChanged.connect(update_split_label)
        update_split_label(50)

        # 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec_() == QDialog.Accepted:
            pct = slider.value() / 100.0
            split_offset_hours = block.duration_hours * pct
            self.block_split.emit(block.record_id, split_offset_hours)


class TimelinePage(QWidget):
    """时间轴页面"""

    def __init__(self, db_manager: DatabaseManager, parent: QWidget=None) -> None:
        super().__init__(parent)
        self.db = db_manager
        self._is_dark = False
        self._loader = None  # 异步加载器
        self._setup_ui()

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 20)

        # 标题
        title = QLabel("时间轴")
        title.setObjectName("page_title")
        main_layout.addWidget(title)

        # 语义化配色图例
        legend_card = AnimatedCard()
        legend_card.setObjectName("card")
        apply_card_shadow(legend_card)
        legend_layout = QHBoxLayout(legend_card)
        legend_layout.setSpacing(20)

        legends = [
            ("■ 生产力工具", CATEGORY_COLORS["productivity"]),
            ("■ 浏览器/资讯", CATEGORY_COLORS["browser"]),
            ("■ 社交/娱乐", CATEGORY_COLORS["social"]),
            ("■ 系统空闲", CATEGORY_COLORS["idle"]),
            ("■ 其他", CATEGORY_COLORS["other"]),
        ]
        for text, color in legends:
            label = QLabel(text)
            label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            legend_layout.addWidget(label)
        legend_layout.addStretch()

        # 标签图例
        tag_legend = QLabel("● 活动标签")
        tag_legend.setStyleSheet(f"color: {self._colors['primary']}; font-size: 12px; font-weight: bold;")
        self._tag_legend = tag_legend
        legend_layout.addWidget(tag_legend)
        main_layout.addWidget(legend_card)

        # 时间轴控件
        timeline_card = AnimatedCard()
        timeline_card.setObjectName("card")
        apply_card_shadow(timeline_card)
        timeline_layout = QVBoxLayout(timeline_card)

        self.timeline_widget = TimelineWidget()
        timeline_layout.addWidget(self.timeline_widget)

        # 连接右键菜单信号
        self.timeline_widget.mark_sensitive.connect(self._on_mark_sensitive)
        self.timeline_widget.set_category.connect(self._on_set_category)
        self.timeline_widget.block_split.connect(self._on_split_block)
        self.timeline_widget.block_merge.connect(self._on_merge_block)

        # 空数据状态
        self.empty_state = EmptyStateWidget(
            icon="🕐", title="还没有时间轴数据",
            description="开始记录后，这里将展示您的应用使用时间线"
        )
        self.empty_state.setFixedHeight(300)
        self.empty_state.hide()
        timeline_layout.addWidget(self.empty_state)

        main_layout.addWidget(timeline_card)

        main_layout.addStretch()
        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def refresh(self, date: str = None, start_date: str = None, is_range: bool = False) -> None:
        """异步刷新时间轴数据"""
        if date is None:
            date = QDate.currentDate().toString("yyyy-MM-dd")

        # 取消上一次加载
        if self._loader and self._loader.isRunning():
            self._loader.cancel()
            self._loader.wait(1000)

        # 异步加载数据
        self._loader = DataLoadWorker(
            lambda: self.db.get_timeline_data(date, limit=200),
            parent=self
        )
        self._loader.result_ready.connect(lambda data: self._on_data_loaded(data, date))
        self._loader.start()

    def _on_data_loaded(self, rows: list, date: str) -> None:
        """数据加载完成，构建时间轴色块"""
        blocks = []
        for row in rows:
            app_name = row.get("app_name", "Unknown")
            window_title = row.get("window_title", "") or ""
            start_time = row.get("start_time", "")
            duration = row.get("duration_seconds", 0) or 0
            record_id = row.get("id", -1) or -1
            if duration < 1:
                continue

            # 解析开始时间到小时
            try:
                parts = start_time.split(" ")
                time_part = parts[-1] if len(parts) > 1 else parts[0]
                h, m, s = time_part.split(":")
                start_hour = int(h) + int(m) / 60 + int(s.split(".")[0]) / 3600
            except (ValueError, IndexError):
                start_hour = 0

            duration_hours = duration / 3600
            category = get_app_category(app_name)
            blocks.append(TimelineBlock(
                app_name=app_name,
                window_title=window_title,
                start_hour=start_hour,
                duration_hours=duration_hours,
                category=category,
                record_id=record_id
            ))

        # 脱敏处理
        blocks = self._mask_sensitive_blocks(blocks)

        # 加载活动标签并匹配到色块
        self._attach_tags_to_blocks(blocks, date)

        # 加载空闲时段
        idle_blocks = self._build_idle_blocks(date)

        # 显示/隐藏空状态
        if blocks:
            self.timeline_widget.show()
            self.empty_state.hide()
            self.timeline_widget.set_blocks(blocks, self._is_dark, idle_blocks)
        else:
            self.timeline_widget.hide()
            self.empty_state.show()
            self.empty_state.set_theme(self._is_dark)

    def _mask_sensitive_blocks(self, blocks: list) -> list:
        """将敏感应用的时间轴色块脱敏"""
        sensitive_apps = self.db.get_sensitive_apps()
        for block in blocks:
            if block.app_name in sensitive_apps:
                block.app_name = "敏感应用"
                block.window_title = "***"
                block.category = "other"
                block.color = CATEGORY_COLORS["other"]
        return blocks

    def _attach_tags_to_blocks(self, blocks: list, date: str) -> None:
        """将活动标签匹配到对应的时间轴色块"""
        tags = self.db.get_activity_tags(date)
        if not tags:
            return

        for block in blocks:
            block_end_hour = block.start_hour + block.duration_hours
            for tag in tags:
                # 解析标签时间范围
                tag_start = tag.get("start_time", "")
                tag_end = tag.get("end_time", "")
                if not tag_start or not tag_end:
                    continue
                try:
                    parts = tag_start.split(":")
                    tag_start_hour = int(parts[0]) + int(parts[1]) / 60
                    parts = tag_end.split(":")
                    tag_end_hour = int(parts[0]) + int(parts[1]) / 60
                except (ValueError, AttributeError):
                    continue

                # 检查时间重叠
                if tag_start_hour < block_end_hour and tag_end_hour > block.start_hour:
                    block.tags.append({
                        "tag": tag.get("tag", ""),
                        "note": tag.get("note", ""),
                        "color": tag.get("color", self._colors["primary"]),
                        "start_time": tag_start,
                        "end_time": tag_end,
                    })

    def _build_idle_blocks(self, date: str) -> list:
        """构建空闲时段色块列表"""
        idle_periods = self.db.get_idle_periods(date, min_gap_minutes=10)
        idle_blocks = []
        for p in idle_periods:
            idle_blocks.append(TimelineBlock(
                app_name="空闲",
                window_title="",
                start_hour=p.get("start_hour", 0),
                duration_hours=p.get("duration_hours", 0),
                category="idle"
            ))
        return idle_blocks

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        c = get_colors(is_dark)
        self._colors = c
        self.timeline_widget._is_dark = is_dark
        self.timeline_widget._colors = c
        self.timeline_widget.update()
        # 更新标签图例颜色
        if hasattr(self, '_tag_legend'):
            self._tag_legend.setStyleSheet(f"color: {c['primary']}; font-size: 12px; font-weight: bold;")

    def _on_mark_sensitive(self, app_name: str) -> None:
        """标记/取消敏感应用"""
        sensitive_apps = self.db.get_sensitive_apps()
        if app_name in sensitive_apps:
            self.db.remove_sensitive_app(app_name)
            QMessageBox.information(self, "提示", f"已取消 \"{app_name}\" 的敏感标记")
        else:
            self.db.add_sensitive_app(app_name)
            QMessageBox.information(self, "提示", f"已将 \"{app_name}\" 标记为敏感应用")
        # 刷新时间轴
        self.refresh()

    def _on_set_category(self, app_name: str, category_key: str) -> None:
        """设置应用分类"""
        self.db.set_app_category(app_name, category_key)
        cat_names = {
            "productivity": "生产力工具",
            "browser": "浏览器",
            "social": "社交/娱乐",
            "idle": "系统空闲",
            "other": "其他",
        }
        QMessageBox.information(self, "提示", f"已将 \"{app_name}\" 分类为 {cat_names.get(category_key, category_key)}")
        # 刷新时间轴
        self.refresh()

    def start_live_update(self) -> None:
        """启动实时更新（每分钟刷新当前时间线）"""
        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(lambda: self.timeline_widget.update())
        self._live_timer.start(60000)  # 每60秒刷新

    def stop_live_update(self) -> None:
        """停止实时更新"""
        if hasattr(self, '_live_timer') and self._live_timer:
            self._live_timer.stop()

    def _on_split_block(self, record_id: int, split_offset_hours: float) -> None:
        """处理拆分色块操作"""
        split_seconds = split_offset_hours * 3600
        new_id = self.db.split_app_usage(record_id, split_seconds)
        if new_id > 0:
            QMessageBox.information(self, "拆分成功", "已将此段时间轴拆分为两段")
            self.refresh()
        else:
            QMessageBox.warning(self, "拆分失败", "无法拆分此段，请检查拆分点是否在有效范围内")

    def _on_merge_block(self, record_id1: int, record_id2: int) -> None:
        """处理合并色块操作"""
        success = self.db.merge_app_usage(record_id1, record_id2)
        if success:
            QMessageBox.information(self, "合并成功", "已将相邻两段时间轴合并为一段")
            self.refresh()
        else:
            QMessageBox.warning(self, "合并失败", "无法合并，仅支持相邻的同类应用记录")