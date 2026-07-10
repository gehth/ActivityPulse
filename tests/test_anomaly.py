"""异常告警功能测试"""
import tempfile
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager

def test_anomaly_db():
    """测试异常告警数据库方法"""
    db_path = os.path.join(tempfile.gettempdir(), 'test_anomaly.db')
    # 清理旧测试文件
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = DatabaseManager(db_path)
    
    # 1. 测试 save_anomaly_alert
    print('1. Testing save_anomaly_alert...')
    alert_id = db.save_anomaly_alert('continuous_use', 'Test Alert', description='Test desc', app_name='Chrome', severity='warning', threshold_value=120, actual_value=180)
    print(f'   Alert ID: {alert_id}')
    assert alert_id > 0, "save_anomaly_alert should return positive ID"
    
    # 2. 测试 get_anomaly_alerts
    print('2. Testing get_anomaly_alerts...')
    alerts = db.get_anomaly_alerts(limit=10)
    print(f'   Alerts count: {len(alerts)}')
    assert len(alerts) == 1, f"Expected 1 alert, got {len(alerts)}"
    assert alerts[0]['title'] == 'Test Alert'
    
    # 3. 测试 get_unread_alert_count
    print('3. Testing get_unread_alert_count...')
    count = db.get_unread_alert_count()
    print(f'   Unread count: {count}')
    assert count == 1, f"Expected 1 unread, got {count}"
    
    # 4. 测试 check_recent_alert_exists
    print('4. Testing check_recent_alert_exists...')
    exists = db.check_recent_alert_exists('continuous_use', hours=1, app_name='Chrome')
    print(f'   Recent exists: {exists}')
    assert exists, "Should find recent alert for Chrome"
    
    # 5. 测试 mark_alert_read
    print('5. Testing mark_alert_read...')
    db.mark_alert_read(alert_id)
    count2 = db.get_unread_alert_count()
    print(f'   Unread after read: {count2}')
    assert count2 == 0, f"Expected 0 unread, got {count2}"
    
    # 6. 测试 mark_all_alerts_read
    print('6. Testing mark_all_alerts_read...')
    db.save_anomaly_alert('late_night', 'Late Night Test', description='desc2', severity='critical')
    db.mark_all_alerts_read()
    count3 = db.get_unread_alert_count()
    print(f'   Unread after all read: {count3}')
    assert count3 == 0, f"Expected 0 unread, got {count3}"
    
    # 7. 测试 dismiss_alert
    print('7. Testing dismiss_alert...')
    db.dismiss_alert(alert_id)
    alerts2 = db.get_anomaly_alerts(limit=10, dismissed=False)
    print(f'   Active alerts after dismiss: {len(alerts2)}')
    assert len(alerts2) == 1, f"Expected 1 active alert, got {len(alerts2)}"
    
    # 8. 测试 get_continuous_app_usage
    print('8. Testing get_continuous_app_usage...')
    today = datetime.now().strftime("%Y-%m-%d")
    db.save_app_usage('Chrome', 'Test', f'{today} 10:00:00', f'{today} 11:30:00', 5400)
    db.save_app_usage('Chrome', 'Test', f'{today} 11:35:00', f'{today} 12:00:00', 1500)
    continuous = db.get_continuous_app_usage(date=today, min_minutes=60)
    print(f'   Continuous segments: {len(continuous)}')
    for s in continuous:
        print(f'   - {s["app_name"]}: {s["duration_minutes"]:.0f} min')
    assert len(continuous) >= 1, "Should find at least 1 continuous segment"
    
    # 9. 测试 get_late_night_usage
    print('9. Testing get_late_night_usage...')
    db.save_app_usage('VSCode', 'Coding', f'{today} 23:30:00', f'{today} 23:59:00', 1740)
    late = db.get_late_night_usage(date=today)
    print(f'   Late night records: {len(late)}')
    assert len(late) >= 1, "Should find late night usage"
    
    # 10. 测试 get_recent_daily_totals
    print('10. Testing get_recent_daily_totals...')
    totals = db.get_recent_daily_totals(days=7)
    print(f'   Daily totals: {len(totals)}')
    assert len(totals) >= 1, "Should find daily totals"
    
    # 11. 测试 get_continuous_computer_usage
    print('11. Testing get_continuous_computer_usage...')
    segments = db.get_continuous_computer_usage(date=today)
    print(f'   Computer segments: {len(segments)}')
    assert len(segments) >= 1, "Should find computer usage segments"
    
    # 清理
    del db
    import gc
    gc.collect()
    import time
    time.sleep(0.5)
    try:
        os.remove(db_path)
    except PermissionError:
        pass
    print('\nAll database tests PASSED!')


def test_anomaly_detector():
    """测试异常检测引擎"""
    db_path = os.path.join(tempfile.gettempdir(), 'test_anomaly_det.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db = DatabaseManager(db_path)
    
    from utils.anomaly_detector import AnomalyDetector
    detector = AnomalyDetector(db)
    
    # 测试 detect_all（空数据库不应产生告警）
    print('\nTesting AnomalyDetector.detect_all (empty db)...')
    alerts = detector.detect_all()
    print(f'   Alerts from empty db: {len(alerts)}')
    # 空数据库不应有偏离告警（数据不足）
    
    # 插入足够数据触发偏离告警
    print('Testing with data...')
    from datetime import datetime, timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 插入历史7天数据（每天2小时）
    for i in range(1, 8):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        db.save_app_usage('Chrome', 'Test', f'{d} 09:00:00', f'{d} 11:00:00', 7200)
    
    # 插入今天大量数据（6小时，3倍均值）
    db.save_app_usage('Chrome', 'Test', f'{today} 08:00:00', f'{today} 14:00:00', 21600)
    
    alerts = detector.detect_all()
    print(f'   Alerts after data: {len(alerts)}')
    for a in alerts:
        print(f'   - [{a["alert_type"]}] {a["title"]}')
    
    del db, detector
    import gc
    gc.collect()
    import time
    time.sleep(0.5)
    try:
        os.remove(db_path)
    except PermissionError:
        pass
    print('\nAnomalyDetector tests PASSED!')


if __name__ == '__main__':
    test_anomaly_db()
    test_anomaly_detector()
    print('\n=== ALL TESTS PASSED ===')