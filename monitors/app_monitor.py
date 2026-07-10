"""应用使用记录模块 - 追踪打开的软件和使用时长"""

import threading
import time
import logging
from datetime import datetime
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

try:
    import pygetwindow as gw
except ImportError:
    gw = None

try:
    import psutil
except ImportError:
    psutil = None


class AppMonitor:
    """监控应用程序使用情况"""

    def __init__(self, db_manager: DatabaseManager, interval: float = 5.0):
        """
        初始化应用监控器

        Args:
            db_manager: 数据库管理器实例
            interval: 检查间隔（秒）
        """
        self.db = db_manager
        self.interval = interval
        self._running = False
        self._thread = None
        self._current_app = None
        self._current_title = None
        self._current_start = None
        self._current_record_id = None

    def _get_active_window(self):
        """获取当前活动窗口信息"""
        try:
            if gw:
                window = gw.getActiveWindow()
                if window:
                    app_name = window.appName if hasattr(window, 'appName') else ""
                    title = window.title if hasattr(window, 'title') else ""
                    # 如果appName为空，尝试从标题推断
                    if not app_name and title:
                        app_name = title.split(" - ")[-1] if " - " in title else title
                    return app_name or "Unknown", title or "Unknown"
            # 备用方案：使用psutil获取前台进程
            if psutil:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name']:
                            return proc.info['name'], ""
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except Exception as e:
            logger.warning(f"获取活动窗口失败: {e}")
        return "Unknown", "Unknown"

    def _on_app_change(self, new_app: str, new_title: str):
        """当活动应用发生变化时处理"""
        now = datetime.now()
        # 关闭旧的应用记录
        if self._current_record_id is not None:
            duration = (now - self._current_start).total_seconds()
            end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            self.db.update_app_usage(self._current_record_id, end_time, duration)

        # 创建新的应用记录
        start_time = now.strftime("%Y-%m-%d %H:%M:%S")
        record_id = self.db.save_app_usage(
            app_name=new_app,
            window_title=new_title,
            start_time=start_time
        )
        self._current_app = new_app
        self._current_title = new_title
        self._current_start = now
        self._current_record_id = record_id

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                app_name, window_title = self._get_active_window()
                if app_name != self._current_app or window_title != self._current_title:
                    self._on_app_change(app_name, window_title)
            except Exception as e:
                logger.error(f"应用监控循环错误: {e}")
            time.sleep(self.interval)

    def start(self) -> None:
        """启动应用监控线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        # 初始化当前应用
        app_name, window_title = self._get_active_window()
        self._on_app_change(app_name, window_title)
        logger.info(f"应用监控已启动，检查间隔: {self.interval}秒")

    def stop(self) -> None:
        """停止应用监控，关闭当前应用记录"""
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        # 关闭当前记录
        if self._current_record_id is not None:
            now = datetime.now()
            duration = (now - self._current_start).total_seconds()
            end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            self.db.update_app_usage(self._current_record_id, end_time, duration)
            self._current_record_id = None
        logger.info("应用监控已停止")

    @property
    def is_running(self) -> bool:
        """监控是否正在运行"""
        return self._running