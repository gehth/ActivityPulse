"""主窗口 - 侧边栏导航 + 多页面切换 + 主题系统"""

import logging
from typing import Callable

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStackedWidget, QFrame,
    QSystemTrayIcon,
    QMessageBox,
    QGraphicsOpacityEffect, QShortcut
)
from PyQt5.QtCore import Qt, QTimer, QDate, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QPoint, QObject
from PyQt5.QtGui import QKeySequence

from database.db_manager import DatabaseManager
from monitors.app_monitor import AppMonitor
from monitors.input_monitor import InputMonitor
from monitors.screen_monitor import ScreenMonitor
from gui.themes import get_theme_qss, get_colors
from gui.components.toolbar_builder import create_toolbar
from gui.components.tray_manager import TrayManager
from gui.components.check_manager import CheckManager
from gui.components.export_manager import ExportManager
from gui.sidebar import Sidebar
from gui.pages.dashboard_page import DashboardPage
from gui.pages.timeline_page import TimelinePage
from gui.pages.insights_page import InsightsPage
from gui.pages.categories_page import CategoriesPage
from gui.pages.screenshots_page import ScreenshotsPage
from gui.pages.welcome_page import WelcomePage
from gui.settings_dialog import SettingsDialog
from gui.about_dialog import AboutDialog
from gui.sedentary_dialog import SedentaryDialog
from gui.search_dialog import SearchDialog
from gui.pomodoro_widget import PomodoroWidget
from gui.activity_tag_dialog import ActivityTagDialog
from utils.global_hotkey import GlobalHotkeyManager, DEFAULT_HOTKEY, DEFAULT_HOTKEYS
from gui.anomaly_alert_dialog import AnomalyAlertDialog
from gui.screen_playback import ScreenPlaybackDialog

