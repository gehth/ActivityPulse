"""anomaly_detector 异常行为检测引擎单元测试"""
import pytest
from unittest.mock import MagicMock, patch
from utils.anomaly_detector import AnomalyDetector, DEFAULT_ANOMALY_CONFIG


@pytest.fixture
def mock_db():
    """创建模拟数据库管理器"""
    db = MagicMock()

    # 默认配置：所有检测启用
    def get_config_side_effect(key, default=""):
        return DEFAULT_ANOMALY_CONFIG.get(key, default)

    db.get_config.side_effect = get_config_side_effect
    return db


@pytest.fixture
def detector(mock_db):
    """创建检测器实例"""
    return AnomalyDetector(mock_db)


class TestAnomalyDetectorInit:
    """初始化测试"""

    def test_creates_with_db(self, mock_db):
        """应正确创建检测器"""
        d = AnomalyDetector(mock_db)
        assert d.db is mock_db


class TestDetectAll:
    """detect_all 总调度测试"""

    def test_returns_empty_when_disabled(self, detector, mock_db):
        """总开关关闭时应返回空列表"""
        mock_db.get_config.side_effect = lambda key, default="": "0" if key == "anomaly_enabled" else DEFAULT_ANOMALY_CONFIG.get(key, default)
        result = detector.detect_all()
        assert result == []

    def test_calls_all_detect_methods(self, detector, mock_db):
        """启用时应调用所有检测方法"""
        mock_db.get_continuous_app_usage.return_value = []
        mock_db.get_late_night_usage.return_value = []
        mock_db.get_recent_daily_totals.return_value = []
        mock_db.get_continuous_computer_usage.return_value = []
        mock_db.check_recent_alert_exists.return_value = False

        detector.detect_all()

        mock_db.get_continuous_app_usage.assert_called_once()
        mock_db.get_late_night_usage.assert_called_once()
        mock_db.get_recent_daily_totals.assert_called_once()
        mock_db.get_continuous_computer_usage.assert_called_once()

    def test_saves_alerts_to_db(self, detector, mock_db):
        """检测到异常时应保存告警"""
        mock_db.get_continuous_app_usage.return_value = [
            {"app_name": "chrome.exe", "duration_minutes": 150, "start_time": "09:00", "end_time": "11:30"}
        ]
        mock_db.check_recent_alert_exists.return_value = False
        mock_db.save_anomaly_alert.return_value = 1

        result = detector.detect_all()

        assert len(result) > 0
        mock_db.save_anomaly_alert.assert_called()


class TestDetectContinuousUse:
    """detect_continuous_use 连续使用检测测试"""

    def test_no_alert_when_below_threshold(self, detector, mock_db):
        """低于阈值不应产生告警"""
        mock_db.get_continuous_app_usage.return_value = []
        result = detector.detect_continuous_use()
        assert result == []

    def test_alert_when_exceeds_threshold(self, detector, mock_db):
        """超过阈值应产生告警"""
        mock_db.get_continuous_app_usage.return_value = [
            {"app_name": "chrome.exe", "duration_minutes": 150, "start_time": "09:00", "end_time": "11:30"}
        ]
        mock_db.check_recent_alert_exists.return_value = False

        result = detector.detect_continuous_use()

        assert len(result) == 1
        assert result[0]["alert_type"] == "continuous_use"
        assert result[0]["app_name"] == "chrome.exe"
        assert result[0]["severity"] == "warning"

    def test_critical_severity_when_far_exceeds(self, detector, mock_db):
        """远超阈值应产生critical级别告警"""
        mock_db.get_continuous_app_usage.return_value = [
            {"app_name": "code.exe", "duration_minutes": 200, "start_time": "08:00", "end_time": "11:20"}
        ]
        mock_db.check_recent_alert_exists.return_value = False

        result = detector.detect_continuous_use()

        assert len(result) == 1
        assert result[0]["severity"] == "critical"

    def test_no_alert_during_cooldown(self, detector, mock_db):
        """冷却期内不应重复告警"""
        mock_db.get_continuous_app_usage.return_value = [
            {"app_name": "chrome.exe", "duration_minutes": 150, "start_time": "09:00", "end_time": "11:30"}
        ]
        mock_db.check_recent_alert_exists.return_value = True  # 冷却期内

        result = detector.detect_continuous_use()

        assert result == []


