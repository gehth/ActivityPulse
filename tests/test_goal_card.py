"""测试每日目标卡片"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt5.QtWidgets import QApplication
from database.db_manager import DatabaseManager
from gui.pages.dashboard_page import GoalProgressCard, GoalRingWidget

app = QApplication(sys.argv)
db = DatabaseManager()
card = GoalProgressCard(db_manager=db)
print(f'Default goal: {card._goal_minutes} minutes')
card.set_progress(3600)  # 1 hour
print(f'Progress after 1h: target={card._target_progress:.2f}')
print(f'Current minutes: {card._current_minutes}')

# Test goal achieved signal
achieved = []
card.goal_achieved.connect(lambda: achieved.append(True))
card.set_progress(480 * 60)  # 8 hours = goal
print(f'Goal achieved signal fired: {len(achieved) > 0}')
print('GoalProgressCard test OK')