# -*- coding: utf-8 -*-
"""
到期提醒工具 — 工具函数（日期解析、通知、调试日志）
"""

import re
import sys
import logging
from datetime import datetime, timedelta
from config import DATE_FORMATS, LOG_FILE, COL_MAP, HEADER_PATTERNS

# ---------------------------------------------------------------
# 调试日志（默认关闭，enable_debug() 后开启）
# ---------------------------------------------------------------

_logger = logging.getLogger("expiry_reminder")
_logger.setLevel(logging.DEBUG)
_logger.propagate = False

_fh = None
_debug_on = False


def enable_debug():
    """开启调试日志，输出到 LOG_FILE。"""
    global _fh, _debug_on
    if _debug_on:
        return True
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    _logger.addHandler(_fh)
    _debug_on = True
    log_debug("DEBUG 模式已开启")
    return True


def disable_debug():
    """关闭调试日志。"""
    global _fh, _debug_on
    if not _debug_on or _fh is None:
        return True
    _logger.removeHandler(_fh)
    _fh.flush()
    _fh.close()
    _fh = None
    _debug_on = False
    return True


def is_debug_on():
    return _debug_on


def log_debug(msg):
    if _debug_on:
        _logger.debug(msg)
        try: _fh.flush()
        except Exception: pass


def log_trace(msg):
    """UI 操作追踪日志，仅 debug 模式时写入。"""
    log_debug(msg)


def log_error(msg):
    if _debug_on:
        _logger.error(msg)
    else:
        # error 始终写文件，debug 关闭时手动写入
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                from datetime import datetime as _dt
                f.write(f"{_dt.now().strftime('%Y-%m-%d %H:%M:%S')} [ERROR] {msg}\n")
        except Exception:
            pass
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------
# 日期解析（带缓存，相同值不重复解析）
# ---------------------------------------------------------------

_date_cache = {}          # str → (date, err)
_DATE_CACHE_MAX = 5000
_RE_DATE = re.compile(r"^[\d年月日./-]+$")


def _parse_date_core(val):
    """内部解析逻辑，结果会被缓存。"""
    if val is None:
        return None, "空值"
    if isinstance(val, datetime):
        return val.date(), None
    if isinstance(val, (int, float)):
        try:
            return (datetime(1899, 12, 30) + timedelta(days=int(val))).date(), None
        except Exception:
            return None, "无效数字"
    s = str(val).strip()
    if not s or not _RE_DATE.match(s):
        return None, "非日期"
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date(), None
        except Exception:
            pass
    return None, f"无法解析：{s[:12]}"


def parse_date(val):
    """解析日期值，字符串结果会被缓存避免重复 strptime。"""
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None, "空值"
        cached = _date_cache.get(s)
        if cached is not None:
            return cached
        result = _parse_date_core(val)
        if len(_date_cache) < _DATE_CACHE_MAX:
            _date_cache[s] = result
        return result
    return _parse_date_core(val)


def clear_date_cache():
    """清空日期缓存（加载新文件时调用）。"""
    _date_cache.clear()


def check_expiry(d, days_ahead=7, _today=None):
    """检查到期状态。_today 可预传入避免循环中重复获取。"""
    if _today is None:
        _today = datetime.today().date()
    diff = (d - _today).days
    if diff < 0:
        return "已过期", diff
    if diff == 0:
        return "今天到期", diff
    if diff <= days_ahead:
        return f"即将到期({diff}天)", diff
    return "正常", diff


# ---------------------------------------------------------------
# Excel 辅助
# ---------------------------------------------------------------

def _row_value(row, idx):
    return row[idx] if idx < len(row) else None


def detect_date_columns(headers, rows, max_sample=50):
    """检测日期列：前 5 个非空值均非日期则跳过该列（提前退出）。"""
    candidates = []
    sample_rows = rows[:max_sample]
    max_cols = max(len(headers), max((len(r) for r in sample_rows), default=0))
    _PROBE = 5  # 前 N 个值探测，均非日期则跳过
    for col in range(max_cols):
        vals = []
        for row in sample_rows:
            v = _row_value(row, col)
            if v is not None:
                vals.append(v)
        if not vals:
            continue
        # 提前退出：前 _PROBE 个值均非日期 → 跳过整列
        probe = vals[:_PROBE]
        if all(parse_date(v)[0] is None for v in probe):
            continue
        ok = sum(1 for v in vals if parse_date(v)[0] is not None)
        ratio = ok / len(vals)
        if ok >= 2 and ratio >= 0.4:
            h = str(_row_value(headers, col) or "").strip()
            score = ratio + (0.3 if re.search(r"时间|日期|送货|截止|到期|有效", h) else 0)
            candidates.append({
                "col": col + 1,
                "index": col,
                "header": h,
                "ok": ok,
                "total": len(vals),
                "score": score,
            })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def detect_col_map(headers):
    """根据表头关键词自动检测列位置，未匹配的字段回退到 COL_MAP 默认值。"""
    result = dict(COL_MAP)
    for field, keywords in HEADER_PATTERNS.items():
        for i, h in enumerate(headers):
            h_str = str(h or "").strip().lower()
            if not h_str:
                continue
            if any(kw.lower() in h_str for kw in keywords):
                result[field] = i
                break
    return result


# ---------------------------------------------------------------
# 系统通知
# ---------------------------------------------------------------

def send_notify(title, msg):
    import platform as _plat
    try:
        if _plat.system() == "Darwin":
            # macOS 原生通知
            import subprocess as _sp
            script = f'display notification "{msg}" with title "{title}"'
            _sp.run(["osascript", "-e", script], check=False)
            return
    except Exception:
        pass
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, msg, duration=5, threaded=False)
        return
    except Exception:
        pass
    try:
        import ctypes as ct
        from ctypes import Structure, byref, wintypes as w
        Shell = ct.windll.shell32.Shell_NotifyIconW

        class NID(Structure):
            _fields_ = [
                ("cbSize", w.UINT), ("hWnd", w.HWND), ("uID", w.UINT),
                ("uFlags", w.UINT), ("uCallbackMessage", w.UINT), ("hIcon", ct.c_void_p),
                ("szTip", ct.c_wchar * 128), ("dwState", w.UINT), ("dwStateMask", w.UINT),
                ("szInfo", ct.c_wchar * 256), ("uTimeout", w.UINT),
                ("szInfoTitle", ct.c_wchar * 64), ("dwInfoFlags", w.UINT),
            ]

        Shell(0x1, byref(NID(
            cbSize=ct.sizeof(NID),
            hWnd=ct.windll.user32.GetForegroundWindow(), uID=1, uFlags=0x10,
            szInfo=msg[:255], uTimeout=5000,
            szInfoTitle=title[:63], dwInfoFlags=1,
        )))
    except Exception:
        pass
