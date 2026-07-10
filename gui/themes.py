"""主题系统 - 浅色/深色双主题 QSS 样式表"""

from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QPushButton, QFrame
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QColor, QPainter, QBrush, QRadialGradient

# 色彩常量
COLORS = {
    "light": {
        "bg_primary": "#F9FAFB",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#FFFFFF",
        "bg_sidebar_hover": "#F3F4F6",
        "bg_sidebar_active": "#EFF6FF",
        "text_primary": "#111827",
        "text_secondary": "#6B7280",
        "text_muted": "#9CA3AF",
        "border": "#E5E7EB",
        "primary": "#3B82F6",
        "primary_hover": "#2563EB",
        "primary_light": "#DBEAFE",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "danger_light": "#FEE2E2",
        "shadow": "rgba(0,0,0,0.08)",
    },
    "dark": {
        "bg_primary": "#111827",
        "bg_card": "#1F2937",
        "bg_sidebar": "#1F2937",
        "bg_sidebar_hover": "#374151",
        "bg_sidebar_active": "#1E3A5F",
        "text_primary": "#F9FAFB",
        "text_secondary": "#9CA3AF",
        "text_muted": "#6B7280",
        "border": "#374151",
        "primary": "#3B82F6",
        "primary_hover": "#60A5FA",
        "primary_light": "#1E3A5F",
        "success": "#10B981",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "danger_light": "#7F1D1D",
        "shadow": "rgba(0,0,0,0.3)",
    }
}


# ── QSS 样式片段常量 ──────────────────────────────────────────
# 高频重复的CSS属性组合，供各组件setStyleSheet引用
# 用法: widget.setStyleSheet(QSS_STYLES["section_title"].format(c=colors))

QSS_STYLES = {
    # 排版
    "section_title": "font-size: 15px; font-weight: bold; color: {c[text_primary]};",
    "section_desc": "font-size: 12px; color: {c[text_muted]};",
    "metric_title": "font-size: 13px; color: {c[text_secondary]};",
    "metric_value": "font-size: 28px; font-weight: bold; color: {c[text_primary]}; font-family: \"Consolas\", \"Microsoft YaHei\", monospace;",
    "metric_change_up": "font-size: 12px; color: {c[success]}; font-family: \"Consolas\", monospace;",
    "metric_change_down": "font-size: 12px; color: {c[danger]}; font-family: \"Consolas\", monospace;",
    "body_text": "font-size: 13px; color: {c[text_primary]}; line-height: 1.5;",
    "secondary_text": "font-size: 12px; color: {c[text_secondary]};",
    "muted_text": "font-size: 12px; color: {c[text_muted]};",
    "small_text": "font-size: 11px; color: {c[text_muted]};",

    # 边框/圆角
    "card_border": "border: 1px solid {c[border]}; border-radius: 8px;",
    "input_border": "border: 1px solid {c[border]}; border-radius: 6px;",
    "pill_border": "border-radius: 12px;",

    # 按钮
    "btn_outline": "background: transparent; border: 1px solid {c[border]}; color: {c[text_secondary]}; border-radius: 6px; padding: 4px 12px;",
    "btn_outline_hover": "border-color: {c[primary]}; color: {c[primary]}; background-color: {c[primary_light]};",
    "btn_primary_sm": "background-color: {c[primary]}; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;",
    "btn_danger_sm": "background-color: {c[danger]}; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;",

    # 标签/徽章
    "badge": "font-size: 11px; padding: 2px 8px; border-radius: 4px;",
    "badge_primary": "font-size: 11px; padding: 2px 8px; border-radius: 12px; background-color: {c[primary_light]}; color: {c[primary]};",
    "badge_danger": "font-size: 11px; padding: 2px 8px; border-radius: 12px; background-color: {c[danger_light]}; color: {c[danger]};",
    "badge_success": "font-size: 11px; padding: 2px 8px; border-radius: 12px; background-color: {c[primary_light]}; color: {c[success]};",

    # 色块
    "color_dot": "width: 12px; height: 12px; border-radius: 6px;",

    # 分隔
    "divider": "background-color: {c[border]}; max-height: 1px; margin: 8px 0;",
}


