import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager

db = DatabaseManager()
# 测试新增的数据库方法
print('get_day_total_seconds:', db.get_day_total_seconds('2026-07-07'))
print('get_day_app_count:', db.get_day_app_count('2026-07-07'))
print('get_heatmap_data:', len(db.get_heatmap_data('2026-07-07')), 'rows')
print('get_timeline_data:', len(db.get_timeline_data('2026-07-07')), 'rows')
print('get_7day_trend:', len(db.get_7day_trend('2026-07-07')), 'rows')
print('get_hourly_distribution:', len(db.get_hourly_distribution('2026-07-07')), 'rows')
db.close()
print('DB methods OK')