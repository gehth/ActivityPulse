"""键鼠操作记录模块 - 记录键盘输入和鼠标点击/移动"""

import threading
import time
import logging
from datetime import datetime
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

try:
    from pynput import keyboard, mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


class InputMonitor:
    """监控键盘和鼠标操作"""

    def __init__(self, db_manager: DatabaseManager, save_interval: float = 2.0,
                 track_mouse_move: bool = False) -> None:
        """
        初始化键鼠监控器

        Args:
            db_manager: 数据库管理器实例
            save_interval: 保存间隔（秒），避免过于频繁写入数据库
            track_mouse_move: 是否追踪鼠标移动事件（数据量较大）
        """
        self.db = db_manager
        self.save_interval = save_interval
        self.track_mouse_move = track_mouse_move
        self._running = False
        self._keyboard_listener = None
        self._mouse_listener = None
        self._event_buffer = []
        self._buffer_lock = threading.Lock()
        self._save_thread = None
        # 统计计数
        self._key_press_count = 0
        self._mouse_click_count = 0
        self._mouse_move_count = 0
        self._scroll_count = 0

    def _on_key_press(self, key) -> None:
        """键盘按键回调"""
        try:
            if hasattr(key, 'char') and key.char:
                event_detail = f"按键: {key.char}"
            elif hasattr(key, 'name'):
                event_detail = f"特殊键: {key.name}"
            else:
                event_detail = f"按键: {str(key)}"
            self._key_press_count += 1
            self._add_event("keyboard_press", event_detail)
        except Exception:
            pass

    def _on_mouse_click(self, x, y, button, pressed) -> None:
        """鼠标点击回调"""
        if pressed:
            btn_name = str(button).split('.')[-1] if button else "unknown"
            event_detail = f"点击: {btn_name} ({x}, {y})"
            self._mouse_click_count += 1
            self._add_event("mouse_click", event_detail)

    def _on_mouse_move(self, x, y) -> None:
        """鼠标移动回调"""
        if self.track_mouse_move:
            event_detail = f"移动: ({x}, {y})"
            self._mouse_move_count += 1
            self._add_event("mouse_move", event_detail)

    def _on_mouse_scroll(self, x, y, dx, dy) -> None:
        """鼠标滚轮回调"""
        direction = "上" if dy > 0 else "下"
        event_detail = f"滚轮: {direction} ({x}, {y})"
        self._scroll_count += 1
        self._add_event("mouse_scroll", event_detail)

    def _add_event(self, event_type: str, event_detail: str) -> None:
        """添加事件到缓冲区"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        with self._buffer_lock:
            self._event_buffer.append({
                "event_type": event_type,
                "event_detail": event_detail,
                "timestamp": timestamp
            })

    def _save_loop(self) -> None:
        """定期保存事件到数据库"""
        while self._running:
            try:
                time.sleep(self.save_interval)
                self._flush_buffer()
            except Exception as e:
                logger.error(f"键鼠事件保存错误: {e}")

    def _flush_buffer(self) -> None:
        """将缓冲区中的事件批量写入数据库"""
        with self._buffer_lock:
            events = self._event_buffer.copy()
            self._event_buffer.clear()

        if not events:
            return

        try:
            self.db.save_input_events_batch(events)
        except Exception as e:
            logger.warning(f"批量保存键鼠事件失败: {e}")

    def start(self) -> None:
        """启动键鼠监控监听器和保存线程"""
        if not PYNPUT_AVAILABLE:
            logger.warning("pynput库未安装，无法监控键鼠操作")
            return
        if self._running:
            return
        self._running = True

        # 启动键盘监听
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        self._keyboard_listener.daemon = True
        self._keyboard_listener.start()

        # 启动鼠标监听
        mouse_kwargs = {
            "on_click": self._on_mouse_click,
            "on_scroll": self._on_mouse_scroll,
        }
        if self.track_mouse_move:
            mouse_kwargs["on_move"] = self._on_mouse_move

        self._mouse_listener = mouse.Listener(**mouse_kwargs)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

        # 启动保存线程
        self._save_thread = threading.Thread(target=self._save_loop, daemon=True)
        self._save_thread.start()

        logger.info("键鼠监控已启动")

    def stop(self) -> None:
        """停止键鼠监控，关闭监听器和保存线程"""
        if not self._running:
            return
        self._running = False

        # 停止监听器
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()

        # 保存剩余事件
        self._flush_buffer()
        logger.info("键鼠监控已停止")

    def get_stats(self) -> dict:
        """获取当前统计数据"""
        return {
            "key_press_count": self._key_press_count,
            "mouse_click_count": self._mouse_click_count,
            "mouse_move_count": self._mouse_move_count,
            "scroll_count": self._scroll_count,
        }

    @property
    def is_running(self) -> bool:
        """监控是否正在运行"""
        return self._running