"""pytest 配置和共享 fixtures"""
import os
import sys
import tempfile
import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager


@pytest.fixture
def db(tmp_path):
    """创建临时数据库，测试结束后自动清理"""
    db_path = str(tmp_path / "test_monitor.db")
    manager = DatabaseManager(db_path)
    yield manager
    # 清理：关闭数据库连接
    manager.close()


@pytest.fixture
def db_with_data(db):
    """预填充测试数据的数据库"""
    # 插入配置
    db.save_config("anomaly_enabled", "1")
    db.save_config("anomaly_continuous_minutes", "120")

    # 插入应用使用记录
    from datetime import datetime
    records = [
        ("chrome.exe", "Google Chrome", "2025-01-15 09:00:00", "2025-01-15 09:30:00", 1800),
        ("code.exe", "VS Code", "2025-01-15 09:30:00", "2025-01-15 10:30:00", 3600),
        ("chrome.exe", "Google Chrome", "2025-01-15 10:30:00", "2025-01-15 11:00:00", 1800),
        ("notepad.exe", "Notepad", "2025-01-15 11:00:00", "2025-01-15 11:15:00", 900),
        ("code.exe", "VS Code", "2025-01-15 11:15:00", "2025-01-15 12:00:00", 2700),
    ]
    for app, title, start, end, dur in records:
        db.save_app_usage(app, title, start, end, dur)

    return db