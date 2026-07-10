"""屏幕活动记录模块 - 定时截图保存"""

import os
import threading
import time
import logging
from datetime import datetime
from database.db_manager import DatabaseManager
import inspect
import ctypes

logger = logging.getLogger(__name__)

try:
    from PIL import ImageGrab, Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ScreenMonitor:
    """定时截图监控"""

    def __init__(self, db_manager: DatabaseManager, interval: float = 60.0,
                 quality: int = 80, save_screenshots: bool = True) -> None:
        """
        初始化屏幕截图监控

        Args:
            db_manager: 数据库管理器实例
            interval: 截图间隔（秒），默认60秒
            quality: JPEG压缩质量（1-100）
            save_screenshots: 是否保存截图文件
        """
        self.db = db_manager
        self.interval = interval
        self.quality = quality
        self.save_screenshots = save_screenshots
        self._running = False
        self._thread = None
        self._screenshot_count = 0

        # 设置截图保存目录
        self.screenshot_dir = os.path.join(
            os.path.expanduser("~"), ".computer_monitor", "screenshots"
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def _take_screenshot(self) -> str:
        """
        截取屏幕截图（支持多显示器）

        Returns:
            截图文件路径
        """
        if not PIL_AVAILABLE:
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.jpg"
        filepath = os.path.join(self.screenshot_dir, filename)

        try:
            # 尝试截取多显示器拼接截图
            screenshot = self._grab_all_monitors()
            if screenshot is None:
                # 回退：截取主显示器
                screenshot = ImageGrab.grab()
            # 压缩保存
            screenshot.save(filepath, "JPEG", quality=self.quality)
            return filepath
        except Exception as e:
            logger.warning(f"截图失败: {e}")
            return ""

    def _grab_all_monitors(self) -> object:
        """截取所有显示器的拼接截图

        Returns:
            拼接后的PIL Image，失败返回None
        """
        try:
            # Pillow 10+ 支持 all_screens 参数
            grab_params = inspect.signature(ImageGrab.grab).parameters
            if 'all_screens' in grab_params:
                return ImageGrab.grab(all_screens=True)
        except Exception:
            pass

        # 备用方案：使用win32api获取虚拟屏幕尺寸
        try:
            user32 = ctypes.windll.user32
            virtual_left = user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
            virtual_top = user32.GetSystemMetrics(77)    # SM_YVIRTUALSCREEN
            virtual_width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
            virtual_height = user32.GetSystemMetrics(79) # SM_CYVIRTUALSCREEN

            if virtual_width > 0 and virtual_height > 0:
                bbox = (virtual_left, virtual_top,
                        virtual_left + virtual_width,
                        virtual_top + virtual_height)
                return ImageGrab.grab(bbox=bbox)
        except Exception as e:
            logger.debug(f"多显示器截图回退: {e}")

        return None

    def _create_thumbnail(self, filepath: str, size: tuple = (320, 180)) -> str:
        """
        创建缩略图

        Args:
            filepath: 原图路径
            size: 缩略图尺寸

        Returns:
            缩略图路径
        """
        if not PIL_AVAILABLE or not os.path.exists(filepath):
            return ""

        try:
            thumb_dir = os.path.join(self.screenshot_dir, "thumbnails")
            os.makedirs(thumb_dir, exist_ok=True)

            filename = os.path.basename(filepath)
            thumb_path = os.path.join(thumb_dir, f"thumb_{filename}")

            img = Image.open(filepath)
            img.thumbnail(size)
            img.save(thumb_path, "JPEG", quality=60)
            return thumb_path
        except Exception as e:
            logger.warning(f"创建缩略图失败: {e}")
            return ""

    def _monitor_loop(self) -> None:
        """截图监控循环"""
        while self._running:
            try:
                filepath = self._take_screenshot()
                if filepath:
                    thumbnail_path = self._create_thumbnail(filepath)
                    # 保存记录到数据库
                    self.db.save_screenshot(
                        file_path=filepath,
                        thumbnail_path=thumbnail_path
                    )
                    self._screenshot_count += 1
                    logger.debug(f"截图已保存: {filepath}")
            except Exception as e:
                logger.error(f"屏幕监控错误: {e}")

            # 等待下一次截图
            for _ in range(int(self.interval)):
                if not self._running:
                    break
                time.sleep(1)

    def start(self) -> None:
        """启动屏幕截图监控线程"""
        if not PIL_AVAILABLE:
            logger.warning("Pillow库未安装，无法截图")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"屏幕监控已启动，截图间隔: {self.interval}秒")

    def stop(self) -> None:
        """停止屏幕截图监控"""
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("屏幕监控已停止")

    def take_screenshot_now(self) -> str:
        """立即截取一张截图"""
        filepath = self._take_screenshot()
        if filepath:
            thumbnail_path = self._create_thumbnail(filepath)
            self.db.save_screenshot(
                file_path=filepath,
                thumbnail_path=thumbnail_path
            )
            self._screenshot_count += 1
        return filepath

    @property
    def is_running(self) -> bool:
        """监控是否正在运行"""
        return self._running

    @property
    def screenshot_count(self) -> int:
        """已截取的截图数量"""
        return self._screenshot_count