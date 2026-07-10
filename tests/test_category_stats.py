"""category_stats 分类统计工具单元测试"""
import pytest
from unittest.mock import patch
from utils.category_stats import compute_category_stats


class TestComputeCategoryStats:
    """compute_category_stats 核心逻辑测试"""

    def test_empty_summary(self):
        """空列表应返回空统计"""
        cat_stats, cat_names, cat_colors = compute_category_stats([])
        assert cat_stats == {}
        assert isinstance(cat_names, dict)
        assert isinstance(cat_colors, dict)

    def test_single_app(self):
        """单个应用统计"""
        app_summary = [{"app_name": "chrome.exe", "total_seconds": 3600}]
        cat_stats, cat_names, cat_colors = compute_category_stats(app_summary)

        # chrome.exe 属于 browser 分类
        assert "browser" in cat_stats
        assert cat_stats["browser"]["seconds"] == 3600
        assert cat_stats["browser"]["count"] == 1

    def test_multiple_apps_same_category(self):
        """同分类多应用应合并时长"""
        app_summary = [
            {"app_name": "chrome.exe", "total_seconds": 1800},
            {"app_name": "firefox.exe", "total_seconds": 1200},
        ]
        cat_stats, _, _ = compute_category_stats(app_summary)

        assert "browser" in cat_stats
        assert cat_stats["browser"]["seconds"] == 3000
        assert cat_stats["browser"]["count"] == 2

    def test_multiple_categories(self):
        """多分类应分别统计"""
        app_summary = [
            {"app_name": "chrome.exe", "total_seconds": 3600},
            {"app_name": "code.exe", "total_seconds": 7200},
        ]
        cat_stats, cat_names, cat_colors = compute_category_stats(app_summary)

        assert "browser" in cat_stats
        assert "productivity" in cat_stats
        assert cat_stats["browser"]["seconds"] == 3600
        assert cat_stats["productivity"]["seconds"] == 7200

    def test_include_apps_true(self):
        """include_apps=True 应包含应用名列表"""
        app_summary = [{"app_name": "chrome.exe", "total_seconds": 3600}]
        cat_stats, _, _ = compute_category_stats(app_summary, include_apps=True)

        assert "browser" in cat_stats
        assert "apps" in cat_stats["browser"]
        assert "chrome.exe" in cat_stats["browser"]["apps"]

    def test_include_apps_false(self):
        """include_apps=False 不应包含应用名列表"""
        app_summary = [{"app_name": "chrome.exe", "total_seconds": 3600}]
        cat_stats, _, _ = compute_category_stats(app_summary, include_apps=False)

        assert "browser" in cat_stats
        assert "apps" not in cat_stats["browser"]

    def test_zero_seconds(self):
        """时长为0的应用应正常处理"""
        app_summary = [{"app_name": "chrome.exe", "total_seconds": 0}]
        cat_stats, _, _ = compute_category_stats(app_summary)

        assert "browser" in cat_stats
        assert cat_stats["browser"]["seconds"] == 0

    def test_none_seconds(self):
        """时长为None的应用应视为0"""
        app_summary = [{"app_name": "chrome.exe", "total_seconds": None}]
        cat_stats, _, _ = compute_category_stats(app_summary)

        assert "browser" in cat_stats
        assert cat_stats["browser"]["seconds"] == 0

    def test_missing_seconds_key(self):
        """缺少total_seconds键应视为0"""
        app_summary = [{"app_name": "chrome.exe"}]
        cat_stats, _, _ = compute_category_stats(app_summary)

        assert "browser" in cat_stats
        assert cat_stats["browser"]["seconds"] == 0

    def test_cat_names_and_colors_populated(self):
        """分类名称和颜色映射应被填充"""
        app_summary = [{"app_name": "chrome.exe", "total_seconds": 3600}]
        _, cat_names, cat_colors = compute_category_stats(app_summary)

        # browser 分类应有名称和颜色
        assert "browser" in cat_names
        assert "browser" in cat_colors
        assert cat_colors["browser"].startswith("#")

    def test_unknown_app_goes_to_other(self):
        """未知应用应归入 other 分类"""
        app_summary = [{"app_name": "totally_unknown_app.xyz", "total_seconds": 100}]
        cat_stats, _, _ = compute_category_stats(app_summary)

        assert "other" in cat_stats
        assert cat_stats["other"]["seconds"] == 100