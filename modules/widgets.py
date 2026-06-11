# -*- coding: utf-8 -*-
"""
到期提醒工具 — 自定义控件（FlatButton、绘制辅助）
"""

import tkinter as tk
from modules.config import C, FONT_FAMILY


# ---------------------------------------------------------------
# FlatButton — Canvas 圆角扁平按钮
# ---------------------------------------------------------------

class FlatButton(tk.Canvas):
    """圆角扁平按钮，支持 hover / press / disabled。"""
    def __init__(self, parent, text="", command=None, bg=None, fg=None,
                 height=32, radius=8, font=None, width=0, **kw):
        if command is None and "cmd" in kw:
            command = kw.pop("cmd")
        self._state = kw.pop("state", "normal")
        canvas_bg = parent.cget("bg") if hasattr(parent, "cget") else C.surface
        self._bg = bg or C.accent
        self._fg = fg or "white"
        self._bg_h = _lighten(self._bg, 0.08)
        self._bg_p = _lighten(self._bg, 0.15)
        self._text = text
        self._cmd = command
        self._radius = radius
        self._font = font or (FONT_FAMILY, 10)
        self._hover = False
        self._pressed = False
        self._pw = width if width else height * 2
        self._ph = height
        super().__init__(parent, height=height, bg=canvas_bg,
                         highlightthickness=0, width=self._pw)
        self.bind("<Configure>", lambda _: self.draw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _: self._set_hover(True))
        self.bind("<Leave>", lambda _: self._set_hover(False))
        self.after_idle(self.draw)

    def draw(self):
        if self._state == "disabled":
            bg = _lighten(C.border, 0.02)
            fg = C.text3
        else:
            bg = self._bg_p if self._pressed else (self._bg_h if self._hover else self._bg)
            fg = self._fg
        r = self._radius
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1:
            w = self._pw
        if h <= 1:
            h = self._ph
        self.delete("all")
        # 动态同步父容器背景，解决主题切换后四角颜色不一致
        parent_bg = C.bg
        try:
            parent_bg = self.master.cget("bg")
        except Exception:
            pass
        if self.cget("bg") != parent_bg:
            tk.Canvas.config(self, bg=parent_bg)
        _rounded_rect(self, 0, 0, w, h, r, fill=bg, canvas_bg=parent_bg)
        self.create_text(w / 2, h / 2, text=self._text, fill=fg,
                         font=self._font, anchor="center")

    def _set_hover(self, on):
        if self._state == "disabled":
            return
        self._hover = on
        self._pressed = False
        self.after(30, self.draw)

    def _on_click(self, _event):
        if self._state == "disabled":
            return
        self._pressed = True
        self.draw()
        self.update()
        self.after(100, self.draw)
        if self._cmd:
            self._cmd()

    def config(self, **kw):
        if "text" in kw:
            self._text = kw.pop("text")
        if "command" in kw:
            self._cmd = kw.pop("command")
        if "font" in kw:
            self._font = kw.pop("font")
        if "state" in kw:
            self._state = kw.pop("state")
        self._bg = kw.pop("bg", self._bg)
        self._fg = kw.pop("fg", self._fg)
        # Canvas 背景不在此设置，由 draw() 动态同步父容器
        kw.pop("bg", None)
        kw.pop("fg", None)
        if kw:
            super().config(**kw)
        self._bg_h = _lighten(self._bg, 0.08)
        self._bg_p = _lighten(self._bg, 0.15)
        self.draw()

    def sync_canvas_bg(self, color):
        """仅更新 Canvas 底色（圆角空隙区域），不动 _bg（按钮填充色）。"""
        tk.Canvas.config(self, bg=color)


# ---------------------------------------------------------------
# 绘制辅助
# ---------------------------------------------------------------

def _lighten(hex_color, amount):
    """#RRGGBB 变亮。"""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r = min(255, int(h[0:2], 16) + int(255 * amount))
    g = min(255, int(h[2:4], 16) + int(255 * amount))
    b = min(255, int(h[4:6], 16) + int(255 * amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def _rounded_rect(canvas, x1, y1, x2, y2, r, **kw):
    """用单个多边形绘制圆角矩形，角落用 canvas_bg 填充以融入父容器背景。"""
    fill_color = kw.get("fill", "")
    canvas_bg = kw.get("canvas_bg", fill_color)
    # 底层垫满整个 Canvas 的 canvas_bg 色矩形，使四角与父容器一致
    canvas.create_rectangle(x1, y1, x2, y2, fill=canvas_bg, outline=canvas_bg)
    points = []
    S = 16  # 每段弧的点数，越大弧越光滑
    # 上边
    points.extend([x1 + r, y1, x2 - r, y1])
    # 右上弧 (90° → 0°)
    _arc_points(points, x2 - r, y1 + r, r, 90, -90, S)
    # 右边
    points.extend([x2, y1 + r, x2, y2 - r])
    # 右下弧 (0° → -90°)
    _arc_points(points, x2 - r, y2 - r, r, 0, -90, S)
    # 下边
    points.extend([x2 - r, y2, x1 + r, y2])
    # 左下弧 (270° → 180°)
    _arc_points(points, x1 + r, y2 - r, r, 270, -90, S)
    # 左边
    points.extend([x1, y2 - r, x1, y1 + r])
    # 左上弧 (180° → 90°)
    _arc_points(points, x1 + r, y1 + r, r, 180, -90, S)
    canvas.create_polygon(points, fill=fill_color, outline=fill_color)


def _arc_points(dst, cx, cy, r, start, extent, steps):
    import math
    for i in range(steps + 1):
        a = math.radians(start + extent * i / steps)
        dst.extend([cx + r * math.cos(a), cy - r * math.sin(a)])
