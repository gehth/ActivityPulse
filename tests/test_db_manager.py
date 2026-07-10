"""db_manager 数据库管理器单元测试"""
import pytest
from database.db_manager import DatabaseManager


class TestDatabaseInit:
    """数据库初始化测试"""

    def test_db_created(self, db):
        """数据库文件应被创建"""
        import os
        assert os.path.exists(db.db_path)

    def test_tables_created(self, db):
        """所有表应被创建"""
        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
        expected = {"app_usage", "input_events", "screenshots", "app_settings",
                    "config", "app_limits", "activity_tags", "anomaly_alerts"}
        assert expected.issubset(tables)


class TestConfigCache:
    """配置缓存测试"""

    def test_save_and_get_config(self, db):
        """保存并读取配置"""
        db.save_config("test_key", "test_value")
        assert db.get_config("test_key") == "test_value"

    def test_get_config_default(self, db):
        """不存在的配置返回默认值"""
        assert db.get_config("nonexistent", "default") == "default"

    def test_get_config_none_default(self, db):
        """不存在的配置无默认值返回None"""
        assert db.get_config("nonexistent") is None

    def test_cache_hit(self, db):
        """缓存命中：重复读取不查数据库"""
        db.save_config("cached_key", "cached_val")
        # 第一次读取填充缓存
        val1 = db.get_config("cached_key")
        # 清空数据库验证缓存生效
        db._execute("DELETE FROM config WHERE key = ?", ("cached_key",))
        # 缓存应仍返回原值
        val2 = db.get_config("cached_key")
        assert val1 == val2 == "cached_val"

    def test_save_updates_cache(self, db):
        """save_config应同步更新缓存"""
        db.save_config("update_key", "old_val")
        db.save_config("update_key", "new_val")
        assert db.get_config("update_key") == "new_val"

    def test_cache_dict_initialized(self, db):
        """_config_cache应为dict"""
        assert isinstance(db._config_cache, dict)


class TestAppUsage:
    """应用使用记录测试"""

    def test_save_app_usage(self, db):
        """保存应用使用记录"""
        rid = db.save_app_usage("test.exe", "Test App", "2025-01-15 10:00:00",
                                "2025-01-15 10:30:00", 1800)
        assert rid > 0

    def test_get_app_usage_summary(self, db_with_data):
        """获取应用使用汇总"""
        summary = db_with_data.get_app_usage_summary("2025-01-15")
        assert len(summary) > 0
        # 应有chrome.exe和code.exe
        apps = {s["app_name"] for s in summary}
        assert "chrome.exe" in apps
        assert "code.exe" in apps

    def test_get_day_total_seconds(self, db_with_data):
        """获取某天总使用时长"""
        total = db_with_data.get_day_total_seconds("2025-01-15")
        # 5条记录: 1800+3600+1800+900+2700 = 10800秒
        assert total == 10800

    def test_get_day_app_count(self, db_with_data):
        """获取某天活跃应用数"""
        count = db_with_data.get_day_app_count("2025-01-15")
        # chrome.exe, code.exe, notepad.exe = 3
        assert count == 3

    def test_get_day_total_seconds_empty(self, db):
        """无数据日期返回0"""
        total = db.get_day_total_seconds("2025-01-01")
        assert total == 0


class TestContinuousUsage:
    """连续使用时段测试"""

    def test_continuous_app_usage(self, db_with_data):
        """获取连续使用同一应用的时段"""
        # code.exe: 09:30-10:30 + 11:15-12:00，间隔45分钟 > 5分钟阈值
        # 应分为两段，但只有09:30-10:30(3600秒) >= 60分钟阈值
        results = db_with_data.get_continuous_app_usage("2025-01-15", min_minutes=60)
        assert len(results) >= 1
        # 至少有一段code.exe
        code_segments = [r for r in results if r["app_name"] == "code.exe"]
        assert len(code_segments) >= 1

    def test_continuous_computer_usage(self, db_with_data):
        """获取连续使用电脑的时段"""
        # 所有记录间隔 <= 10分钟，应合并为1段
        results = db_with_data.get_continuous_computer_usage("2025-01-15", gap_minutes=10)
        assert len(results) >= 1
        # 第一段应从09:00开始
        assert results[0]["start_time"].startswith("2025-01-15 09:")

    def test_continuous_computer_usage_empty(self, db):
        """无数据日期返回空"""
        results = db.get_continuous_computer_usage("2025-01-01")
        assert results == []


class TestAppLimits:
    """应用使用限制测试"""

    def test_set_and_get_limit(self, db):
        """设置并获取限制"""
        db.set_app_limit("chrome.exe", 120, enabled=True)
        limit = db.get_app_limit("chrome.exe")
        assert limit is not None
        assert limit["daily_limit_minutes"] == 120
        assert limit["enabled"] == 1

    def test_remove_limit(self, db):
        """删除限制"""
        db.set_app_limit("test.exe", 60)
        db.remove_app_limit("test.exe")
        assert db.get_app_limit("test.exe") is None

    def test_check_app_limit_not_set(self, db):
        """未设置限制返回None"""
        result = db.check_app_limit("nonexistent.exe", "2025-01-15")
        assert result is None

    def test_check_app_limit_exceeded(self, db_with_data):
        """检查是否超限"""
        # chrome.exe 使用了3600秒=60分钟
        db_with_data.set_app_limit("chrome.exe", 30, enabled=True)
        result = db_with_data.check_app_limit("chrome.exe", "2025-01-15")
        assert result is not None
        assert result["exceeded"] is True

    def test_get_exceeded_limits(self, db_with_data):
        """获取所有超限应用"""
        db_with_data.set_app_limit("chrome.exe", 30, enabled=True)
        exceeded = db_with_data.get_exceeded_limits("2025-01-15")
        assert len(exceeded) >= 1
        assert any(e["app_name"] == "chrome.exe" for e in exceeded)


class TestNDayTrend:
    """N天趋势数据测试"""

    def test_get_n_day_trend(self, db_with_data):
        """获取N天趋势"""
        result = db_with_data.get_n_day_trend("2025-01-15", 3)
        assert len(result) == 3
        # 应包含 days_ago 字段
        assert all("days_ago" in r for r in result)
        assert all("total_seconds" in r for r in result)

    def test_get_n_day_trend_empty(self, db):
        """无数据日期返回0"""
        result = db.get_n_day_trend("2025-01-15", 3)
        assert len(result) == 3
        assert all(r["total_seconds"] == 0 for r in result)