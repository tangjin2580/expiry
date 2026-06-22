# -*- coding: utf-8 -*-
"""
到期提醒工具 — 配置常量
"""

import os
import sys
import platform

# 程序根目录（modules/ 的上一级）
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_ROOT_DIR, "assets")

HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".expiry_reminder_history.json")
LOG_FILE = os.path.join(_ROOT_DIR, "expiry_reminder_debug.log")
NOTIFY_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".expiry_reminder_notify.json")
ROBOT_SYNC_CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".expiry_reminder_robot_sync.json")

# 版本 & 更新
APP_VERSION = "5.1"
GITHUB_REPO = "tangjin2580/expiry"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def check_for_updates():
    """
    检查 GitHub 最新版本。
    返回 dict: {"has_update": bool, "latest": str, "current": str, "url": str, "body": str}
    网络失败时返回 {"error": str}。
    """
    import urllib.request
    import json as _json
    try:
        req = urllib.request.Request(
            GITHUB_API_LATEST,
            headers={"Accept": "application/vnd.github.v3+json",
                     "User-Agent": f"ExpiryReminder/{APP_VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "").lstrip("v")
        latest_name = data.get("name", latest_tag)
        html_url = data.get("html_url", "")
        body = data.get("body", "")

        # 提取版本号的主要数字部分用于比较
        def _ver_key(v):
            parts = []
            for seg in v.split("-")[0].split("."):
                try:
                    parts.append(int(seg))
                except ValueError:
                    break
            return tuple(parts) if parts else (0,)

        has_update = _ver_key(latest_tag) > _ver_key(APP_VERSION)

        return {
            "has_update": has_update,
            "latest": latest_name or latest_tag,
            "latest_tag": latest_tag,
            "current": APP_VERSION,
            "url": html_url,
            "body": body[:500],
        }
    except Exception as e:
        return {"error": str(e)}

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

# ---------------------------------------------------------------
# 开机自启（Windows 注册表）
# ---------------------------------------------------------------

_REGISTRY_RUN_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
_REGISTRY_APP_NAME = "ExpiryReminder"


def get_exe_path():
    """获取当前可执行文件路径（兼容 PyInstaller 打包和脚本直接运行）。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def get_autostart_enabled():
    """检查开机自启是否已启用。"""
    if platform.system() != "Windows":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REGISTRY_RUN_KEY,
                             0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, _REGISTRY_APP_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        return False


def set_autostart(enabled):
    """设置或取消开机自启。启用时以 --background 后台模式启动。"""
    if platform.system() != "Windows":
        return
    import winreg
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REGISTRY_RUN_KEY,
                         0, winreg.KEY_SET_VALUE)
    if enabled:
        exe = get_exe_path()
        if getattr(sys, "frozen", False):
            cmd = f'"{exe}" --background'
        else:
            cmd = f'"{sys.executable}" "{exe}" --background'
        winreg.SetValueEx(key, _REGISTRY_APP_NAME, 0, winreg.REG_SZ, cmd)
    else:
        try:
            winreg.DeleteValue(key, _REGISTRY_APP_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)

# 表头关键词匹配（用于自动检测列位置，关键词越靠前优先级越高）
HEADER_PATTERNS = {
    "customer":     ["客户", "顾客", "买家", "company", "customer", "client"],
    "product":      ["产品", "商品", "货品", "货物", "品名", "product", "item", "goods"],
    "order_status": ["订单状态", "发货状态", "状态", "status", "order status"],
    "quantity":     ["数量", "件数", "qty", "quantity", "amount", "count"],
    "note":         ["备注", "说明", "remark", "note", "memo", "comment"],
}
