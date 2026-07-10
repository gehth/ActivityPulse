"""异步数据加载模块 - 使用QThread避免主线程阻塞"""

import logging
from PyQt5.QtCore import QThread, pyqtSignal, QObject

logger = logging.getLogger(__name__)


class DataLoadWorker(QThread):
    """通用异步数据加载Worker

    在后台线程执行数据查询函数，通过信号返回结果到主线程。
    用法：
        worker = DataLoadWorker(lambda db: db.get_app_usage_summary(date))
        worker.result_ready.connect(self._on_data_loaded)
        worker.start()
    """

    result_ready = pyqtSignal(object)  # 查询结果
    error_occurred = pyqtSignal(str)   # 错误信息

    def __init__(self, load_func, parent=None):
        """
        Args:
            load_func: 无参可调用对象，返回查询结果。
                       闭包捕获db_manager和参数。
        """
        super().__init__(parent)
        self._load_func = load_func
        self._cancelled = False

    def run(self):
        """在后台线程执行数据加载"""
        try:
            if not self._cancelled:
                result = self._load_func()
                if not self._cancelled:
                    self.result_ready.emit(result)
        except Exception as e:
            logger.error(f"异步数据加载失败: {e}", exc_info=True)
            if not self._cancelled:
                self.error_occurred.emit(str(e))

    def cancel(self):
        """取消加载"""
        self._cancelled = True


class MultiDataLoader(QObject):
    """多数据源并行加载器

    同时加载多个数据源，全部完成后统一回调。
    用法：
        loader = MultiDataLoader()
        loader.add("summary", lambda: db.get_app_usage_summary(date))
        loader.add("trend", lambda: db.get_7day_trend(date))
        loader.all_done.connect(self._on_all_loaded)
        loader.start()
    """

    all_done = pyqtSignal(dict)       # {key: result}
    partial_done = pyqtSignal(str, object)  # (key, result)
    error_occurred = pyqtSignal(str, str)   # (key, error_msg)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks = {}  # {key: load_func}
        self._results = {}
        self._errors = {}
        self._workers = []

    def add(self, key: str, load_func):
        """添加一个数据加载任务"""
        self._tasks[key] = load_func

    def start(self):
        """启动所有加载任务"""
        self._results = {}
        self._errors = {}
        self._workers = []

        for key, func in self._tasks.items():
            worker = DataLoadWorker(func)
            worker.result_ready.connect(lambda result, k=key: self._on_result(k, result))
            worker.error_occurred.connect(lambda err, k=key: self._on_error(k, err))
            self._workers.append(worker)
            worker.start()

    def _on_result(self, key: str, result):
        """单个任务完成"""
        self._results[key] = result
        self.partial_done.emit(key, result)
        self._check_all_done()

    def _on_error(self, key: str, error_msg: str):
        """单个任务出错"""
        self._errors[key] = error_msg
        self.error_occurred.emit(key, error_msg)
        self._check_all_done()

    def _check_all_done(self):
        """检查是否全部完成"""
        if len(self._results) + len(self._errors) >= len(self._tasks):
            # 合并结果和错误
            final = {}
            for k, v in self._results.items():
                final[k] = v
            for k, v in self._errors.items():
                final[k] = None  # 出错的任务结果为None
            self.all_done.emit(final)

    def cancel_all(self):
        """取消所有任务"""
        for worker in self._workers:
            worker.cancel()
            worker.wait(1000)