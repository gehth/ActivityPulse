"""仪表盘组件库 - 仪表盘页面使用的所有Widget组件（re-export入口，保持向后兼容）"""

from gui.pages.dashboard_cards import (
    MetricCard,
    GoalProgressCard,
    IdleTimeCard,
    WeekCompareCard,
    HourlyDistCard,
    TopAppItem,
)

from gui.pages.dashboard_charts import (
    HeatmapWidget,
    GoalRingWidget,
    WeekBarWidget,
    HourlyBarWidget,
)

__all__ = [
    "MetricCard",
    "GoalProgressCard",
    "IdleTimeCard",
    "WeekCompareCard",
    "HourlyDistCard",
    "TopAppItem",
    "HeatmapWidget",
    "GoalRingWidget",
    "WeekBarWidget",
    "HourlyBarWidget",
]