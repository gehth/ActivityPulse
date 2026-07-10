"""backup_restore 数据备份与恢复工具单元测试"""
import os
import tempfile
import zipfile
import pytest
from unittest.mock import patch
from utils.backup_restore import create_backup, restore_backup, get_backup_info, DATA_DIR, DB_FILE


@pytest.fixture
def temp_env(tmp_path):
    """创建临时测试环境（模拟数据目录和数据库）"""
    # 创建临时数据目录
    data_dir = tmp_path / ".computer_monitor"
    data_dir.mkdir()
    db_file = data_dir / "monitor.db"
    screenshots_dir = data_dir / "screenshots"
    screenshots_dir.mkdir()

    # 创建一个最小的SQLite数据库
    import sqlite3
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE test (id INTEGER)")
    conn.execute("INSERT INTO test VALUES (1)")
    conn.commit()
    conn.close()

    # 创建一些测试截图文件
    for i in range(3):
        screenshot = screenshots_dir / f"screenshot_{i}.png"
        screenshot.write_bytes(b"fake_png_data_" + str(i).encode())

    return {
        "data_dir": str(data_dir),
        "db_file": str(db_file),
        "screenshots_dir": str(screenshots_dir),
        "output_dir": str(tmp_path / "backups"),
    }


class TestCreateBackup:
    """create_backup 备份创建测试"""

    def test_backup_creates_zip(self, temp_env):
        """备份应创建zip文件"""
        output_dir = temp_env["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        with patch("utils.backup_restore.DB_FILE", temp_env["db_file"]), \
             patch("utils.backup_restore.DATA_DIR", temp_env["data_dir"]), \
             patch("utils.backup_restore.SCREENSHOTS_DIR", temp_env["screenshots_dir"]):
            backup_path = create_backup(output_dir)

        assert os.path.exists(backup_path)
        assert backup_path.endswith(".zip")

    def test_backup_contains_database(self, temp_env):
        """备份zip应包含数据库文件"""
        output_dir = temp_env["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        with patch("utils.backup_restore.DB_FILE", temp_env["db_file"]), \
             patch("utils.backup_restore.DATA_DIR", temp_env["data_dir"]), \
             patch("utils.backup_restore.SCREENSHOTS_DIR", temp_env["screenshots_dir"]):
            backup_path = create_backup(output_dir)

        with zipfile.ZipFile(backup_path, 'r') as zf:
            assert "monitor.db" in zf.namelist()

    def test_backup_contains_screenshots(self, temp_env):
        """备份zip应包含截图文件"""
        output_dir = temp_env["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        with patch("utils.backup_restore.DB_FILE", temp_env["db_file"]), \
             patch("utils.backup_restore.DATA_DIR", temp_env["data_dir"]), \
             patch("utils.backup_restore.SCREENSHOTS_DIR", temp_env["screenshots_dir"]):
            backup_path = create_backup(output_dir)

        with zipfile.ZipFile(backup_path, 'r') as zf:
            screenshot_entries = [n for n in zf.namelist() if n.startswith("screenshots/")]
            assert len(screenshot_entries) == 3

    def test_backup_raises_if_db_missing(self, tmp_path):
        """数据库文件不存在时应抛出FileNotFoundError"""
        output_dir = str(tmp_path / "backups")
        os.makedirs(output_dir, exist_ok=True)
        fake_db = str(tmp_path / "nonexistent.db")

        with patch("utils.backup_restore.DB_FILE", fake_db):
            with pytest.raises(FileNotFoundError):
                create_backup(output_dir)

    def test_backup_progress_callback(self, temp_env):
        """进度回调应被调用"""
        output_dir = temp_env["output_dir"]
        os.makedirs(output_dir, exist_ok=True)
        progress_calls = []

        def callback(percent, msg):
            progress_calls.append((percent, msg))

        with patch("utils.backup_restore.DB_FILE", temp_env["db_file"]), \
             patch("utils.backup_restore.DATA_DIR", temp_env["data_dir"]), \
             patch("utils.backup_restore.SCREENSHOTS_DIR", temp_env["screenshots_dir"]):
            create_backup(output_dir, progress_callback=callback)

        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == 100  # 最后应为100%


class TestRestoreBackup:
    """restore_backup 备份恢复测试"""

    def test_restore_database(self, temp_env):
        """恢复应还原数据库文件"""
        output_dir = temp_env["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        with patch("utils.backup_restore.DB_FILE", temp_env["db_file"]), \
             patch("utils.backup_restore.DATA_DIR", temp_env["data_dir"]), \
             patch("utils.backup_restore.SCREENSHOTS_DIR", temp_env["screenshots_dir"]):
            backup_path = create_backup(output_dir)

            # 恢复到新的临时目录
            restore_dir = tempfile.mkdtemp()
            restore_db = os.path.join(restore_dir, "monitor.db")
            restore_screenshots = os.path.join(restore_dir, "screenshots")

            with patch("utils.backup_restore.DB_FILE", restore_db), \
                 patch("utils.backup_restore.DATA_DIR", restore_dir), \
                 patch("utils.backup_restore.SCREENSHOTS_DIR", restore_screenshots):
                result = restore_backup(backup_path)

        assert result["db_restored"] is True

    def test_restore_raises_if_backup_missing(self, tmp_path):
        """备份文件不存在时应抛出FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            restore_backup(str(tmp_path / "nonexistent.zip"))


class TestGetBackupInfo:
    """get_backup_info 备份信息查询测试"""

    def test_info_from_valid_backup(self, temp_env):
        """有效备份应返回正确信息"""
        output_dir = temp_env["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        with patch("utils.backup_restore.DB_FILE", temp_env["db_file"]), \
             patch("utils.backup_restore.DATA_DIR", temp_env["data_dir"]), \
             patch("utils.backup_restore.SCREENSHOTS_DIR", temp_env["screenshots_dir"]):
            backup_path = create_backup(output_dir)
            info = get_backup_info(backup_path)

        assert info is not None
        assert info["has_db"] is True
        assert info["screenshot_count"] == 3
        assert info["size_mb"] > 0

    def test_info_returns_none_for_missing_file(self, tmp_path):
        """不存在的文件应返回None"""
        info = get_backup_info(str(tmp_path / "nonexistent.zip"))
        assert info is None

    def test_info_extracts_date_from_filename(self, temp_env):
        """应从文件名提取日期"""
        output_dir = temp_env["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        with patch("utils.backup_restore.DB_FILE", temp_env["db_file"]), \
             patch("utils.backup_restore.DATA_DIR", temp_env["data_dir"]), \
             patch("utils.backup_restore.SCREENSHOTS_DIR", temp_env["screenshots_dir"]):
            backup_path = create_backup(output_dir)
            info = get_backup_info(backup_path)

        # 文件名格式: behavior_backup_YYYYMMDD_HHMMSS.zip
        assert info["date"] != ""
        assert len(info["date"]) == 15  # YYYYMMDD_HHMMSS