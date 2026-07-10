"""导出管理器 - CSV和PDF导出功能"""
import csv
from datetime import datetime

from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtGui import QTextDocument
from PyQt5.QtPrintSupport import QPrinter
from utils.time_utils import format_duration


class ExportManager:
    """导出管理器 - 处理CSV和PDF导出"""

    def __init__(self, db, parent, app_version: str, callbacks: dict):
        """
        Args:
            db: DatabaseManager 实例
            parent: QWidget 父窗口（QFileDialog 需要）
            app_version: 应用版本号（PDF页脚使用）
            callbacks: 回调字典
                get_date_range: () -> (start_date, end_date, is_range)
                show_status: (str) -> None（状态栏消息）
        """
        self.db = db
        self.parent = parent
        self._app_version = app_version
        self.callbacks = callbacks

    def export_csv(self):
        """导出CSV - 支持日期范围，含分类信息"""
        start_date, end_date, is_range = self.callbacks["get_date_range"]()
        if is_range:
            default_name = f"行为记录_{start_date}_至_{end_date}"
        else:
            default_name = f"行为记录_{end_date}"
        path, _ = QFileDialog.getSaveFileName(
            self.parent, "导出CSV", f"{default_name}.csv",
            "CSV文件 (*.csv)"
        )
        if path:
            try:
                from gui.pages.categories_page import get_app_category, PRESET_CATEGORIES
                cat_names = {c[2]: c[0] for c in PRESET_CATEGORIES}
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(["应用名称", "分类", "窗口标题", "开始时间", "结束时间", "时长(秒)", "时长(格式化)"])
                    if is_range:
                        rows = self.db.get_app_usage_summary_range(start_date, end_date)
                        for item in rows:
                            secs = item.get("total_seconds", 0) or 0
                            dur = format_duration(secs)
                            cat = cat_names.get(get_app_category(item.get("app_name", "")), "其他")
                            writer.writerow([
                                item.get("app_name", ""),
                                cat,
                                item.get("window_title", ""),
                                item.get("start_time", ""),
                                item.get("end_time", ""),
                                f"{secs:.0f}",
                                dur
                            ])
                    else:
                        conn = self.db._get_conn()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT app_name, window_title, start_time, end_time, duration_seconds
                            FROM app_usage WHERE date(start_time) = ?
                            ORDER BY start_time
                        """, (end_date,))
                        for row in cursor.fetchall():
                            app_name = row[0]
                            secs = row[4] or 0
                            dur = format_duration(secs)
                            cat = cat_names.get(get_app_category(app_name), "其他")
                            writer.writerow([app_name, cat, row[1], row[2], row[3], f"{secs:.0f}", dur])
                self.callbacks["show_status"](f"已导出到: {path}")
            except Exception as e:
                QMessageBox.critical(self.parent, "错误", f"导出失败: {e}")

    def export_pdf(self):
        """导出PDF报告 - 支持日期范围，含分类统计和操作详情"""
        start_date, end_date, is_range = self.callbacks["get_date_range"]()
        if is_range:
            default_name = f"行为记录_{start_date}_至_{end_date}"
            date_label = f"{start_date} ~ {end_date}"
        else:
            default_name = f"行为记录_{end_date}"
            date_label = end_date

        path, _ = QFileDialog.getSaveFileName(
            self.parent, "导出PDF", f"{default_name}.pdf",
            "PDF文件 (*.pdf)"
        )
        if not path:
            return

        try:
            # 获取数据
            app_summary, total_seconds, input_counts = self._fetch_pdf_data(
                start_date, end_date, is_range
            )
            duration_str = format_duration(total_seconds)

            # 分类统计
            from utils.category_stats import compute_category_stats
            cat_stats, cat_names, cat_colors = compute_category_stats(app_summary, include_apps=False)

            # 构建分类表格行
            cat_rows = self._build_category_rows(cat_stats, cat_names, cat_colors, total_seconds)

            # 操作详情
            key_count = input_counts.get("keypress", 0) if isinstance(input_counts, dict) else 0
            click_count = input_counts.get("click", 0) if isinstance(input_counts, dict) else 0
            scroll_count = input_counts.get("scroll", 0) if isinstance(input_counts, dict) else 0

            # 构建HTML报告
            html = self._build_pdf_html({
                "date_label": date_label,
                "duration_str": duration_str,
                "app_summary": app_summary,
                "total_seconds": total_seconds,
                "input_counts": input_counts,
                "cat_rows": cat_rows,
                "key_count": key_count,
                "click_count": click_count,
                "scroll_count": scroll_count,
            })

            # 使用QPrinter输出PDF
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageSize(QPrinter.A4)

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)

            self.callbacks["show_status"](f"PDF已导出到: {path}")
        except Exception as e:
            QMessageBox.critical(self.parent, "错误", f"PDF导出失败: {e}")

    def _fetch_pdf_data(self, start_date, end_date, is_range):
        """获取PDF报告所需数据"""
        if is_range:
            app_summary = self.db.get_app_usage_summary_range(start_date, end_date)
            total_seconds = self.db.get_range_total_seconds(start_date, end_date)
            input_counts = self.db.get_input_event_count_range(start_date, end_date)
        else:
            app_summary = self.db.get_app_usage_summary(end_date)
            total_seconds = self.db.get_day_total_seconds(end_date)
            input_counts = self.db.get_input_event_count(end_date)
        return app_summary, total_seconds, input_counts

    def _build_category_rows(self, cat_stats, cat_names, cat_colors, total_seconds):
        """构建分类统计HTML表格行"""
        cat_rows = ""
        sorted_cats = sorted(cat_stats.items(), key=lambda x: -x[1]["seconds"])
        for cat_key, stats in sorted_cats:
            cat_label = cat_names.get(cat_key, cat_key)
            color = cat_colors.get(cat_key, "#6B7280")
            dur = format_duration(stats["seconds"])
            pct = f"{stats['seconds']/max(total_seconds,1)*100:.1f}%"
            cat_rows += f"""<tr>
                    <td><span style="color:{color};">■</span> {cat_label}</td>
                    <td>{dur}</td>
                    <td>{stats['count']}个应用</td>
                    <td>{pct}</td>
                </tr>"""
        return cat_rows

    def _build_pdf_html(self, data: dict):
        """构建PDF报告HTML内容"""
        date_label = data["date_label"]
        duration_str = data["duration_str"]
        app_summary = data["app_summary"]
        total_seconds = data["total_seconds"]
        input_counts = data["input_counts"]
        cat_rows = data["cat_rows"]
        key_count = data["key_count"]
        click_count = data["click_count"]
        scroll_count = data["scroll_count"]
        input_count = sum(input_counts.values()) if isinstance(input_counts, dict) else 0

        html = f"""
            <html><head><style>
                body {{ font-family: "Microsoft YaHei", sans-serif; padding: 40px; color: #111827; }}
                h1 {{ color: #3B82F6; font-size: 24px; }}
                h2 {{ color: #374151; border-bottom: 2px solid #E5E7EB; padding-bottom: 8px; font-size: 18px; }}
                h3 {{ color: #6B7280; font-size: 14px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px; }}
                th {{ background: #F3F4F6; padding: 8px 12px; text-align: left; border: 1px solid #E5E7EB; font-weight: bold; }}
                td {{ padding: 8px 12px; border: 1px solid #E5E7EB; }}
                .metrics {{ display: flex; gap: 30px; margin: 16px 0; }}
                .metric-card {{ background: #F9FAFB; border-radius: 8px; padding: 16px 24px; border: 1px solid #E5E7EB; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #111827; }}
                .metric-label {{ font-size: 12px; color: #6B7280; margin-top: 4px; }}
                .footer {{ color: #9CA3AF; font-size: 11px; margin-top: 30px; border-top: 1px solid #E5E7EB; padding-top: 12px; }}
                .bar {{ height: 8px; border-radius: 4px; background: #E5E7EB; }}
                .bar-fill {{ height: 8px; border-radius: 4px; }}
            </style></head><body>
            <h1>📊 行为记录报告</h1>
            <p style="color:#6B7280;">报告日期: {date_label} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h2>概览</h2>
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-value">{duration_str}</div>
                    <div class="metric-label">专注时长</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{len(app_summary)}</div>
                    <div class="metric-label">活跃应用</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{input_count:,}</div>
                    <div class="metric-label">操作次数</div>
                </div>
            </div>

            <h3>操作详情</h3>
            <table>
                <tr><th>类型</th><th>次数</th></tr>
                <tr><td>⌨️ 键盘输入</td><td>{key_count:,}</td></tr>
                <tr><td>🖱️ 鼠标点击</td><td>{click_count:,}</td></tr>
                <tr><td>📜 滚轮滚动</td><td>{scroll_count:,}</td></tr>
            </table>

            <h2>分类统计</h2>
            <table>
                <tr><th>分类</th><th>时长</th><th>应用数</th><th>占比</th></tr>
                {cat_rows}
            </table>

            <h2>应用使用详情 (Top 20)</h2>
            <table>
                <tr><th>排名</th><th>应用名称</th><th>时长</th><th>会话数</th><th>占比</th></tr>
            """

        for i, item in enumerate(app_summary[:20]):
            secs = item.get("total_seconds", 0) or 0
            dur = format_duration(secs)
            pct = f"{secs/max(total_seconds,1)*100:.1f}%"
            html += f"""<tr>
                    <td>{i+1}</td>
                    <td>{item.get('app_name', 'Unknown')}</td>
                    <td>{dur}</td>
                    <td>{item.get('session_count', 0)}</td>
                    <td>{pct}</td>
                </tr>"""

        html += f"""
            </table>
            <div class="footer">🛡 所有数据均存储于本地，未经您允许不会上传 | 行为记录 v{self._app_version}</div>
            </body></html>
            """
        return html