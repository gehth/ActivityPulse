"""电脑行为记录器 - 主入口文件"""

import sys
import os
import logging
import traceback
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def setup_logging() -> str:
    """配置日志系统 - 文件日志+控制台日志"""
    log_dir = os.path.join(os.path.expanduser("~"), ".computer_monitor", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 日志文件名按日期
    log_file = os.path.join(log_dir, f"monitor_{datetime.now().strftime('%Y%m%d')}.log")

    # 根日志器配置
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 文件Handler - 详细日志
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)
    root_logger.addHandler(file_handler)

    # 控制台Handler - 仅WARNING以上
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_fmt = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # 第三方库日志级别抑制
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('pynput').setLevel(logging.WARNING)

    logging.info(f"日志系统已启动，日志文件: {log_file}")
    return log_file


def global_exception_handler(exc_type: type, exc_value: Exception, exc_tb: object) -> None:
    """全局异常处理器 - 捕获未处理异常并记录到日志"""
    # 记录到日志
    logging.critical("未捕获的异常", exc_info=(exc_type, exc_value, exc_tb))

    # 写入单独的crash日志
    crash_dir = os.path.join(os.path.expanduser("~"), ".computer_monitor", "logs")
    os.makedirs(crash_dir, exist_ok=True)
    crash_file = os.path.join(crash_dir, "crash.log")
    with open(crash_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"崩溃时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"异常类型: {exc_type.__name__}\n")
        f.write(f"异常信息: {exc_value}\n")
        f.write(f"堆栈跟踪:\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        f.write(f"{'='*60}\n")

    # 显示错误对话框（如果QApplication可用）
    try:
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("程序异常")
        msg.setText(f"发生未预期的错误: {exc_type.__name__}")
        msg.setDetailedText(''.join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        msg.exec_()
    except Exception:
        pass

    # 调用原始异常钩子
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def check_dependencies() -> bool:
    """检查依赖库是否安装"""
    missing = []
    try:
        import PyQt5
    except ImportError:
        missing.append("PyQt5")

    try:
        import pynput
    except ImportError:
        missing.append("pynput")

    try:
        from PIL import Image, ImageGrab
    except ImportError:
        missing.append("Pillow")

    try:
        import psutil
    except ImportError:
        missing.append("psutil")

    if missing:
        print("=" * 50)
        print("缺少以下依赖库，请先安装：")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 50)
        return False
    return True


def main() -> None:
    """主函数"""
    if not check_dependencies():
        sys.exit(1)

    # 配置日志系统
    setup_logging()

    # 安装全局异常处理器
    sys.excepthook = global_exception_handler

    logging.info("程序启动")

    # 高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置全局字体
    font = app.font()
    font.setFamily("Microsoft YaHei")
    font.setPointSize(9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    logging.info("主窗口已显示")

    exit_code = app.exec_()
    logging.info(f"程序退出，代码: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()