def get_theme_qss(theme: str = "light") -> str:
    """获取主题QSS样式表"""
    c = COLORS[theme]
    is_dark = theme == "dark"

    return f"""
    /* ===== 全局样式 ===== */
    QMainWindow {{
        background-color: {c['bg_primary']};
    }}
    QWidget {{
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        color: {c['text_primary']};
    }}

    /* ===== 侧边栏 ===== */
    #sidebar {{
        background-color: {c['bg_sidebar']};
        border-right: 1px solid {c['border']};
        min-width: 220px;
        max-width: 220px;
    }}
    #sidebar_collapsed {{
        background-color: {c['bg_sidebar']};
        border-right: 1px solid {c['border']};
        min-width: 60px;
        max-width: 60px;
    }}

    /* 品牌区 */
    #brand_area {{
        padding: 20px 16px 16px 16px;
        border-bottom: 1px solid {c['border']};
    }}
    #brand_label {{
        font-size: 18px;
        font-weight: bold;
        color: {c['primary']};
    }}
    #brand_label_collapsed {{
        font-size: 14px;
        font-weight: bold;
        color: {c['primary']};
    }}

    /* 导航按钮 */
    #nav_button {{
        text-align: left;
        padding: 12px 16px;
        border: none;
        border-radius: 8px;
        background: transparent;
        color: {c['text_secondary']};
        font-size: 14px;
        margin: 2px 8px;
    }}
    #nav_button:hover {{
        background-color: {c['bg_sidebar_hover']};
        color: {c['text_primary']};
    }}
    #nav_button_active {{
        text-align: left;
        padding: 12px 16px;
        border: none;
        border-radius: 8px;
        background-color: {c['bg_sidebar_active']};
        color: {c['primary']};
        font-size: 14px;
        font-weight: bold;
        margin: 2px 8px;
    }}

    /* 底部操作区 */
    #sidebar_bottom {{
        border-top: 1px solid {c['border']};
        padding: 12px;
    }}

    /* 状态指示灯 */
    #status_label {{
        font-size: 12px;
        padding: 4px 8px;
        border-radius: 4px;
    }}
    #status_recording {{
        background-color: {c['danger_light']};
        color: {c['danger']};
        font-size: 12px;
        padding: 4px 12px;
        border-radius: 12px;
    }}
    #status_paused {{
        background-color: {c['primary_light']};
        color: {c['primary']};
        font-size: 12px;
        padding: 4px 12px;
        border-radius: 12px;
    }}

    /* ===== 右侧内容区 ===== */
    #content_area {{
        background-color: {c['bg_primary']};
    }}

    /* 顶部工具栏 */
    #toolbar {{
        background-color: {c['bg_card']};
        border-bottom: 1px solid {c['border']};
        padding: 12px 20px;
        min-height: 48px;
    }}

    /* ===== 卡片 ===== */
    #card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 20px;
    }}
    #card:hover {{
        border-color: {c['primary']};
    }}
    #metric_card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 16px 20px;
        min-height: 100px;
    }}
    #metric_card:hover {{
        border-color: {c['primary']};
    }}
    #metric_value {{
        font-size: 28px;
        font-weight: bold;
        color: {c['text_primary']};
        font-family: "Consolas", "Microsoft YaHei", monospace;
    }}
    #metric_title {{
        font-size: 13px;
        color: {c['text_secondary']};
    }}
    #metric_change_up {{
        font-size: 12px;
        color: {c['success']};
        font-family: "Consolas", monospace;
    }}
    #metric_change_down {{
        font-size: 12px;
        color: {c['danger']};
        font-family: "Consolas", monospace;
    }}

    /* ===== 按钮 ===== */
    QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
        background-color: {c['primary']};
        color: white;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {c['primary_hover']};
        padding-top: 6px;
    }}
    QPushButton:pressed {{
        padding-top: 9px;
        padding-left: 17px;
    }}

    #btn_outline {{
        background: transparent;
        border: 1px solid {c['border']};
        color: {c['text_secondary']};
    }}
    #btn_outline:hover {{
        border-color: {c['primary']};
        color: {c['primary']};
        background-color: {c['primary_light']};
        padding-top: 6px;
    }}

    #btn_danger {{
        background-color: {c['danger']};
    }}
    #btn_danger:hover {{
        background-color: #DC2626;
        padding-top: 6px;
    }}

    /* ===== 输入框 ===== */
    QComboBox, QSpinBox, QDateEdit {{
        padding: 6px 12px;
        border: 1px solid {c['border']};
        border-radius: 6px;
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        min-height: 28px;
    }}
    QComboBox:hover, QSpinBox:hover, QDateEdit:hover {{
        border-color: {c['primary']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    /* ===== 表格 ===== */
    QTableWidget {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        gridline-color: {c['border']};
        color: {c['text_primary']};
    }}
    QTableWidget::item {{
        padding: 8px;
        border-bottom: 1px solid {c['border']};
    }}
    QTableWidget::item:hover {{
        background-color: {c['bg_sidebar_hover']};
    }}
    QHeaderView::section {{
        background-color: {c['bg_primary']};
        color: {c['text_secondary']};
        padding: 8px;
        border: none;
        border-bottom: 2px solid {c['border']};
        font-weight: bold;
        font-size: 12px;
    }}

    /* ===== 滚动条 ===== */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {c['text_muted']};
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['text_secondary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ===== 选项卡 ===== */
    QTabWidget::pane {{
        border: none;
    }}

    /* ===== 隐私模式遮罩 ===== */
    #privacy_overlay {{
        background-color: rgba(239, 68, 68, 0.05);
        border-top: 3px solid {c['danger']};
    }}
    #privacy_banner {{
        background-color: {c['danger_light']};
        color: {c['danger']};
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 13px;
    }}

    /* ===== 进度条 ===== */
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background-color: {c['bg_sidebar_hover']};
        height: 8px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        border-radius: 4px;
        background-color: {c['primary']};
    }}

    /* ===== 分隔线 ===== */
    #separator {{
        background-color: {c['border']};
        max-height: 1px;
        margin: 8px 16px;
    }}

    /* ===== 页面通用样式 ===== */
    #page_title {{
        font-size: 20px;
        font-weight: bold;
        color: {c['text_primary']};
    }}
    #card_title {{
        font-size: 15px;
        font-weight: bold;
        color: {c['text_primary']};
    }}
    #section_desc {{
        font-size: 12px;
        color: {c['text_muted']};
    }}
    #legend_text {{
        font-size: 12px;
        font-weight: bold;
    }}
    #empty_hint {{
        color: {c['text_muted']};
        font-size: 13px;
        padding: 20px;
    }}

    /* ===== 卡片hover效果 ===== */
    #card:hover {{
        border-color: {c['primary']};
    }}
    #metric_card:hover {{
        border-color: {c['primary']};
    }}

    /* ===== QScrollArea ===== */
    QScrollArea {{
        background: transparent;
        border: none;
    }}

    /* ===== QGroupBox ===== */
    QGroupBox {{
        font-size: 14px;
        font-weight: bold;
        color: {c['text_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px 12px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {c['primary']};
    }}
    """