class TestDetectLateNight:
    """detect_late_night 深夜活跃检测测试"""

    def test_no_alert_when_disabled(self, detector, mock_db):
        """深夜检测关闭时不应告警"""
        def get_config_side_effect(key, default=""):
            if key == "anomaly_late_night_enabled":
                return "0"
            return DEFAULT_ANOMALY_CONFIG.get(key, default)

        mock_db.get_config.side_effect = get_config_side_effect
        result = detector.detect_late_night()
        assert result == []

    def test_alert_when_exceeds_threshold(self, detector, mock_db):
        """深夜使用超阈值应产生告警"""
        mock_db.get_late_night_usage.return_value = [
            {"app_name": "chrome.exe", "total_minutes": 50},
            {"app_name": "code.exe", "total_minutes": 20},
        ]
        mock_db.check_recent_alert_exists.return_value = False

        result = detector.detect_late_night()

        assert len(result) == 1
        assert result[0]["alert_type"] == "late_night"
        assert result[0]["severity"] == "warning"

    def test_critical_severity_for_double_threshold(self, detector, mock_db):
        """深夜使用达2倍阈值应产生critical告警"""
        mock_db.get_late_night_usage.return_value = [
            {"app_name": "chrome.exe", "total_minutes": 150},
        ]
        mock_db.check_recent_alert_exists.return_value = False

        result = detector.detect_late_night()

        assert len(result) == 1
        assert result[0]["severity"] == "critical"

    def test_no_alert_below_threshold(self, detector, mock_db):
        """深夜使用未超阈值不应告警"""
        mock_db.get_late_night_usage.return_value = [
            {"app_name": "chrome.exe", "total_minutes": 30},
        ]

        result = detector.detect_late_night()

        assert result == []


class TestDetectDailyDeviation:
    """detect_daily_deviation 日使用偏离检测测试"""

    def test_no_alert_when_disabled(self, detector, mock_db):
        """偏离检测关闭时不应告警"""
        def get_config_side_effect(key, default=""):
            if key == "anomaly_deviation_enabled":
                return "0"
            return DEFAULT_ANOMALY_CONFIG.get(key, default)

        mock_db.get_config.side_effect = get_config_side_effect
        result = detector.detect_daily_deviation()
        assert result == []

    def test_no_alert_insufficient_data(self, detector, mock_db):
        """数据不足3天不应告警"""
        mock_db.get_recent_daily_totals.return_value = [
            {"date": "2025-01-15", "total_minutes": 120},
            {"date": "2025-01-14", "total_minutes": 100},
        ]
        result = detector.detect_daily_deviation()
        assert result == []

    def test_alert_when_deviation_exceeds_factor(self, detector, mock_db):
        """使用时长偏离超过倍数应告警"""
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")

        mock_db.get_recent_daily_totals.return_value = [
            {"date": today_str, "total_minutes": 600},  # 今天10小时
            {"date": "2025-01-14", "total_minutes": 120},  # 昨天2小时
            {"date": "2025-01-13", "total_minutes": 100},  # 前天1.7小时
            {"date": "2025-01-12", "total_minutes": 110},  # 3天前1.8小时
        ]
        mock_db.check_recent_alert_exists.return_value = False

        result = detector.detect_daily_deviation()

        # 均值约110分钟，今天600分钟，偏离超过1.5倍
        assert len(result) == 1
        assert result[0]["alert_type"] == "daily_deviation"

    def test_no_alert_when_within_normal_range(self, detector, mock_db):
        """使用时长在正常范围不应告警"""
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")

        mock_db.get_recent_daily_totals.return_value = [
            {"date": today_str, "total_minutes": 120},
            {"date": "2025-01-14", "total_minutes": 100},
            {"date": "2025-01-13", "total_minutes": 110},
            {"date": "2025-01-12", "total_minutes": 105},
        ]

        result = detector.detect_daily_deviation()
        assert result == []


class TestDetectNoBreak:
    """detect_no_break 无休息检测测试"""

    def test_no_alert_below_threshold(self, detector, mock_db):
        """低于阈值不应告警"""
        mock_db.get_continuous_computer_usage.return_value = [
            {"duration_minutes": 120, "start_time": "09:00", "end_time": "11:00"}
        ]

        result = detector.detect_no_break()
        assert result == []

    def test_alert_when_exceeds_threshold(self, detector, mock_db):
        """超过阈值应产生告警"""
        mock_db.get_continuous_computer_usage.return_value = [
            {"duration_minutes": 300, "start_time": "09:00", "end_time": "14:00"}
        ]
        mock_db.check_recent_alert_exists.return_value = False

        result = detector.detect_no_break()

        assert len(result) == 1
        assert result[0]["alert_type"] == "no_break"
        assert result[0]["severity"] == "warning"

    def test_critical_severity_for_far_exceeds(self, detector, mock_db):
        """远超阈值应产生critical告警"""
        mock_db.get_continuous_computer_usage.return_value = [
            {"duration_minutes": 400, "start_time": "08:00", "end_time": "14:40"}
        ]
        mock_db.check_recent_alert_exists.return_value = False

        result = detector.detect_no_break()

        assert len(result) == 1
        assert result[0]["severity"] == "critical"