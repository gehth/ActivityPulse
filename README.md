<div align="center">

# ActivityPulse

**电脑行为记录与数据分析工具**

实时追踪应用使用、输入活动与屏幕时间，用数据洞察你的数字生活节奏

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[功能特性](#功能特性) · [快速开始](#快速开始) · [项目结构](#项目结构) · [技术栈](#技术栈) · [文档](#文档)

</div>

---

## 功能特性

### 📊 实时监控
- **应用使用追踪** — 自动记录前台应用切换，统计各应用使用时长
- **输入活动检测** — 监测键盘/鼠标活动，识别活跃与空闲时段
- **屏幕截图** — 可配置间隔自动截图，支持按日期浏览与全屏查看

### 📈 数据洞察
- **仪表盘** — 一目了然的今日概览：专注时长、活跃应用数、目标进度
- **时间轴** — 可视化全天活动轨迹，精确到分钟级
- **统计洞察** — 环形图/折线图/柱状图多维度分析应用占比与趋势
- **分类管理** — 自动推断应用分类，支持自定义分类与敏感标记

### ⏰ 效率工具
- **番茄钟** — 浮动计时器，专注/休息循环提醒
- **每日目标** — 设置专注时长目标，实时追踪完成进度
- **应用限制** — 为指定应用设置每日使用时间上限，超时提醒

### 🔔 智能提醒
- **久坐提醒** — 长时间未活动时弹出提醒对话框
- **异常告警** — 检测异常使用模式（深夜使用、过度使用等），系统托盘通知

### 🛠 系统集成
- **系统托盘** — 最小化到托盘，后台静默记录
- **全局快捷键** — Ctrl+F 全局搜索，Ctrl+Shift+M 切换监控
- **开机自启** — 可配置开机自动启动并开始记录
- **明暗主题** — 跟随系统或手动切换 Light/Dark 主题

### 💾 数据管理
- **SQLite 存储** — 轻量本地数据库，零配置
- **备份恢复** — 一键打包/恢复数据库与截图
- **PDF 报告** — 导出每日/每周活动报告
- **自动清理** — 按保留天数自动清理过期数据

---

## 快速开始

### 环境要求

- Python 3.8+
- Windows 10/11

### 安装依赖

```bash
git clone https://github.com/gehth/ActivityPulse.git
cd ActivityPulse
pip install -r requirements.txt
```

### 启动应用

```bash
python main.py
```

### 打包发布

```bash
pip install pyinstaller
pyinstaller build.spec
```

---

## 项目结构

```
ActivityPulse/
├── main.py                    # 应用入口
├── requirements.txt           # 依赖清单
├── build.spec                 # PyInstaller 打包配置
│
├── gui/                       # 界面模块
│   ├── main_window.py         # 主窗口
│   ├── sidebar.py             # 侧边栏导航
│   ├── themes.py              # 主题系统（Light/Dark）
│   ├── settings_dialog.py     # 设置对话框
│   ├── search_dialog.py       # 全局搜索
│   ├── pomodoro_widget.py     # 番茄钟组件
│   ├── image_viewer.py        # 图片查看器
│   ├── screen_playback.py     # 截图回放
│   ├── activity_tag_dialog.py # 活动标签
│   ├── app_limit_dialog.py    # 应用限制
│   ├── anomaly_alert_dialog.py# 异常告警卡片
│   ├── pages/                 # 页面
│   │   ├── dashboard_page.py  # 仪表盘
│   │   ├── timeline_page.py   # 时间轴
│   │   ├── insights_page.py   # 统计洞察
│   │   ├── screenshots_page.py# 截图浏览
│   │   ├── categories_page.py # 分类管理
│   │   └── welcome_page.py    # 欢迎页
│   └── components/            # 组件
│       ├── check_manager.py   # 检测管理器
│       ├── export_manager.py  # PDF导出
│       ├── icon_factory.py    # 图标工厂
│       ├── toolbar_builder.py # 工具栏构建
│       └── tray_manager.py    # 托盘管理
│
├── monitors/                  # 监控模块
│   ├── app_monitor.py         # 应用使用监控
│   ├── input_monitor.py       # 输入活动监控
│   └── screen_monitor.py      # 屏幕截图监控
│
├── database/                  # 数据库模块（Mixin 架构）
│   ├── db_manager.py          # 数据库管理器（组合7个Mixin）
│   ├── app_usage_mixin.py     # 应用使用数据
│   ├── idle_mixin.py          # 空闲检测数据
│   ├── screenshot_mixin.py    # 截图数据
│   ├── settings_mixin.py      # 配置管理
│   ├── anomaly_mixin.py       # 异常告警数据
│   ├── app_limit_mixin.py     # 应用限制数据
│   └── activity_tag_mixin.py  # 活动标签数据
│
├── utils/                     # 工具模块
│   ├── backup_restore.py      # 备份恢复
│   ├── anomaly_detector.py    # 异常检测引擎
│   ├── category_stats.py      # 分类统计
│   ├── segment_merge.py       # 时间段合并
│   ├── time_utils.py          # 时间工具
│   ├── auto_report.py         # 自动报告
│   ├── autostart.py           # 开机自启
│   ├── global_hotkey.py       # 全局快捷键
│   └── async_loader.py        # 异步加载器
│
└── tests/                     # 测试套件
    ├── test_db_manager.py     # 数据库测试
    ├── test_backup_restore.py # 备份恢复测试
    ├── test_anomaly_detector.py# 异常检测测试
    └── ...
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 界面 | PyQt5 + 自定义 QSS 主题系统 |
| 数据库 | SQLite（Mixin 架构，7个功能模块解耦） |
| 监控 | psutil + pynput + Win32 API |
| 打包 | PyInstaller |
| 测试 | pytest |

---

## 界面预览

| 仪表盘 | 时间轴 |
|:------:|:------:|
| 实时指标卡片 + 热力图 + Top5应用 | 全天活动轨迹，分钟级精度 |

| 统计洞察 | 分类管理 |
|:--------:|:--------:|
| 环形图 + 折线图 + 柱状图 | 自动分类 + 自定义 + 敏感标记 |

---

## 文档

- 📖 [维护与使用手册](开发文档/维护与使用手册.md) — 完整的项目架构、模块详解、配置系统、开发规范
- 🌐 [HTML 版手册](开发文档/维护与使用手册.html) — 带侧边栏导航的可视化文档

---

## 许可证

MIT License