def get_colors(theme: str = "light") -> dict:
    """获取当前主题的颜色字典"""
    return COLORS.get(theme, COLORS["light"])


def apply_card_shadow(widget: QWidget, is_dark: bool = False, blur: int = 16, offset: int = 2) -> None:
    """为卡片/组件添加投影阴影效果"""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, offset)
    if is_dark:
        shadow.setColor(QColor(0, 0, 0, 60))
    else:
        shadow.setColor(QColor(0, 0, 0, 25))
    widget.setGraphicsEffect(shadow)
    # 关键：将shadow存储为widget的属性，防止Python垃圾回收导致C++对象被删除
    widget._card_shadow = shadow
    return shadow


class SkeletonWidget(QWidget):
    """骨架屏占位组件 - 显示加载中的占位效果"""

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self._is_dark = False
        self._opacity = 0.0
        self._increasing = True

        # 呼吸动画
        from PyQt5.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self.update()

    def _animate(self) -> None:
        """执行动画帧更新"""
        step = 0.02
        if self._increasing:
            self._opacity += step
            if self._opacity >= 0.3:
                self._opacity = 0.3
                self._increasing = False
        else:
            self._opacity -= step
            if self._opacity <= 0.0:
                self._opacity = 0.0
                self._increasing = True
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        from PyQt5.QtGui import QPainter, QColor, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        colors = get_colors("dark" if self._is_dark else "light")
        base_color = QColor(colors["bg_sidebar_hover"])
        highlight = QColor(colors["primary"])
        highlight.setAlphaF(self._opacity)

        # 绘制骨架块
        painter.setBrush(QBrush(base_color))
        painter.setPen(Qt.NoPen)

        # 4个指标卡骨架
        card_w = (self.width() - 80) // 4
        for i in range(4):
            x = 24 + i * (card_w + 16)
            painter.drawRoundedRect(x, 20, card_w, 100, 8, 8)

        # 热力图骨架
        painter.drawRoundedRect(24, 140, self.width() - 48, 160, 8, 8)

        # Top5骨架
        for i in range(5):
            y = 320 + i * 44
            painter.drawRoundedRect(24, y, self.width() - 48, 36, 6, 6)

        # 叠加高亮
        painter.setBrush(QBrush(highlight))
        painter.drawRect(0, 0, self.width(), self.height())

        painter.end()


    def hideEvent(self, event: QHideEvent) -> None:
        """隐藏事件重写"""
        self._timer.stop()
        super().hideEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        """显示事件重写"""
        self._timer.start(50)
        super().showEvent(event)


