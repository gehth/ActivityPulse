"""模块导入测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

errors = []

def test(name, func):
    try:
        func()
        print(f"[OK] {name}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        errors.append((name, str(e)))

test("DatabaseManager", lambda: __import__('database.db_manager', fromlist=['DatabaseManager']))
test("themes", lambda: __import__('gui.themes', fromlist=['get_theme_qss']))
test("Sidebar", lambda: __import__('gui.sidebar', fromlist=['Sidebar']))
test("DashboardPage", lambda: __import__('gui.pages.dashboard_page', fromlist=['DashboardPage']))
test("TimelinePage", lambda: __import__('gui.pages.timeline_page', fromlist=['TimelinePage']))
test("InsightsPage", lambda: __import__('gui.pages.insights_page', fromlist=['InsightsPage']))
test("CategoriesPage", lambda: __import__('gui.pages.categories_page', fromlist=['CategoriesPage']))
test("MainWindow", lambda: __import__('gui.main_window', fromlist=['MainWindow']))

# 测试数据库
try:
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    db.close()
    print("[OK] Database init/close")
except Exception as e:
    print(f"[FAIL] Database init/close: {e}")
    errors.append(("Database", str(e)))

if errors:
    print(f"\n{len(errors)} error(s) found!")
    for n, e in errors:
        print(f"  - {n}: {e}")
else:
    print("\nAll tests passed!")