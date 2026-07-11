"""对话框基类 - 统一管理主题色和暗色模式

所有对话框共享的模式:
- _is_dark / _colors 状态管理
- 对话框背景样式(dialog_base/dialog_card)
- set_theme() 暗色模式切换

用法:
    class MyDialog(BaseDialog):
        def __init__(self, parent=None):
            super().__init__(is_dark=False, parent=parent, dialog_style="dialog_card")
            self._setup_ui()

        def _setup_ui(self):
            colors = self._colors
            # ... 使用 colors 构建UI

        def set_theme(self, is_dark):
            super().set_theme(is_dark)
            # ... 更新子控件样式
"""

from PyQt5.QtWidgets import QDialog, QWidget
from gui.themes import get_colors, QSS_STYLES


class BaseDialog(QDialog):
    """对话框基类 - 统一管理主题色和暗色模式"""

    def __init__(
        self,
        is_dark: bool = False,
        parent: QWidget = None,
        dialog_style: str = "dialog_base",
    ) -> None:
        super().__init__(parent)
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        self._dialog_style = dialog_style
        if dialog_style:
            self._apply_dialog_style()

    def _apply_dialog_style(self) -> None:
        """应用对话框背景样式"""
        if self._dialog_style in QSS_STYLES:
            self.setStyleSheet(
                QSS_STYLES[self._dialog_style].format(c=self._colors)
            )

    def set_theme(self, is_dark: bool) -> None:
        """设置主题（明/暗模式）

        子类可重写此方法以更新子控件样式，但应先调用 super().set_theme(is_dark)
        """
        self._is_dark = is_dark
        self._colors = get_colors(is_dark)
        if self._dialog_style:
            self._apply_dialog_style()

    # 别名：部分对话框使用 set_dark_mode 方法名
    def set_dark_mode(self, is_dark: bool) -> None:
        """set_theme 的别名，供使用 set_dark_mode 命名的调用方"""
        self.set_theme(is_dark)