class HoverButton(QPushButton):
    """按钮hover上浮+阴影加深效果

    使用QGraphicsDropShadowEffect实现hover时阴影加深，
    配合QSS padding-top:6px实现上浮视觉，动画过渡平滑。
    """

    def __init__(self, text: str = "", parent: QWidget=None) -> None:
        super().__init__(text, parent)
        self._is_dark = False
        self._hover_shadow = None
        self._normal_shadow = None
        self._anim = None
        self.setCursor(Qt.PointingHandCursor)

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self._update_shadow(False)

    def _update_shadow(self, hover: bool) -> None:
        """更新阴影效果"""
        shadow = QGraphicsDropShadowEffect(self)
        if hover:
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 4)
            shadow.setColor(QColor(0, 0, 0, 50) if not self._is_dark else QColor(0, 0, 0, 80))
        else:
            shadow.setBlurRadius(10)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 15) if not self._is_dark else QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)
        self._card_shadow = shadow  # 防止GC回收

    def enterEvent(self, event: QEvent) -> None:
        """鼠标进入事件重写"""
        self._update_shadow(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        """鼠标离开事件重写"""
        self._update_shadow(False)
        super().leaveEvent(event)


class RippleOverlay(QWidget):
    """卡片ripple点击反馈效果 - 覆盖在目标widget上的透明层

    点击时在鼠标位置产生扩散的水波纹动画，模拟Material Design ripple。
    """

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self._ripples = []  # [(cx, cy, radius, max_radius, opacity), ...]
        self._is_dark = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark

    def add_ripple(self, x: int, y: int) -> None:
        """在(x,y)位置添加一个ripple"""
        max_radius = max(self.width(), self.height()) * 1.2
        self._ripples.append([x, y, 0.0, max_radius, 0.3])
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self) -> None:
        """动画帧"""
        alive = []
        for r in self._ripples:
            r[2] += r[3] * 0.04  # radius增长
            r[4] -= 0.012  # opacity衰减
            if r[4] > 0:
                alive.append(r)
        self._ripples = alive
        self.update()
        if not alive:
            self._timer.stop()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        if not self._ripples:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        color = QColor(get_colors("dark" if self._is_dark else "light")["primary"])
        for cx, cy, radius, _, opacity in self._ripples:
            color.setAlphaF(max(0, opacity))
            gradient = QRadialGradient(cx, cy, radius)
            gradient.setColorAt(0, color)
            color_fade = QColor(color)
            color_fade.setAlphaF(0)
            gradient.setColorAt(1, color_fade)
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(cx - radius), int(cy - radius),
                                int(radius * 2), int(radius * 2))
        painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """跟随父组件大小"""
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        super().resizeEvent(event)


