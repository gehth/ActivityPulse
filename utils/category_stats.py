"""分类统计工具 - 统一应用分类统计逻辑"""
from typing import List, Dict, Tuple


def compute_category_stats(
    app_summary: List[Dict],
    include_apps: bool = True,
) -> Tuple[Dict, Dict, Dict]:
    """计算应用分类统计

    遍历应用摘要列表，按分类汇总时长和应用数。

    Args:
        app_summary: 应用摘要列表，每项需含 'app_name' 和 'total_seconds'
        include_apps: 是否在统计中包含应用名列表（默认True）

    Returns:
        (cat_stats, cat_names, cat_colors)
        - cat_stats: {cat_key: {"seconds": float, "count": int, "apps": [str]}}
        - cat_names: {cat_key: 显示名称}，如 {"productivity": "生产力工具"}
        - cat_colors: {cat_key: 颜色hex}，如 {"productivity": "#3B82F6"}
    """
    from gui.pages.categories_page import get_app_category, PRESET_CATEGORIES

    cat_names = {c[2]: c[0] for c in PRESET_CATEGORIES}
    cat_colors = {c[2]: c[1] for c in PRESET_CATEGORIES}

    cat_stats = {}
    for item in app_summary:
        app_name = item.get("app_name", "Unknown")
        secs = item.get("total_seconds", 0) or 0
        cat = get_app_category(app_name)
        if cat not in cat_stats:
            cat_stats[cat] = {"seconds": 0, "count": 0}
            if include_apps:
                cat_stats[cat]["apps"] = []
        cat_stats[cat]["seconds"] += secs
        cat_stats[cat]["count"] += 1
        if include_apps and "apps" in cat_stats[cat]:
            cat_stats[cat]["apps"].append(app_name)

    return cat_stats, cat_names, cat_colors