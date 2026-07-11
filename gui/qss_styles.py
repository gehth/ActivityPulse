"""QSS样式片段常量 - 高频重复的CSS属性组合

用法:
    from gui.qss_styles import QSS_STYLES
    colors = get_colors(is_dark)
    widget.setStyleSheet(QSS_STYLES["section_title"].format(c=colors))
"""

# QSS样式片段常量
# 排版(11): dialog_title, section_title, section_desc, metric_title, metric_value,
#   metric_change_up, metric_change_down, body_text, secondary_text, muted_text, small_text
# 边框/圆角(3): card_border, input_border, pill_border
# 按钮(4): btn_outline, btn_outline_hover, btn_primary_sm, btn_danger_sm
# 标签/徽章(4): badge, badge_primary, badge_danger, badge_success
# 色块(1): color_dot
# 分隔(1): divider
# 组件样式块(13): card_frame, dialog_base, dialog_card, btn_primary, btn_primary_md,
#   btn_ghost, btn_ghost_sm, btn_secondary, input_field, text_edit, time_edit, spinbox, progressbar

QSS_STYLES = {
    # 排版
    "dialog_title": "font-size: 18px; font-weight: bold; color: {c[text_primary]};",
    "section_title": "font-size: 15px; font-weight: bold; color: {c[text_primary]};",
    "section_desc": "font-size: 12px; color: {c[text_muted]};",
    "metric_title": "font-size: 13px; color: {c[text_secondary]};",
    "metric_value": "font-size: 28px; font-weight: bold; color: {c[text_primary]}; font-family: \"Consolas\", \"Microsoft YaHei\", monospace;",
    "metric_change_up": "font-size: 12px; color: {c[success]}; font-family: \"Consolas\", monospace;",
    "metric_change_down": "font-size: 12px; color: {c[danger]}; font-family: \"Consolas\", monospace;",
    "body_text": "font-size: 13px; color: {c[text_primary]}; line-height: 1.5;",
    "secondary_text": "font-size: 12px; color: {c[text_secondary]};",
    "muted_text": "font-size: 12px; color: {c[text_muted]};",
    "small_text": "font-size: 11px; color: {c[text_muted]};",

    # 边框/圆角
    "card_border": "border: 1px solid {c[border]}; border-radius: 8px;",
    "input_border": "border: 1px solid {c[border]}; border-radius: 6px;",
    "pill_border": "border-radius: 12px;",

    # 按钮
    "btn_outline": "background: transparent; border: 1px solid {c[border]}; color: {c[text_secondary]}; border-radius: 6px; padding: 4px 12px;",
    "btn_outline_hover": "border-color: {c[primary]}; color: {c[primary]}; background-color: {c[primary_light]};",
    "btn_primary_sm": "background-color: {c[primary]}; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;",
    "btn_danger_sm": "background-color: {c[danger]}; color: white; border: none; border-radius: 6px; padding: 4px 12px; font-size: 12px;",

    # 标签/徽章
    "badge": "font-size: 11px; padding: 2px 8px; border-radius: 4px;",
    "badge_primary": "font-size: 11px; padding: 2px 8px; border-radius: 12px; background-color: {c[primary_light]}; color: {c[primary]};",
    "badge_danger": "font-size: 11px; padding: 2px 8px; border-radius: 12px; background-color: {c[danger_light]}; color: {c[danger]};",
    "badge_success": "font-size: 11px; padding: 2px 8px; border-radius: 12px; background-color: {c[primary_light]}; color: {c[success]};",

    # 色块
    "color_dot": "width: 12px; height: 12px; border-radius: 6px;",

    # 分隔
    "divider": "background-color: {c[border]}; max-height: 1px; margin: 8px 0;",

    # ===== 组件样式块（多选择器） =====

    # 卡片容器
    "card_frame": "QFrame#card {{ background-color: {c[bg_card]}; border: 1px solid {c[border]}; border-radius: 8px; }}",

    # 对话框基础
    "dialog_base": "QDialog {{ background: {c[bg_primary]}; }} QLabel {{ color: {c[text_primary]}; }}",
    "dialog_card": "QDialog {{ background-color: {c[bg_card]}; }} QLabel {{ color: {c[text_primary]}; font-size: 13px; }}",

    # 主按钮（primary风格）
    "btn_primary": "QPushButton {{ background: {c[primary]}; color: white; border: none; border-radius: 6px; padding: 8px; font-size: 13px; font-weight: bold; }} QPushButton:hover {{ background: {c[primary_hover]}; }}",

    # 主按钮（小尺寸）
    "btn_primary_md": "QPushButton {{ background: {c[primary]}; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 12px; }} QPushButton:hover {{ background: {c[primary_hover]}; }}",

    # 幽灵按钮（outline风格）
    "btn_ghost": "QPushButton {{ border: 1px solid {c[border]}; border-radius: 4px; background: transparent; color: {c[text_secondary]}; font-size: 11px; }} QPushButton:hover {{ background: {c[primary_light]}; color: {c[primary]}; }}",

    # 幽灵按钮（带padding变体）
    "btn_ghost_sm": "QPushButton {{ border: 1px solid {c[border]}; border-radius: 4px; background: transparent; color: {c[text_secondary]}; font-size: 11px; padding: 0px 6px; }} QPushButton:hover {{ background: {c[bg_sidebar_hover]}; color: {c[text_primary]}; }}",

    # 次要按钮（sidebar_hover背景）
    "btn_secondary": "QPushButton {{ background: {c[bg_sidebar_hover]}; color: {c[text_primary]}; border: 1px solid {c[border]}; border-radius: 6px; padding: 8px; font-size: 13px; }} QPushButton:hover {{ background: {c[border]}; }}",

    # 输入框
    "input_field": "QLineEdit {{ background: {c[bg_sidebar_hover]}; color: {c[text_primary]}; border: 1px solid {c[border]}; border-radius: 4px; padding: 6px; font-size: 13px; }}",

    # 文本编辑框
    "text_edit": "QTextEdit {{ background: {c[bg_sidebar_hover]}; color: {c[text_primary]}; border: 1px solid {c[border]}; border-radius: 4px; padding: 4px; font-size: 12px; }}",

    # 时间选择器
    "time_edit": "QTimeEdit {{ background: {c[bg_sidebar_hover]}; color: {c[text_primary]}; border: 1px solid {c[border]}; border-radius: 4px; padding: 4px; }}",

    # 数字输入框
    "spinbox": "QSpinBox {{ background: {c[bg_sidebar_hover]}; color: {c[text_primary]}; border: 1px solid {c[border]}; border-radius: 4px; padding: 6px; font-size: 14px; }}",

    # 进度条
    "progressbar": "QProgressBar {{ border: none; border-radius: 4px; background-color: {c[bg_sidebar_hover]}; }} QProgressBar::chunk {{ border-radius: 4px; background-color: {c[primary]}; }}",
}