class AnimatedCard(QFrame):
    """带ripple反馈的动画卡片

    点击时产生ripple水波纹 + 轻微缩放反馈。
    用于替代普通QFrame卡片，提升交互质感。
    """

    def __init__(self, parent: QWidget=None) -> None:
        super().__init__(parent)
        self._ripple = RippleOverlay(self)
        self._is_dark = False
        self._scale_anim = None

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self._ripple.set_theme(is_dark)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """点击时触发ripple + 缩放动画"""
        if event.button() == Qt.LeftButton:
            self._ripple.add_ripple(event.x(), event.y())
            # 缩放反馈：轻微缩小后弹回
            self._scale_anim = QPropertyAnimation(self, b"geometry")
            self._scale_anim.setDuration(150)
            geo = self.geometry()
            # 缩小2px
            shrink = geo.adjusted(1, 1, -1, -1)
            self._scale_anim.setKeyValueAt(0, geo)
            self._scale_anim.setKeyValueAt(0.4, shrink)
            self._scale_anim.setKeyValueAt(1, geo)
            self._scale_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._scale_anim.start()
        super().mousePressEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """ripple层跟随卡片大小"""
        self._ripple.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)


class EmptyStateWidget(QWidget):
    """空数据状态组件 - 无数据时显示引导文案"""

    def __init__(self, icon: str = "📭", title: str = "暂无数据",
                 description: str = "开始使用后，数据将自动出现在这里", parent: QWidget=None) -> None:
        super().__init__(parent)
        self._is_dark = False
        self._icon = icon
        self._title = title
        self._description = description

    def set_theme(self, is_dark: bool) -> None:
        """设置主题样式（明/暗模式）"""
        self._is_dark = is_dark
        self.update()

    def set_content(self, icon: str = None, title: str = None, description: str = None) -> None:
        """设置显示内容"""
        if icon:
            self._icon = icon
        if title:
            self._title = title
        if description:
            self._description = description
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """绘制事件重写"""
        from PyQt5.QtGui import QPainter, QColor, QFont
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        colors = get_colors("dark" if self._is_dark else "light")

        # 图标
        painter.setFont(QFont("Segoe UI Emoji", 48))
        painter.setPen(QColor(colors["text_muted"]))
        icon_rect = self.rect()
        icon_rect.setTop(self.height() // 2 - 80)
        icon_rect.setHeight(60)
        painter.drawText(icon_rect, Qt.AlignCenter, self._icon)

        # 标题
        painter.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        painter.setPen(QColor(colors["text_secondary"]))
        title_rect = self.rect()
        title_rect.setTop(self.height() // 2 - 15)
        title_rect.setHeight(30)
        painter.drawText(title_rect, Qt.AlignCenter, self._title)

        # 描述
        painter.setFont(QFont("Microsoft YaHei", 12))
        painter.setPen(QColor(colors["text_muted"]))
        desc_rect = self.rect()
        desc_rect.setTop(self.height() // 2 + 20)
        desc_rect.setHeight(25)
        painter.drawText(desc_rect, Qt.AlignCenter, self._description)

        painter.end()
