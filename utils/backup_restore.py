"""数据备份与恢复工具

备份：将数据库+截图目录打包为zip
恢复：从zip解压并替换当前数据
"""

import os
import shutil
import zipfile
import tempfile
import logging
from datetime import datetime
from typing import Optional, Callable
import sqlite3
import re

logger = logging.getLogger(__name__)

# 数据目录
DATA_DIR = os.path.join(os.path.expanduser("~"), ".computer_monitor")
DB_FILE = os.path.join(DATA_DIR, "monitor.db")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")


def create_backup(output_dir: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> str:
    """创建数据备份

    Args:
        output_dir: 备份文件输出目录
        progress_callback: 进度回调 (percent, message)

    Returns:
        备份文件路径

    Raises:
        FileNotFoundError: 数据库文件不存在
        OSError: 文件操作失败
    """
    if not os.path.exists(DB_FILE):
        raise FileNotFoundError(f"数据库文件不存在: {DB_FILE}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"behavior_backup_{timestamp}.zip"
    backup_path = os.path.join(output_dir, backup_filename)

    if progress_callback:
        progress_callback(5, "正在准备备份...")

    # 统计文件数量用于进度计算
    total_files = 1  # 数据库文件
    screenshot_files = []
    if os.path.exists(SCREENSHOTS_DIR):
        for root, dirs, files in os.walk(SCREENSHOTS_DIR):
            for f in files:
                filepath = os.path.join(root, f)
                # 跳过临时文件
                if not f.startswith('~') and not f.startswith('.'):
                    screenshot_files.append(filepath)
                    total_files += 1

    if progress_callback:
        progress_callback(10, f"正在备份，共 {total_files} 个文件...")

    # 创建zip备份
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        _backup_database_to_zip(zf, progress_callback)
        _backup_screenshots_to_zip(zf, screenshot_files, total_files, progress_callback)

    if progress_callback:
        progress_callback(100, "备份完成！")

    # 计算备份文件大小
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    logger.info(f"备份完成: {backup_path} ({size_mb:.1f}MB)")

    return backup_path


def _backup_database_to_zip(zf, progress_callback=None):
    """将数据库备份到zip文件中（使用SQLite backup API确保一致性）"""
    if progress_callback:
        progress_callback(15, "正在备份数据库...")

    temp_db = os.path.join(tempfile.gettempdir(), "monitor_backup.db")
    try:
        src_conn = sqlite3.connect(DB_FILE)
        dst_conn = sqlite3.connect(temp_db)
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        zf.write(temp_db, "monitor.db")
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def _backup_screenshots_to_zip(zf, screenshot_files, total_files, progress_callback=None):
    """将截图文件备份到zip文件中"""
    if not screenshot_files:
        return

    processed = 0
    for filepath in screenshot_files:
        # 保留相对路径结构
        rel_path = os.path.relpath(filepath, DATA_DIR)
        arcname = rel_path.replace("\\", "/")
        zf.write(filepath, arcname)
        processed += 1

        # 每处理50个文件更新一次进度
        if progress_callback and processed % 50 == 0:
            percent = 15 + int(80 * processed / total_files)
            progress_callback(percent, f"正在备份截图 ({processed}/{len(screenshot_files)})...")


def restore_backup(backup_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> dict:
    """从备份恢复数据

    Args:
        backup_path: 备份zip文件路径
        progress_callback: 进度回调 (percent, message)

    Returns:
        恢复信息字典 {"db_restored": bool, "screenshots_restored": int}

    Raises:
        FileNotFoundError: 备份文件不存在
        zipfile.BadZipFile: 备份文件损坏
        OSError: 文件操作失败
    """
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"备份文件不存在: {backup_path}")

    if progress_callback:
        progress_callback(5, "正在验证备份文件...")

    # 验证zip文件
    if not zipfile.is_zipfile(backup_path):
        raise zipfile.BadZipFile("备份文件格式无效")

    result = {"db_restored": False, "screenshots_restored": 0}

    with zipfile.ZipFile(backup_path, 'r') as zf:
        namelist = zf.namelist()

        # 检查是否包含数据库
        if "monitor.db" not in namelist:
            raise ValueError("备份文件中未找到数据库")

        if progress_callback:
            progress_callback(10, "正在恢复数据库...")

        # 1. 恢复数据库
        result["db_restored"] = _restore_database(zf)

        # 2. 恢复截图
        screenshot_entries = [n for n in namelist if n.startswith("screenshots/")]
        if screenshot_entries:
            result["screenshots_restored"] = _restore_screenshots(zf, screenshot_entries, progress_callback)

    if progress_callback:
        progress_callback(100, "恢复完成！")

    logger.info(f"恢复完成: db={result['db_restored']}, screenshots={result['screenshots_restored']}")
    return result


def _restore_database(zf) -> bool:
    """从zip文件恢复数据库，返回是否成功"""
    temp_db = os.path.join(tempfile.gettempdir(), "monitor_restore.db")
    try:
        zf.extract("monitor.db", tempfile.gettempdir())
        temp_db = os.path.join(tempfile.gettempdir(), "monitor.db")

        # 确保数据目录存在
        os.makedirs(DATA_DIR, exist_ok=True)

        # 备份当前数据库（以防恢复失败）
        current_db_backup = None
        if os.path.exists(DB_FILE):
            current_db_backup = DB_FILE + ".bak"
            shutil.copy2(DB_FILE, current_db_backup)

        try:
            # 替换数据库
            shutil.copy2(temp_db, DB_FILE)
            return True
        except Exception as e:
            # 恢复失败，还原备份
            if current_db_backup and os.path.exists(current_db_backup):
                shutil.copy2(current_db_backup, DB_FILE)
            raise e
        finally:
            # 清理临时文件
            if current_db_backup and os.path.exists(current_db_backup):
                os.remove(current_db_backup)
    finally:
        if os.path.exists(temp_db):
            os.remove(temp_db)


def _restore_screenshots(zf, screenshot_entries: list, progress_callback) -> int:
    """从zip文件恢复截图，返回恢复数量"""
    if progress_callback:
        progress_callback(30, f"正在恢复截图 ({len(screenshot_entries)} 个文件)...")

    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    processed = 0
    for entry in screenshot_entries:
        target_path = os.path.join(DATA_DIR, entry.replace("/", os.sep))
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        # 跳过目录条目
        if entry.endswith('/'):
            continue
        try:
            zf.extract(entry, DATA_DIR)
            processed += 1
        except Exception as e:
            logger.warning(f"恢复截图失败 {entry}: {e}")

        if progress_callback and processed % 50 == 0:
            percent = 30 + int(65 * processed / len(screenshot_entries))
            progress_callback(percent, f"正在恢复截图 ({processed}/{len(screenshot_entries)})...")

    return processed


def get_backup_info(backup_path: str) -> dict:
    """获取备份文件信息（不执行恢复）

    Returns:
        {"size_mb": float, "has_db": bool, "screenshot_count": int, "date": str}
    """
    if not os.path.exists(backup_path):
        return None

    info = {
        "size_mb": os.path.getsize(backup_path) / (1024 * 1024),
        "has_db": False,
        "screenshot_count": 0,
        "date": "",
    }

    try:
        with zipfile.ZipFile(backup_path, 'r') as zf:
            namelist = zf.namelist()
            info["has_db"] = "monitor.db" in namelist
            info["screenshot_count"] = len([n for n in namelist if n.startswith("screenshots/") and not n.endswith('/')])
            # 从文件名提取日期
            match = re.search(r'(\d{8}_\d{6})', os.path.basename(backup_path))
            if match:
                info["date"] = match.group(1)
    except Exception:
        pass

    return info