# -*- coding: utf-8 -*-
"""
到期提醒工具 — 配置常量
"""

import os
import platform

# 程序根目录（modules/ 的上一级）
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_ROOT_DIR, "assets")

HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".expiry_reminder_history.json")
LOG_FILE = os.path.join(_ROOT_DIR, "expiry_reminder_debug.log")
NOTIFY_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".expiry_reminder_notify.json")
ROBOT_SYNC_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".expiry_reminder_robot_sync.json")

# 跨平台字体
FONT_FAMILY = "Segoe UI" if platform.system() == "Windows" else (".AppleSystemUIFont" if platform.system() == "Darwin" else "Sans")

# ---------------------------------------------------------------
# 颜色 & 主题（浅色参照 Tailwind slate/blue 色系）
# ---------------------------------------------------------------

LIGHT_COLORS = {
    "bg":        "#E9EEF5",
    "surface":   "#F7F9FC",
    "surface2":  "#EEF3F8",
    "border":    "#CBD5E1",
    "accent":    "#2563EB",   # blue-600
    "accent_h":  "#3B82F6",   # blue-500
    "text":      "#334155",   # slate-700
    "text2":     "#64748B",   # slate-500
    "text3":     "#64748B",   # slate-500
    "btn2":      "#5B6678",
    "danger":    "#C42B1C",
    "danger_bg": "#FDECEC",
    "warn":      "#B45309",
    "warn_bg":   "#FDF0C8",
    "ok":        "#166534",
    "ok_bg":     "#E3F7EA",
    "info":      "#075985",
    "info_bg":   "#E2EEF9",
}

# Tailwind CSS 暗色主题色板（slate / blue / red / amber / emerald / sky）
DARK_COLORS = {
    "bg":        "#020617",   # slate-950
    "surface":   "#0F172A",   # slate-900
    "surface2":  "#1E293B",   # slate-800
    "border":    "#334155",   # slate-700
    "accent":    "#60A5FA",   # blue-400
    "accent_h":  "#93C5FD",   # blue-300
    "text":      "#E2E8F0",   # slate-200
    "text2":     "#94A3B8",   # slate-400
    "text3":     "#64748B",   # slate-500
    "btn2":      "#475569",   # slate-600
    "danger":    "#F87171",   # red-400
    "danger_bg": "#450A0A",   # red-950
    "warn":      "#FBBF24",   # amber-400
    "warn_bg":   "#451A03",   # amber-950
    "ok":        "#34D399",   # emerald-400
    "ok_bg":     "#022C22",   # emerald-950
    "info":      "#38BDF8",   # sky-400
    "info_bg":   "#082F49",   # sky-950
}

C = type("C", (), dict(LIGHT_COLORS))()

# ---------------------------------------------------------------
# 日期格式
# ---------------------------------------------------------------

DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
    "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y",
    "%m/%d/%Y", "%m-%d-%Y",
    "%Y年%m月%d日",
    "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
    "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
    "%y/%m/%d", "%y-%m-%d", "%y.%m.%d",
    "%Y%m%d",
]

# ---------------------------------------------------------------
# 列映射
# ---------------------------------------------------------------

COL_MAP = {
    "customer": 0,       # 客户
    "order_status": 4,   # 订单状态
    "product": 5,        # 产品
    "quantity": 6,       # 数量
    "note": 10,          # 备注
}

# 表头关键词匹配（用于自动检测列位置，关键词越靠前优先级越高）
HEADER_PATTERNS = {
    "customer":     ["客户", "顾客", "买家", "company", "customer", "client"],
    "product":      ["产品", "商品", "货品", "货物", "品名", "product", "item", "goods"],
    "order_status": ["订单状态", "发货状态", "状态", "status", "order status"],
    "quantity":     ["数量", "件数", "qty", "quantity", "amount", "count"],
    "note":         ["备注", "说明", "remark", "note", "memo", "comment"],
}
