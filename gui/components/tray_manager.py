"""系统托盘管理器 - 托盘图标、菜单、通知"""

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import QTimer, QDate

from gui.components.icon_factory import create_app_icon
from utils.time_utils import format_duration


APP_NAME = "行为记录"
APP_VERSION = "1.0"


class TrayManager:
    """系统托盘管理器

    管理托盘图标、菜单和动态信息更新。
    """

    def __init__(self, main_window, db, app_monitor, callbacks: dict):
        """
        Args:
            main_window: 主窗口实例（用于setWindowIcon等）
            db: DatabaseManager实例
            app_monitor: AppMonitor实例
            callbacks: 回调函数字典，支持以下键：
                - on_show_window: 显示主窗口
                - on_toggle_monitor: 切换监控状态
                - on_toggle_privacy: 切换隐私模式
                - on_show_about: 显示关于对话框
                - on_quit: 退出应用
        """
        self._main_window = main_window
        self._db = db
        self._app_monitor = app_monitor
        self._callbacks = callbacks

        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(main_window)
        self.tray_icon.setToolTip(f"{APP_NAME} v{APP_VERSION}\n快捷键: Ctrl+Shift+H 显示/隐藏")

        # 生成应用图标
        app_icon = create_app_icon()
        self.tray_icon.setIcon(app_icon)
        main_window.setWindowIcon(app_icon)

        # 托盘菜单
        self._tray_menu = QMenu()

        # 今日时长（动态更新）
        self._tray_duration_action = QAction("今日记录: 计算中...", main_window)
        self._tray_duration_action.setEnabled(False)
        self._tray_menu.addAction(self._tray_duration_action)

        # 当前应用（动态更新）
        self._tray_current_app_action = QAction("当前应用: --", main_window)
        self._tray_current_app_action.setEnabled(False)
        self._tray_menu.addAction(self._tray_current_app_action)

        self._tray_menu.addSeparator()

        action_show = QAction("打开主界面", main_window)
        action_show.triggered.connect(callbacks.get("on_show_window"))
        self._tray_menu.addAction(action_show)

        self._tray_menu.addSeparator()

        self.action_toggle = QAction("暂停记录", main_window)
        self.action_toggle.triggered.connect(callbacks.get("on_toggle_monitor"))
        self._tray_menu.addAction(self.action_toggle)

        action_privacy = QAction("隐私模式", main_window)
        action_privacy.triggered.connect(callbacks.get("on_toggle_privacy"))
        self._tray_menu.addAction(action_privacy)

        self._tray_menu.addSeparator()

        action_about = QAction(f"关于 {APP_NAME} v{APP_VERSION}", main_window)
        action_about.triggered.connect(callbacks.get("on_show_about"))
        self._tray_menu.addAction(action_about)

        action_quit = QAction("退出", main_window)
        action_quit.triggered.connect(callbacks.get("on_quit"))
        self._tray_menu.addAction(action_quit)

        self.tray_icon.setContextMenu(self._tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

        # 托盘信息更新定时器
        self._tray_info_timer = QTimer(main_window)
        self._tray_info_timer.timeout.connect(self.update_tray_info)
        self._tray_info_timer.start(10000)  # 每10秒更新

    def _on_tray_activated(self, reason):
        """托盘图标激活（双击打开主窗口）"""
        if reason == QSystemTrayIcon.DoubleClick:
            callback = self._callbacks.get("on_show_window")
            if callback:
                callback()

    def update_tray_info(self):
        """更新托盘菜单中的动态信息"""
        try:
            # 今日记录时长
            today = QDate.currentDate().toString("yyyy-MM-dd")
            total_seconds = self._db.get_day_total_seconds(today)
            duration_str = format_duration(total_seconds, fmt="long")
            self._tray_duration_action.setText(f"今日记录: {duration_str}")

            # 当前活跃应用
            current_app = self._app_monitor._current_app or "--"
            self._tray_current_app_action.setText(f"当前应用: {current_app}")
        except Exception:
            pass