APP_VERSION = "1.0"
APP_NAME = "行为记录"


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        # 初始化数据库
        self.db = DatabaseManager()

        # 初始化监控器
        self._init_monitors()

        # 状态
        self.is_monitoring = False
        self.privacy_mode = False
        self.current_theme = "light"
        self._time_range_mode = "今日"  # 当前时间范围模式

        # 构建UI
        self._setup_ui()

        # 初始化管理器
        self._init_managers()

        # 初始化后续设置
        self._init_post_setup()

    def _init_monitors(self) -> None:
        """从配置读取参数并初始化监控器"""
        app_interval = float(self.db.get_config("app_interval", "5"))
        input_interval = float(self.db.get_config("input_interval", "2"))
        screenshot_interval = float(self.db.get_config("screenshot_interval", "60"))
        screenshot_enabled = self.db.get_config("screenshot_enabled", "1") == "1"

        self.app_monitor = AppMonitor(self.db, interval=app_interval)
        self.input_monitor = InputMonitor(self.db, save_interval=input_interval)
        self.screen_monitor = ScreenMonitor(self.db, interval=screenshot_interval)
        self.screenshot_enabled = screenshot_enabled

    def _init_managers(self) -> None:
        """初始化托盘、检测、导出管理器"""
        self._tray_manager = TrayManager(
            main_window=self,
            db=self.db,
            app_monitor=self.app_monitor,
            callbacks={
                "on_show_window": self._show_window,
                "on_toggle_monitor": lambda: self.sidebar._on_toggle_monitor(),
                "on_toggle_privacy": lambda: self.sidebar._on_toggle_privacy(),
                "on_show_about": self._show_about,
                "on_quit": self._quit_app,
            }
        )
        self.tray_icon = self._tray_manager.tray_icon

        self._check_manager = CheckManager(
            db=self.db,
            tray_icon=self.tray_icon,
            app_monitor=self.app_monitor,
            input_monitor=self.input_monitor,
            callbacks={
                "is_monitoring": lambda: self.is_monitoring,
                "show_status": lambda msg: self.statusBar().showMessage(msg),
                "show_sedentary_dialog": self._show_sedentary_dialog,
                "show_anomaly_alerts": self._show_anomaly_alerts,
                "update_anomaly_badge": self._update_anomaly_badge,
                "is_dark": lambda: self._is_dark,
            }
        )

        self._export_manager = ExportManager(
            db=self.db,
            parent=self,
            app_version=APP_VERSION,
            callbacks={
                "get_date_range": self._get_date_range,
                "show_status": lambda msg: self.statusBar().showMessage(msg),
            }
        )

    def _init_post_setup(self) -> None:
        """初始化定时器、快捷键、主题及启动后任务"""
        self._setup_timer()
        self._setup_hotkey()

        # 应用主题
        self._apply_theme()

        # 添加状态栏
        self.statusBar().showMessage(f"{APP_NAME} v{APP_VERSION} 就绪")

        # 检查是否首次启动
        self._check_first_run()

        # 首次启动自动刷新仪表盘
        QTimer.singleShot(500, self._refresh_current_page)

        # 启动时间轴实时刷新（每分钟更新当前时间线）
        self.timeline_page.start_live_update()

        # 根据配置自动开始记录
        auto_monitor = self.db.get_config("auto_monitor", "1") == "1"
        if auto_monitor:
            QTimer.singleShot(1000, self._auto_start_monitoring)

        # Ctrl+F 搜索快捷键
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self._open_search)

        # 根据配置启动时最小化到托盘
        start_minimized = self.db.get_config("start_minimized", "0") == "1"
        if start_minimized:
            QTimer.singleShot(100, self.hide)

        # 启动时自动清理过期数据
        retention_days = int(self.db.get_config("retention_days", "90"))
        if retention_days > 0:
            QTimer.singleShot(2000, lambda: self._auto_cleanup(retention_days))

    def _auto_start_monitoring(self) -> None:
        """自动开始记录"""
        self._start_monitoring()
        self.sidebar.set_monitoring(True)

    def _auto_cleanup(self, retention_days: int) -> None:
        """启动时自动清理过期数据"""
        try:
            stats = self.db.cleanup_old_data(retention_days)
            total = sum(stats.values())
            if total > 0:
                self.statusBar().showMessage(
                    f"已自动清理 {retention_days} 天前的过期数据：{total} 条记录"
                )
        except Exception as e:
            logging.exception("自动清理失败")

    def _setup_ui(self) -> None:
        """初始化UI界面布局和组件"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        self.sidebar.toggle_monitor.connect(self._on_toggle_monitor)
        self.sidebar.toggle_privacy.connect(self._on_toggle_privacy)
        self.sidebar.settings_clicked.connect(self._on_settings)
        self.sidebar.alert_clicked.connect(self._show_anomaly_alerts)
        main_layout.addWidget(self.sidebar)

        # 右侧内容区
        self._right_container = QWidget()
        self._right_container.setObjectName("content_area")
        right_layout = QVBoxLayout(self._right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        main_layout.addWidget(self._right_container)

        # 顶部工具栏
        self._setup_toolbar(right_layout)

        # 隐私模式横幅
        self.privacy_banner = QLabel("🔒 隐私模式已开启，当前操作不会被记录")
        self.privacy_banner.setObjectName("privacy_banner")
        self.privacy_banner.setAlignment(Qt.AlignCenter)
        self.privacy_banner.hide()
        right_layout.addWidget(self.privacy_banner)

        # 页面容器
        right_layout.addWidget(self._create_content_stack(), 1)

        # 监听resize事件以调整遮罩位置
        self._content_stack.installEventFilter(self)

        # 番茄钟浮动组件
        self._pomodoro_widget = PomodoroWidget(self.db, self._right_container)
        self._pomodoro_widget.hide()
        self._pomodoro_visible = False
        self._pomodoro_widget.pomodoro_completed.connect(self._on_pomodoro_completed)

    def _setup_toolbar(self, parent_layout: QVBoxLayout) -> None:
        """创建顶部工具栏"""
        toolbar, tb_widgets = create_toolbar({
            "on_time_range_changed": self._on_time_range_changed,
            "on_refresh": self._refresh_current_page,
            "on_search": self._open_search,
            "on_pomodoro": self._toggle_pomodoro,
            "on_tags": self._open_tags,
            "on_alert": self._show_anomaly_alerts,
            "on_playback": self._open_playback,
            "on_export_csv": self._export_manager.export_csv,
            "on_export_pdf": self._export_manager.export_pdf,
            "on_toggle_theme": self._toggle_theme,
        })
        self.time_combo = tb_widgets.time_combo
        self.date_edit = tb_widgets.date_edit
        self.date_start_label = tb_widgets.date_start_label
        self.date_start_edit = tb_widgets.date_start_edit
        self.date_end_label = tb_widgets.date_end_label
        self.date_end_edit = tb_widgets.date_end_edit
        self._btn_alert = tb_widgets.btn_alert
        self.btn_theme = tb_widgets.btn_theme
        parent_layout.addWidget(toolbar)

    def _create_content_stack(self) -> None:
        """创建页面容器（含隐私遮罩层）"""
        self._content_stack = QFrame()
        self._content_stack.setObjectName("content_stack")
        content_layout = QVBoxLayout(self._content_stack)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.page_stack = QStackedWidget()
        self.dashboard_page = DashboardPage(self.db)
        self.timeline_page = TimelinePage(self.db)
        self.insights_page = InsightsPage(self.db)
        self.categories_page = CategoriesPage(self.db)
        self.screenshots_page = ScreenshotsPage(self.db)

        self.page_stack.addWidget(self.dashboard_page)
        self.page_stack.addWidget(self.timeline_page)
        self.page_stack.addWidget(self.insights_page)
        self.page_stack.addWidget(self.categories_page)
        self.page_stack.addWidget(self.screenshots_page)

        # Top5点击跳转分类管理页
        self.dashboard_page.navigate_to_categories.connect(self._navigate_to_categories)
        # 每日目标达成通知
        self.dashboard_page.goal_card.goal_achieved.connect(self._on_daily_goal_achieved)

        content_layout.addWidget(self.page_stack)

        # 隐私遮罩层
        self.privacy_overlay = QWidget(self._content_stack)
        self.privacy_overlay.setObjectName("privacy_overlay")
        self.privacy_overlay.hide()

        return self._content_stack







    def _setup_timer(self) -> None:
        """设置定时刷新"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_interval = 30000  # 30秒自动刷新

        # 久坐提醒定时器（同时检查应用限制）
        self._sedentary_timer = QTimer(self)
        self._sedentary_timer.timeout.connect(self._check_manager.check_sedentary)
        self._sedentary_timer.timeout.connect(self._check_manager.check_app_limits)
        self._sedentary_timer.start(60000)  # 每分钟检查

        # 自动报告定时器 - 每5分钟检查是否需要发送报告
        self._report_timer = QTimer(self)
        self._report_timer.timeout.connect(self._check_manager.check_auto_report)
        self._report_timer.start(300000)  # 5分钟检查一次

        # 异常行为检测定时器
        self._anomaly_check_timer = QTimer(self)
        self._anomaly_check_timer.timeout.connect(self._check_manager.check_anomaly)
        # 读取检测间隔配置（默认5分钟）
        anomaly_interval = int(self.db.get_config("anomaly_check_interval", "300")) * 1000
        self._anomaly_check_timer.start(anomaly_interval)

    def _setup_hotkey(self) -> None:
        """设置全局快捷键 - 从配置加载多组快捷键"""
        hotkey_str = self.db.get_config("global_hotkey", DEFAULT_HOTKEY)
        self._hotkey_manager = GlobalHotkeyManager(
            callback=self._toggle_window,
            hotkey_str=hotkey_str
        )
        
        # 注册额外快捷键
        for action, info in DEFAULT_HOTKEYS.items():
            if action == "toggle_window":
                continue  # 已在构造函数中注册
            config_key = f"hotkey_{action}"
            saved_hotkey = self.db.get_config(config_key, info["hotkey"])
            if saved_hotkey:  # 空值表示禁用
                callback = self._get_hotkey_callback(action)
                if callback:
                    self._hotkey_manager.register_hotkey(action, saved_hotkey, callback)
        
        self._hotkey_manager.start()
        # 显示当前快捷键
        display = GlobalHotkeyManager.hotkey_to_display(hotkey_str)
        self.statusBar().showMessage(f"{APP_NAME} v{APP_VERSION} 就绪 | 快捷键: {display}")

    def _get_hotkey_callback(self, action: str) -> object:
        """获取快捷键动作对应的回调函数"""
        callbacks = {
            "toggle_pause": self._toggle_pause,
            "toggle_privacy": self._toggle_privacy,
            "toggle_pomodoro": self._toggle_pomodoro,
        }
        return callbacks.get(action)

    def _toggle_pause(self) -> None:
        """暂停/恢复记录快捷键回调"""
        if hasattr(self, '_monitor_paused') and self._monitor_paused:
            # 恢复监控
            self._start_monitoring()
            self.sidebar.set_monitoring(True)
            self._monitor_paused = False
            self.statusBar().showMessage("监控已恢复")
        else:
            # 暂停监控
            if self.is_monitoring:
                self._stop_monitoring()
                self.sidebar.set_monitoring(False)
                self._monitor_paused = True
                self.statusBar().showMessage("⏸ 监控已暂停（快捷键恢复）")

    def _toggle_privacy(self) -> None:
        """隐私模式切换快捷键回调"""
        if hasattr(self, 'privacy_mode') and self.privacy_mode:
            self._on_toggle_privacy(False)
        else:
            self._on_toggle_privacy(True)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """窗口大小改变时更新引导页位置"""
        super().resizeEvent(event)
        if hasattr(self, '_welcome_page') and self._welcome_page and self._welcome_page.isVisible():
            self._welcome_page.setGeometry(self.rect())

    def _check_first_run(self) -> None:
        """检查是否首次启动，如果是则显示引导页"""
        # 检查是否已有数据（有app_usage记录则非首次）
        has_data = self.db.get_config("first_run_done", "0") == "1"
        if has_data:
            return

        # 首次启动 - 显示欢迎引导页
        self._welcome_page = WelcomePage()
        self._welcome_page.start_clicked.connect(self._on_welcome_done)

        # 将引导页覆盖在内容区
        content_area = self.findChild(QWidget, "content_area")
        if content_area:
            # 使用overlay方式
            self._welcome_page.setParent(self)
            self._welcome_page.setGeometry(self.rect())
            self._welcome_page.raise_()
            self._welcome_page.show()

    def _on_welcome_done(self, settings: dict) -> None:
        """引导页完成 - 保存快速设置"""
        # 保存设置
        self.db.save_config("auto_monitor", "1" if settings.get("auto_monitor", True) else "0")
        self.db.save_config("screenshot_enabled", "1" if settings.get("screenshot_enabled", True) else "0")
        self.db.save_config("sedentary_reminder_minutes", str(settings.get("sedentary_reminder_minutes", 60)))

        # 开机自启
        if settings.get("autostart", False):
            from utils.autostart import enable_auto_start
            enable_auto_start()
            self.db.save_config("autostart", "1")
        else:
            self.db.save_config("autostart", "0")

        # 标记首次启动完成
        self.db.save_config("first_run_done", "1")

        # 关闭引导页
        if hasattr(self, '_welcome_page') and self._welcome_page:
            self._welcome_page.hide()
            self._welcome_page.deleteLater()
            self._welcome_page = None

        # 根据设置启动监控
        if settings.get("auto_monitor", True):
            self._start_monitoring()

        self.statusBar().showMessage("设置已保存，欢迎使用行为记录！")

    def _toggle_window(self) -> None:
        """切换主窗口显示/隐藏（全局热键回调）"""
        if self.isVisible():
            self.hide()
        else:
            self._show_window()

    def _on_page_changed(self, index: int) -> None:
        """页面切换 - 带滑动+淡入动画"""
        old_index = self.page_stack.currentIndex()
        direction = 1 if index > old_index else -1  # 右滑或左滑

        self.page_stack.setCurrentIndex(index)

        # 滑动+淡入组合动画
        current_widget = self.page_stack.currentWidget()
        width = self.page_stack.width()

        # 设置透明度效果（仅作用于页面widget，不影响整个窗口）
        opacity_effect = QGraphicsOpacityEffect(current_widget)
        opacity_effect.setOpacity(0.3)
        current_widget.setGraphicsEffect(opacity_effect)
        # 防止GC回收
        current_widget._page_opacity_effect = opacity_effect

        # 起始位置：从左或右滑入
        current_widget.move(direction * width, 0)

        # 位移动画
        self._slide_anim = QPropertyAnimation(current_widget, b"pos")
        self._slide_anim.setDuration(250)
        self._slide_anim.setStartValue(current_widget.pos())
        self._slide_anim.setEndValue(current_widget.pos() - QPoint(direction * width, 0))
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)

        # 透明度动画（仅作用于页面widget）
        self._fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self._fade_animation.setDuration(250)
        self._fade_animation.setStartValue(0.3)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.InOutCubic)

        # 并行执行
        self._anim_group = QParallelAnimationGroup()
        self._anim_group.addAnimation(self._slide_anim)
        self._anim_group.addAnimation(self._fade_animation)
        self._anim_group.start()

        self._refresh_current_page()

    def _navigate_to_categories(self, app_name: str) -> None:
        """从仪表盘Top5跳转到分类管理页"""
        # 切换到分类管理页(index=3)
        self.sidebar._set_active(3)
        self._on_page_changed(3)
        # 高亮对应应用
        self.categories_page.highlight_app(app_name)

    def _on_toggle_monitor(self, monitoring: bool) -> None:
        """切换监控状态"""
        if monitoring:
            self._start_monitoring()
        else:
            self._stop_monitoring()

    def _start_monitoring(self) -> None:
        """启动所有监控器"""
        try:
            self.app_monitor.start()
            self.input_monitor.start()
            if self.screenshot_enabled:
                self.screen_monitor.start()
            self.is_monitoring = True
            self.refresh_timer.start(self.refresh_interval)
            self.statusBar().showMessage("监控已启动")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动监控失败: {e}")

    def _stop_monitoring(self) -> None:
        """停止所有监控器"""
        try:
            self.app_monitor.stop()
            self.input_monitor.stop()
            self.screen_monitor.stop()
            self.is_monitoring = False
            self.refresh_timer.stop()
            self.statusBar().showMessage("监控已停止")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止监控失败: {e}")

    def _on_toggle_privacy(self, enabled: bool) -> None:
        """切换隐私模式 - 实际暂停/恢复监控"""
        self.privacy_mode = enabled
        if enabled:
            # 暂停监控
            if self.is_monitoring:
                self._stop_monitoring()
                self.sidebar.set_monitoring(False)
            self.privacy_banner.show()
            self.privacy_overlay.show()
            self.privacy_overlay.raise_()
            self.statusBar().showMessage("🔒 隐私模式已开启，监控已暂停")
        else:
            self.privacy_banner.hide()
            self.privacy_overlay.hide()
            # 恢复监控
            self._start_monitoring()
            self.sidebar.set_monitoring(True)
            self.statusBar().showMessage("隐私模式已关闭，监控已恢复")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """事件过滤器 - 调整隐私遮罩位置"""
        try:
            if obj is self._content_stack and event.type() == event.Resize:
                self.privacy_overlay.setGeometry(0, 0, obj.width(), obj.height())
        except RuntimeError:
            pass
        return super().eventFilter(obj, event)

    def _on_settings(self) -> None:
        """打开设置"""
        dialog = SettingsDialog(self.db, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.set_theme(self.current_theme == "dark")
        if dialog.exec_() == SettingsDialog.Accepted:
            self.statusBar().showMessage("设置已更新")

    def _open_search(self) -> None:
        """打开搜索对话框"""
        dialog = SearchDialog(self.db, self)
        dialog.set_theme(self.current_theme == "dark")
        dialog.navigate_to_record.connect(self._on_search_navigate)
        dialog.show_and_focus()

    def _on_search_navigate(self, date_str: str, app_name: str) -> None:
        """搜索结果跳转 - 切换到时间轴页并定位到对应日期"""
        # 设置日期
        self.date_edit.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
        self.time_combo.setCurrentText("今日")
        # 切换到时间轴页(index=1)
        self.sidebar._set_active(1)
        self._on_page_changed(1)
        self.statusBar().showMessage(f"已跳转到 {date_str} - {app_name}")

    def _toggle_pomodoro(self) -> None:
        """切换番茄钟面板"""
        if self._pomodoro_visible:
            self._pomodoro_widget.hide()
            self._pomodoro_visible = False
        else:
            # 定位到右上角
            toolbar_height = 50
            x = self._right_container.width() - 290
            y = toolbar_height + 10
            self._pomodoro_widget.move(x, y)
            self._pomodoro_widget.show()
            self._pomodoro_widget.raise_()
            self._pomodoro_visible = True

    def _on_pomodoro_completed(self, count: int) -> None:
        """番茄钟完成回调"""
        self.statusBar().showMessage(f"🍅 番茄钟完成！今日已完成 {count} 个专注时段")

    def _on_daily_goal_achieved(self) -> None:
        """每日目标达成通知"""
        self.statusBar().showMessage("🎉 恭喜！今日专注目标已达成！")
        # 系统托盘通知
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(
                "🎯 目标达成",
                "恭喜！您已完成今日专注目标！",
                QSystemTrayIcon.Information,
                3000
            )
        from PyQt5.QtWidgets import QApplication
        QApplication.beep()

    def _open_tags(self) -> None:
        """打开活动标签管理对话框"""
        _, end_date, _ = self._get_date_range()
        dialog = ActivityTagDialog(self.db, end_date, self._is_dark, self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.tags_changed.connect(self._refresh_current_page)
        dialog.exec_()

    def _show_window(self) -> None:
        """显示主窗口"""
        self.show()
        self.activateWindow()
        self.raise_()



    def _show_about(self) -> None:
        """显示关于对话框"""
        dialog = AboutDialog(self, version=APP_VERSION)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec_()

    def _on_time_range_changed(self, text: str) -> None:
        """时间范围变更"""
        self._time_range_mode = text
        is_custom = text == "自定义"
        if text == "今日":
            self.date_edit.setDate(QDate.currentDate())
            self.date_edit.setEnabled(True)
        elif text == "昨日":
            self.date_edit.setDate(QDate.currentDate().addDays(-1))
            self.date_edit.setEnabled(True)
        elif text == "近7天":
            self.date_edit.setDate(QDate.currentDate())
            self.date_edit.setEnabled(False)
        elif text == "近30天":
            self.date_edit.setDate(QDate.currentDate())
            self.date_edit.setEnabled(False)
        elif is_custom:
            self.date_edit.setEnabled(False)

        # 显示/隐藏自定义日期选择器
        self.date_start_label.setVisible(is_custom)
        self.date_start_edit.setVisible(is_custom)
        self.date_end_label.setVisible(is_custom)
        self.date_end_edit.setVisible(is_custom)
        self.date_edit.setVisible(not is_custom)

        self._refresh_current_page()

    def _get_date_range(self) -> tuple:
        """获取当前日期范围 (start_date, end_date, is_range)"""
        if self._time_range_mode == "自定义":
            start_date = self.date_start_edit.date().toString("yyyy-MM-dd")
            end_date = self.date_end_edit.date().toString("yyyy-MM-dd")
            return start_date, end_date, True
        end_date = self.date_edit.date().toString("yyyy-MM-dd")
        if self._time_range_mode == "近7天":
            start_date = self.date_edit.date().addDays(-6).toString("yyyy-MM-dd")
            return start_date, end_date, True
        elif self._time_range_mode == "近30天":
            start_date = self.date_edit.date().addDays(-29).toString("yyyy-MM-dd")
            return start_date, end_date, True
        else:
            return end_date, end_date, False

    def _refresh_current_page(self) -> None:
        """刷新当前页面"""
        start_date, end_date, is_range = self._get_date_range()
        index = self.page_stack.currentIndex()
        if index == 0:
            self.dashboard_page.refresh(end_date, start_date=start_date, is_range=is_range)
        elif index == 1:
            self.timeline_page.refresh(end_date, start_date=start_date, is_range=is_range)
        elif index == 2:
            self.insights_page.refresh(end_date, start_date=start_date, is_range=is_range)
        elif index == 3:
            self.categories_page.refresh(end_date, start_date=start_date, is_range=is_range)
        elif index == 4:
            # 同步工具栏日期范围到截图页日期选择器
            self.screenshots_page.date_start.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
            self.screenshots_page.date_end.setDate(QDate.fromString(end_date, "yyyy-MM-dd"))
            self.screenshots_page.refresh()

    def _auto_refresh(self) -> None:
        """自动刷新"""
        if self.is_monitoring:
            self._refresh_current_page()

    def _show_sedentary_dialog(self, minutes: int, snooze_callback: Callable) -> None:
        """显示久坐提醒对话框（CheckManager回调）"""
        dialog = SedentaryDialog(minutes, self)
        dialog.snoozed.connect(snooze_callback)
        dialog.show()







    def _show_anomaly_alerts(self) -> None:
        """显示异常告警中心对话框"""
        try:
            dialog = AnomalyAlertDialog(self.db, self)
            dialog.alerts_changed.connect(self._update_anomaly_badge)
            dialog.set_dark_mode(self._is_dark)
            dialog.exec_()
        except Exception as e:
            logging.exception("显示告警对话框失败")

    def _open_playback(self) -> None:
        """打开屏幕回放对话框"""
        try:
            start_date, end_date, _ = self._get_date_range()
            screenshots = self.db.get_screenshots_for_playback(start_date, end_date)
            if not screenshots:
                QMessageBox.information(
                    self, "屏幕回放",
                    f"在 {start_date} 至 {end_date} 范围内没有截图数据，无法回放。\n"
                    "请确保已开启截图监控并选择有数据的日期范围。"
                )
                return
            dialog = ScreenPlaybackDialog(screenshots, self.db, self)
            dialog.set_theme(self._is_dark)
            dialog.exec_()
        except Exception as e:
            logging.exception("打开屏幕回放失败")
            QMessageBox.warning(self, "屏幕回放", f"打开回放失败: {e}")

    def _update_anomaly_badge(self) -> None:
        """更新侧边栏告警badge"""
        try:
            unread = self.db.get_unread_alert_count()
            if hasattr(self, 'sidebar'):
                self.sidebar.update_anomaly_badge(unread)
        except Exception:
            pass

    def _toggle_theme(self) -> None:
        """切换主题"""
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.btn_theme.setText("☀️ 浅色")
        else:
            self.current_theme = "light"
            self.btn_theme.setText("🌙 深色")
        self._apply_theme()

    def _apply_theme(self) -> None:
        """应用主题"""
        qss = get_theme_qss(self.current_theme)
        self.setStyleSheet(qss)
        is_dark = self.current_theme == "dark"
        # 隐私遮罩使用danger色的8%透明度
        c = get_colors(is_dark)
        danger_hex = c['danger'].lstrip('#')
        r, g, b = int(danger_hex[:2], 16), int(danger_hex[2:4], 16), int(danger_hex[4:6], 16)
        self.privacy_overlay.setStyleSheet(
            f"#privacy_overlay {{ background-color: rgba({r}, {g}, {b}, 0.08); }}"
        )
        self.sidebar.set_theme(is_dark)
        self.btn_theme.set_theme(is_dark)
        self.dashboard_page.set_theme(is_dark)
        self.timeline_page.set_theme(is_dark)
        self.insights_page.set_theme(is_dark)
        self.categories_page.set_theme(is_dark)
        self.screenshots_page.set_theme(is_dark)
        self._pomodoro_widget.set_theme(is_dark)

    def _quit_app(self) -> None:
        """退出应用"""
        if self.is_monitoring:
            self._stop_monitoring()
        self._hotkey_manager.stop()
        self.db.close()
        self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event: QCloseEvent) -> None:
        """关闭事件 - 最小化到托盘"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            APP_NAME,
            "程序已最小化到系统托盘，继续后台记录\n双击托盘图标可重新打开",
            QSystemTrayIcon.Information,
            2000
        )